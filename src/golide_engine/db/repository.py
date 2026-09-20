from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from golide_engine.engine.content import ContentDraft
from golide_engine.storage import Database
from golide_engine.storage.database import utc_now


@dataclass(frozen=True)
class StoredPost:
    id: str
    kind: str
    title: str
    master_text: str
    status: str
    scheduled_at: str | None


class ContentRepository:
    """Persist lightweight distribution records. Media bytes never enter SQLite."""

    def __init__(self, database: Database):
        self.database = database

    def create(
        self,
        draft: ContentDraft,
        *,
        scheduled_at: datetime | None = None,
        post_id: str | None = None,
    ) -> str:
        pid = post_id or str(uuid4())
        now = utc_now()
        schedule = _iso(scheduled_at) if scheduled_at else None
        status = "scheduled" if schedule else "draft"
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO content_posts
                   (id, kind, title, master_text, status, scheduled_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (pid, draft.kind.value, draft.title, draft.master_text, status, schedule, now, now),
            )
            for variant in draft.variants:
                connection.execute(
                    """INSERT INTO social_variants
                       (id, post_id, platform, title, body, media_ref, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
                    (
                        str(uuid4()),
                        pid,
                        variant.platform,
                        variant.title,
                        variant.body,
                        variant.media_ref,
                        now,
                        now,
                    ),
                )
        return pid

    def schedule(self, post_id: str, scheduled_at: datetime) -> None:
        now = utc_now()
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT status FROM content_posts WHERE id=?",
                (post_id,),
            ).fetchone()
            if not row:
                raise KeyError(post_id)
            if row["status"] == "published":
                raise ValueError("published content cannot be rescheduled")
            connection.execute(
                """UPDATE content_posts
                   SET status='scheduled', scheduled_at=?, updated_at=?
                   WHERE id=?""",
                (_iso(scheduled_at), now, post_id),
            )

    def due(self, now: datetime | None = None) -> list[StoredPost]:
        moment = _iso(now or datetime.now(timezone.utc))
        rows = self.database.rows(
            """SELECT id, kind, title, master_text, status, scheduled_at
               FROM content_posts
               WHERE status='scheduled' AND scheduled_at IS NOT NULL AND scheduled_at <= ?
               ORDER BY scheduled_at ASC, created_at ASC""",
            (moment,),
        )
        return [StoredPost(**row) for row in rows]

    def get(self, post_id: str) -> StoredPost:
        rows = self.database.rows(
            """SELECT id, kind, title, master_text, status, scheduled_at
               FROM content_posts WHERE id=?""",
            (post_id,),
        )
        if not rows:
            raise KeyError(post_id)
        return StoredPost(**rows[0])

    def variants(self, post_id: str) -> list[dict[str, Any]]:
        return self.database.rows(
            """SELECT id, post_id, platform, title, body, media_ref, status,
                      platform_content_id, published_url, last_error, published_at
               FROM social_variants
               WHERE post_id=?
               ORDER BY platform ASC""",
            (post_id,),
        )

    def begin_publish(self, post_id: str) -> None:
        self.database.execute(
            """UPDATE content_posts
               SET status='publishing', updated_at=?
               WHERE id=? AND status IN ('draft', 'scheduled', 'partial', 'failed')""",
            (utc_now(), post_id),
        )

    def record_attempt(
        self,
        *,
        post_id: str,
        variant_id: str,
        platform: str,
        status: str,
        remote_id: str | None = None,
        error: str | None = None,
    ) -> None:
        self.database.execute(
            """INSERT INTO publish_attempts
               (post_id, variant_id, platform, status, remote_id, error, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (post_id, variant_id, platform, status, remote_id, error, utc_now()),
        )

    def mark_variant_published(
        self,
        variant_id: str,
        *,
        content_id: str,
        url: str | None,
    ) -> None:
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
               SET status='failed', last_error=?, updated_at=?
               WHERE id=?""",
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
