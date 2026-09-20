from __future__ import annotations

from datetime import datetime

from golide_engine.db import ContentRepository
from golide_engine.db.connections import ConnectionRepository
from golide_engine.db.inbox import InboxRepository
from golide_engine.engine import ContentDraft, PlatformVariant
from golide_engine.storage import Database
from golide_engine.storage.r2 import R2TemporaryMediaStore
from golide_engine.storage.temporary import TemporaryMediaRepository


class StudioService:
    """Small JSON-facing service layer. It stores records, never media bytes."""

    def __init__(
        self,
        database: Database,
        *,
        media_store: R2TemporaryMediaStore | None = None,
    ):
        self.database = database
        self.content = ContentRepository(database)
        self.connections = ConnectionRepository(database)
        self.inbox = InboxRepository(database)
        self.media = TemporaryMediaRepository(database)
        self.media_store = media_store

    def overview(self) -> dict:
        def count(query: str, params: tuple = ()) -> int:
            rows = self.database.rows(query, params)
            return int(rows[0]["count"]) if rows else 0

        return {
            "posts_today": count(
                """SELECT COUNT(*) count FROM content_posts
                   WHERE date(created_at)=date('now')"""
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
            "r2_ready": self.media_store is not None,
        }

    def posts(self, status: str | None = None) -> list[dict]:
        query = """SELECT id, kind, title, master_text, status, scheduled_at,
                          created_at, updated_at
                   FROM content_posts"""
        params: tuple = ()
        if status:
            query += " WHERE status=?"
            params = (status,)
        query += " ORDER BY COALESCE(scheduled_at, created_at) DESC"
        rows = self.database.rows(query, params)
        for row in rows:
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

    def create_post(self, payload: dict) -> dict:
        variants = [
            PlatformVariant(
                platform=str(item.get("platform", "")),
                body=str(item.get("body", "")),
                title=str(item.get("title", "")),
                media_ref=item.get("media_ref"),
            )
            for item in payload.get("variants", [])
        ]
        scheduled_raw = payload.get("scheduled_at")
        scheduled_at = datetime.fromisoformat(str(scheduled_raw)) if scheduled_raw else None
        draft = ContentDraft.build(
            str(payload.get("master_text", "")),
            variants,
            title=str(payload.get("title", "")),
            kind=str(payload.get("kind", "social")),
        )
        post_id = self.content.create(draft, scheduled_at=scheduled_at)
        for media_ref in {item.media_ref for item in variants if item.media_ref}:
            self.media.attach_to_post(
                media_ref,
                post_id,
                scheduled_at=scheduled_at,
            )
        return {"id": post_id, "status": self.content.get(post_id).status}

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
