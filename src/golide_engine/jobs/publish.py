from __future__ import annotations

from datetime import datetime

from golide_engine.db import ContentRepository
from golide_engine.engine.social import PublishSummary, SocialBridge
from golide_engine.storage.temporary import TemporaryMediaRepository


def publish_due(
    repository: ContentRepository,
    bridge: SocialBridge,
    *,
    now: datetime | None = None,
    media_repository: TemporaryMediaRepository | None = None,
) -> list[PublishSummary]:
    """Publish every due post once, oldest first.

    Successful remote confirmation only marks media ready for cleanup. Actual
    deletion remains a separate cleanup job.
    """
    results: list[PublishSummary] = []
    for post in repository.due(now):
        summary = bridge.publish_post(post.id)
        results.append(summary)
        if summary.status == "published" and media_repository is not None:
            media_repository.mark_post_confirmed(post.id)
    return results
