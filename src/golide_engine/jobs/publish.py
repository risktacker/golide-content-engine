from __future__ import annotations

from datetime import datetime

from golide_engine.db import ContentRepository
from golide_engine.engine.social import PublishSummary, SocialBridge


def publish_due(
    repository: ContentRepository,
    bridge: SocialBridge,
    *,
    now: datetime | None = None,
) -> list[PublishSummary]:
    """Publish every due post once, oldest first."""
    return [bridge.publish_post(post.id) for post in repository.due(now)]
