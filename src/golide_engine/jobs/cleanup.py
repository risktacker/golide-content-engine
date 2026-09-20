from __future__ import annotations

from datetime import datetime

from golide_engine.storage.temporary import (
    TemporaryMediaRepository,
    TemporaryMediaStore,
)


def cleanup_temporary_media(
    repository: TemporaryMediaRepository,
    store: TemporaryMediaStore,
    *,
    now: datetime | None = None,
) -> list[str]:
    """Delete confirmed or expired temporary objects and return deleted keys."""
    deleted: list[str] = []
    for media in repository.ready_or_expired(now):
        store.delete(media.object_key)
        repository.mark_deleted(media.id)
        deleted.append(media.object_key)
    return deleted
