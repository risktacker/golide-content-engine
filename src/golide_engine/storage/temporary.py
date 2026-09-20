from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from .database import Database, utc_now


class TemporaryMediaStore(Protocol):
    def delete(self, object_key: str) -> None:
        ...


class MemoryMediaStore:
    """Test storage adapter; records deletions without touching external storage."""

    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete(self, object_key: str) -> None:
        self.deleted.append(object_key)


@dataclass(frozen=True)
class TemporaryMedia:
    id: str
    object_key: str
    media_kind: str
    post_id: str | None
    status: str
    expires_at: str


class TemporaryMediaRepository:
    def __init__(self, database: Database):
        self.database = database

    def register(
        self,
        *,
        object_key: str,
        media_kind: str,
        expires_at: datetime,
        post_id: str | None = None,
    ) -> str:
        object_key = object_key.strip()
        if not object_key:
            raise ValueError("object key is required")
        if media_kind not in {"image", "audio", "video", "render_asset"}:
            raise ValueError("unsupported temporary media kind")
        media_id = str(uuid4())
        self.database.execute(
            """INSERT INTO temporary_media
               (id, object_key, media_kind, post_id, status, expires_at, created_at)
               VALUES (?, ?, ?, ?, 'active', ?, ?)""",
            (media_id, object_key, media_kind, post_id, _iso(expires_at), utc_now()),
        )
        return media_id

    def mark_post_confirmed(self, post_id: str) -> int:
        post = self.database.rows(
            "SELECT status FROM content_posts WHERE id=?",
            (post_id,),
        )
        if not post or post[0]["status"] != "published":
            return 0
        variants = self.database.rows(
            """SELECT media_ref FROM social_variants
               WHERE post_id=? AND media_ref IS NOT NULL""",
            (post_id,),
        )
        keys = {row["media_ref"] for row in variants if row["media_ref"]}
        if not keys:
            return 0
        marked = 0
        with self.database.connect() as connection:
            for key in keys:
                cursor = connection.execute(
                    """UPDATE temporary_media
                       SET status='ready_for_cleanup'
                       WHERE object_key=? AND status='active'""",
                    (key,),
                )
                marked += cursor.rowcount
        return marked

    def ready_or_expired(self, now: datetime | None = None) -> list[TemporaryMedia]:
        moment = _iso(now or datetime.now(timezone.utc))
        rows = self.database.rows(
            """SELECT id, object_key, media_kind, post_id, status, expires_at
               FROM temporary_media
               WHERE status='ready_for_cleanup'
                  OR (status='active' AND expires_at <= ?)
               ORDER BY expires_at ASC""",
            (moment,),
        )
        return [TemporaryMedia(**row) for row in rows]

    def mark_deleted(self, media_id: str) -> None:
        self.database.execute(
            """UPDATE temporary_media
               SET status='deleted', deleted_at=?
               WHERE id=?""",
            (utc_now(), media_id),
        )


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
