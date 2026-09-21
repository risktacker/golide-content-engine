from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

from golide_engine.db import ContentRepository
from golide_engine.db.connections import ConnectionRepository
from golide_engine.db.inbox import InboxRepository
from golide_engine.engine import ContentClass, ContentDraft, ContentPolicy, PlatformVariant
from golide_engine.engine.social_image import SocialImageProfile
from golide_engine.storage import Database
from golide_engine.storage.r2 import R2TemporaryMediaStore
from golide_engine.storage.temporary import TemporaryMediaRepository


class StudioService:
    """Admin-facing service layer for the locked GOLIDE content operating system."""

    def __init__(
        self,
        database: Database,
        *,
        media_store: R2TemporaryMediaStore | None = None,
        root: str | Path = ".",
    ):
        self.database = database
        self.root = Path(root)
        self.policy = ContentPolicy(self.root)
        self.content = ContentRepository(database, self.policy)
        self.connections = ConnectionRepository(database)
        self.inbox = InboxRepository(database)
        self.media = TemporaryMediaRepository(database)
        self.media_store = media_store

    def policy_snapshot(self) -> dict:
        return self.policy.snapshot()

    def overview(self) -> dict:
        def count(query: str, params: tuple = ()) -> int:
            rows = self.database.rows(query, params)
            return int(rows[0]["count"]) if rows else 0

        return {
            "posts_today": count(
                """SELECT COUNT(*) count FROM content_posts
                   WHERE content_class='post' AND date(created_at)=date('now')"""
            ),
            "scheduled": count(
                "SELECT COUNT(*) count FROM content_posts WHERE status='scheduled'"
            ),
            "published": count(
                "SELECT COUNT(*) count FROM content_posts WHERE status='published'"
            ),
            "failed": count(
                "SELECT COUNT(*) count FROM content_posts WHERE status IN ('failed','partial')"
            ),
            "open_responses": count(
                "SELECT COUNT(*) count FROM inbox_threads WHERE status='open'"
            ),
            "connected_platforms": count(
                "SELECT COUNT(*) count FROM social_accounts WHERE status='connected'"
            ),
            "temporary_media": count(
                "SELECT COUNT(*) count FROM temporary_media WHERE status!='deleted'"
            ),
            "draft_posts": count(
                "SELECT COUNT(*) count FROM content_posts WHERE content_class='post' AND status='draft'"
            ),
            "draft_shorts": count(
                "SELECT COUNT(*) count FROM content_posts WHERE content_class='short' AND status='draft'"
            ),
            "draft_longs": count(
                "SELECT COUNT(*) count FROM content_posts WHERE content_class='long' AND status='draft'"
            ),
            "r2_ready": self.media_store is not None,
        }

    def posts(self, status: str | None = None) -> list[dict]:
        query = """SELECT id, kind, content_class, title, master_text, weekly_theme,
                          content_lane, value_units_json, product_bridge_position,
                          product_url, owner_voice_media_ref, media_approved,
                          qa_approved, release_approved, status, scheduled_at,
                          created_at, updated_at
                   FROM content_posts"""
        params: tuple = ()
        if status:
            query += " WHERE status=?"
            params = (status,)
        query += " ORDER BY COALESCE(scheduled_at, created_at) DESC"
        rows = self.database.rows(query, params)
        import json
        for row in rows:
            row["value_units"] = json.loads(row.pop("value_units_json") or "[]")
            row["variants"] = self.content.variants(row["id"])
        return rows

    def prepare_media_upload(self, payload: dict) -> dict:
        if self.media_store is None:
            raise RuntimeError("temporary R2 storage is not configured")
        filename = str(payload.get("filename", "")).strip()
        media_kind = str(payload.get("media_kind", "")).strip()
        if not filename:
            raise ValueError("filename is required")
        if media_kind not in {"image", "audio", "video", "render_asset"}:
            raise ValueError("unsupported media kind")
        prepared = self.media_store.prepare_upload(
            filename=filename,
            media_kind=media_kind,
        )
        self.media.register(
            object_key=prepared.media_ref,
            media_kind=media_kind,
            expires_at=prepared.expires_at,
        )
        return {
            "media_ref": prepared.media_ref,
            "upload_url": prepared.upload_url,
            "expires_at": prepared.expires_at.isoformat(),
        }

    def generate_social_image(self, payload: dict) -> dict:
        if os.getenv("GOLIDE_ENABLE_PAID_PRODUCTION", "").strip() != "1":
            raise RuntimeError(
                "paid image generation is locked; enable paid production only for an approved creative"
            )
        if self.media_store is None:
            raise RuntimeError("temporary R2 storage is not configured")

        profile = SocialImageProfile(self.root / "config/social-image-profile.json")
        prompt = profile.build_prompt(
            hook=str(payload.get("hook", "")),
            concept=str(payload.get("concept", "")),
            context=str(payload.get("context", "")),
        )
        from golide_engine.providers.openai_media import OpenAIImageProvider
        provider = OpenAIImageProvider(profile.model, profile.quality)

        with tempfile.TemporaryDirectory(prefix="golide-social-image-") as temp:
            temp_root = Path(temp)
            master = temp_root / "master.png"
            meta = temp_root / "meta-4x5.jpg"
            square = temp_root / "square-1x1.jpg"
            output = provider.create_image(prompt, master, "1024x1536")
            profile.adapt(master, meta, square)

            meta_upload = self.media_store.upload_bytes(
                filename="golide-post-meta-4x5.jpg",
                media_kind="image",
                data=meta.read_bytes(),
                content_type="image/jpeg",
            )
            square_upload = self.media_store.upload_bytes(
                filename="golide-post-square-1x1.jpg",
                media_kind="image",
                data=square.read_bytes(),
                content_type="image/jpeg",
            )

        for prepared in (meta_upload, square_upload):
            self.media.register(
                object_key=prepared.media_ref,
                media_kind="image",
                expires_at=prepared.expires_at,
            )
        return {
            "meta_4x5": {
                "media_ref": meta_upload.media_ref,
                "preview_url": self.media_store.resolve(meta_upload.media_ref),
                "expires_at": meta_upload.expires_at.isoformat(),
            },
            "square_1x1": {
                "media_ref": square_upload.media_ref,
                "preview_url": self.media_store.resolve(square_upload.media_ref),
                "expires_at": square_upload.expires_at.isoformat(),
            },
            "provider_request_id": output.request_id,
            "approval_required": True,
        }

    def create_post(self, payload: dict) -> dict:
        content_class = ContentClass(str(payload.get("content_class", "post")))
        raw_units = [str(item).strip() for item in payload.get("value_units", []) if str(item).strip()]
        bridge_raw = payload.get("product_bridge_position")
        bridge_position = int(bridge_raw) if bridge_raw not in (None, "", 0, "0") else None
        product_url = str(payload.get("product_url", "")).strip()

        if content_class is ContentClass.POST:
            raw_units = list(self.policy.validate_post_structure(raw_units, bridge_position, product_url))
            if bridge_position is not None and product_url not in raw_units[bridge_position - 1]:
                raw_units[bridge_position - 1] = (
                    raw_units[bridge_position - 1].rstrip() + "\n" + product_url
                )

        variants = []
        for item in payload.get("variants", []):
            parts = tuple(raw_units) if content_class is ContentClass.POST else tuple(
                str(value).strip() for value in item.get("parts", []) if str(value).strip()
            )
            body = str(item.get("body", "")).strip()
            if not body and parts and content_class is ContentClass.POST:
                body = "\n\n".join(parts)
            variants.append(
                PlatformVariant(
                    platform=str(item.get("platform", "")),
                    body=body,
                    title=str(item.get("title", "")),
                    media_ref=item.get("media_ref"),
                    parts=parts,
                )
            )

        self.policy.validate_route(content_class, (item.platform for item in variants))
        scheduled_raw = payload.get("scheduled_at")
        scheduled_at = datetime.fromisoformat(str(scheduled_raw)) if scheduled_raw else None

        master_text = str(payload.get("master_text", "")).strip()
        if not master_text and raw_units:
            master_text = "\n\n".join(raw_units)

        draft = ContentDraft.build(
            master_text,
            variants,
            title=str(payload.get("title", "")),
            content_class=content_class,
            weekly_theme=str(payload.get("weekly_theme", "")),
            content_lane=str(payload.get("content_lane", "")),
            value_units=raw_units,
            product_bridge_position=bridge_position,
            product_url=product_url,
            owner_voice_media_ref=payload.get("owner_voice_media_ref"),
            media_approved=bool(payload.get("media_approved", False)),
            qa_approved=bool(payload.get("qa_approved", False)),
            release_approved=bool(payload.get("release_approved", False)),
        )
        post_id = self.content.create(draft, scheduled_at=scheduled_at)
        media_refs = {
            item.media_ref for item in variants if item.media_ref
        }
        if draft.owner_voice_media_ref:
            media_refs.add(draft.owner_voice_media_ref)
        for media_ref in media_refs:
            self.media.attach_to_post(
                media_ref,
                post_id,
                scheduled_at=scheduled_at,
            )
        return {
            "id": post_id,
            "status": self.content.get(post_id).status,
            "content_class": content_class.value,
        }

    def connection_rows(self) -> list[dict]:
        return [
            {
                "id": item.id,
                "platform": item.platform,
                "account_label": item.account_label,
                "external_account_id": item.external_account_id,
                "transport": item.transport,
                "status": item.status,
            }
            for item in self.connections.list()
        ]

    def inbox_rows(self) -> list[dict]:
        result = []
        for thread in self.inbox.open_threads():
            messages = self.inbox.messages(thread.id)
            result.append({
                "id": thread.id,
                "platform": thread.platform,
                "participant_ref": thread.participant_ref,
                "subject": thread.subject,
                "status": thread.status,
                "last_message_at": thread.last_message_at,
                "messages": [
                    {
                        "direction": message.direction,
                        "body": message.body,
                        "created_at": message.created_at,
                    }
                    for message in messages
                ],
            })
        return result
