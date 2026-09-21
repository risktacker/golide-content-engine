from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from golide_engine.engine.content import ContentClass, ContentDraft
from golide_engine.engine.policy import ContentPolicy
from golide_engine.storage import Database
from golide_engine.storage.database import utc_now


@dataclass(frozen=True)
class StoredPost:
    id: str
    kind: str
    content_class: str
    title: str
    master_text: str
    status: str
    scheduled_at: str | None
    weekly_theme: str
    content_lane: str
    value_units_json: str
    product_bridge_position: int | None
    product_url: str
    owner_voice_media_ref: str | None
    media_approved: int
    qa_approved: int
    release_approved: int

    @property
    def value_units(self) -> tuple[str, ...]:
        try:
            return tuple(json.loads(self.value_units_json or "[]"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return ()


class ContentRepository:
    """Persist lightweight distribution records. Media bytes never enter SQLite."""

    def __init__(self, database: Database, policy: ContentPolicy | None = None):
        self.database = database
        self.policy = policy or ContentPolicy()

    def create(
        self,
        draft: ContentDraft,
        *,
        scheduled_at: datetime | None = None,
        post_id: str | None = None,
    ) -> str:
        if scheduled_at:
            self.policy.validate_ready_for_schedule(draft)
        else:
            self.policy.validate_route(
                draft.content_class,
                (item.platform for item in draft.variants),
                require_complete=False,
            )
            self.policy.validate_lane(draft.content_lane)
            self.policy.validate_variant_copy(draft.variants)
            if draft.content_class is ContentClass.POST and draft.value_units:
                self.policy.validate_post_structure(
                    draft.value_units,
                    draft.product_bridge_position,
                    draft.product_url,
                )

        pid = post_id or str(uuid4())
        now = utc_now()
        schedule = _iso(scheduled_at) if scheduled_at else None
        status = "scheduled" if schedule else "draft"
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO content_posts
                   (id, kind, content_class, title, master_text, weekly_theme, content_lane,
                    value_units_json, product_bridge_position, product_url, owner_voice_media_ref,
                    media_approved, qa_approved, release_approved,
                    status, scheduled_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    pid,
                    draft.kind.value,
                    draft.content_class.value,
                    draft.title,
                    draft.master_text,
                    draft.weekly_theme,
                    draft.content_lane,
                    json.dumps(list(draft.value_units), ensure_ascii=False),
                    draft.product_bridge_position,
                    draft.product_url,
                    draft.owner_voice_media_ref,
                    int(draft.media_approved),
                    int(draft.qa_approved),
                    int(draft.release_approved),
                    status,
                    schedule,
                    now,
                    now,
                ),
            )
            for variant in draft.variants:
                connection.execute(
                    """INSERT INTO social_variants
                       (id, post_id, platform, title, body, parts_json, media_ref,
                        status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
                    (
                        str(uuid4()),
                        pid,
                        variant.platform,
                        variant.title,
                        variant.body,
                        json.dumps(list(variant.parts), ensure_ascii=False),
                        variant.media_ref,
                        now,
                        now,
                    ),
                )
        return pid

    def schedule(self, post_id: str, scheduled_at: datetime) -> None:
        post = self.get(post_id)
        if post.status == "published":
            raise ValueError("published content cannot be rescheduled")
        draft = self.as_draft(post_id)
        self.policy.validate_ready_for_schedule(draft)
        self.database.execute(
            """UPDATE content_posts
               SET status='scheduled', scheduled_at=?, updated_at=?
               WHERE id=?""",
            (_iso(scheduled_at), utc_now(), post_id),
        )

    def due(self, now: datetime | None = None, *, content_class: str | None = None) -> list[StoredPost]:
        moment = _iso(now or datetime.now(timezone.utc))
        query = """SELECT id, kind, content_class, title, master_text, status, scheduled_at,
                          weekly_theme, content_lane, value_units_json, product_bridge_position,
                          product_url, owner_voice_media_ref, media_approved, qa_approved,
                          release_approved
                   FROM content_posts
                   WHERE status='scheduled' AND scheduled_at IS NOT NULL AND scheduled_at <= ?"""
        params: tuple[Any, ...] = (moment,)
        if content_class:
            query += " AND content_class=?"
            params += (content_class,)
        query += " ORDER BY scheduled_at ASC, created_at ASC"
        return [StoredPost(**row) for row in self.database.rows(query, params)]

    def get(self, post_id: str) -> StoredPost:
        rows = self.database.rows(
            """SELECT id, kind, content_class, title, master_text, status, scheduled_at,
                      weekly_theme, content_lane, value_units_json, product_bridge_position,
                      product_url, owner_voice_media_ref, media_approved, qa_approved,
                      release_approved
               FROM content_posts WHERE id=?""",
            (post_id,),
        )
        if not rows:
            raise KeyError(post_id)
        return StoredPost(**rows[0])

    def variants(self, post_id: str) -> list[dict[str, Any]]:
        rows = self.database.rows(
            """SELECT id, post_id, platform, title, body, parts_json, media_ref, status,
                      platform_content_id, published_url, last_error, published_at
               FROM social_variants
               WHERE post_id=?
               ORDER BY platform ASC""",
            (post_id,),
        )
        for row in rows:
            try:
                row["parts"] = json.loads(row.pop("parts_json") or "[]")
            except (TypeError, ValueError, json.JSONDecodeError):
                row["parts"] = []
        return rows

    def as_draft(self, post_id: str) -> ContentDraft:
        post = self.get(post_id)
        from golide_engine.engine.content import PlatformVariant
        return ContentDraft.build(
            post.master_text,
            [
                PlatformVariant(
                    platform=row["platform"],
                    title=row["title"],
                    body=row["body"],
                    media_ref=row["media_ref"],
                    parts=tuple(row.get("parts") or ()),
                )
                for row in self.variants(post_id)
            ],
            title=post.title,
            content_class=post.content_class,
            weekly_theme=post.weekly_theme,
            content_lane=post.content_lane,
            value_units=post.value_units,
            product_bridge_position=post.product_bridge_position,
            product_url=post.product_url,
            owner_voice_media_ref=post.owner_voice_media_ref,
            media_approved=bool(post.media_approved),
            qa_approved=bool(post.qa_approved),
            release_approved=bool(post.release_approved),
        )

    def assert_publishable(self, post_id: str) -> None:
        draft = self.as_draft(post_id)
        self.policy.validate_ready_for_schedule(draft)
        if draft.content_class is not ContentClass.POST:
            raise ValueError(
                "social publisher handles static posts only; Shorts and long-form use the video release lane"
            )

    def begin_publish(self, post_id: str) -> None:
        self.assert_publishable(post_id)
        self.database.execute(
            """UPDATE content_posts
               SET status='publishing', updated_at=?
               WHERE id=? AND status IN ('draft', 'scheduled', 'partial', 'failed')""",
            (utc_now(), post_id),
        )

    def record_attempt(
        self, *, post_id: str, variant_id: str, platform: str,
        status: str, remote_id: str | None = None, error: str | None = None,
    ) -> None:
        self.database.execute(
            """INSERT INTO publish_attempts
               (post_id, variant_id, platform, status, remote_id, error, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (post_id, variant_id, platform, status, remote_id, error, utc_now()),
        )

    def mark_variant_published(self, variant_id: str, *, content_id: str, url: str | None) -> None:
        now = utc_now()
        self.database.execute(
            """UPDATE social_variants
               SET status='published', platform_content_id=?, published_url=?,
                   last_error=NULL, published_at=?, updated_at=?
               WHERE id=?""",
            (content_id, url, now, now, variant_id),
        )

    def mark_variant_failed(self, variant_id: str, error: str) -> None:
        self.database.execute(
            """UPDATE social_variants
               SET status='failed', last_error=?, updated_at=? WHERE id=?""",
            (error[:2000], utc_now(), variant_id),
        )

    def refresh_status(self, post_id: str) -> str:
        variants = self.variants(post_id)
        if not variants:
            raise ValueError("post has no platform variants")
        statuses = {item["status"] for item in variants}
        if statuses == {"published"}:
            status = "published"
        elif "published" in statuses:
            status = "partial"
        elif statuses == {"failed"}:
            status = "failed"
        else:
            status = "publishing"
        self.database.execute(
            "UPDATE content_posts SET status=?, updated_at=? WHERE id=?",
            (status, utc_now(), post_id),
        )
        return status


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
