from __future__ import annotations

from datetime import datetime

from golide_engine.db import ContentRepository


def schedule_post(repository: ContentRepository, post_id: str, scheduled_at: datetime) -> None:
    repository.schedule(post_id, scheduled_at)
