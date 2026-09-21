from __future__ import annotations

from dataclasses import dataclass

from golide_engine.db import ContentRepository
from golide_engine.engine.media import IdentityMediaResolver, MediaResolver
from golide_engine.providers import PublishRequest, SocialProvider


@dataclass(frozen=True)
class PublishSummary:
    post_id: str
    status: str
    published: int
    failed: int


class SocialBridge:
    """Publish approved static-post variants without leaking platform quirks."""

    def __init__(
        self,
        repository: ContentRepository,
        providers: list[SocialProvider],
        *,
        media_resolver: MediaResolver | None = None,
    ):
        self.repository = repository
        self.providers = {provider.platform: provider for provider in providers}
        self.media_resolver = media_resolver or IdentityMediaResolver()

    def publish_post(self, post_id: str) -> PublishSummary:
        self.repository.assert_publishable(post_id)
        self.repository.begin_publish(post_id)
        published = 0
        failed = 0

        for variant in self.repository.variants(post_id):
            if variant["status"] == "published":
                continue
            platform = variant["platform"]
            provider = self.providers.get(platform)
            if provider is None:
                error = f"no connected provider for {platform}"
                self.repository.mark_variant_failed(variant["id"], error)
                self.repository.record_attempt(
                    post_id=post_id, variant_id=variant["id"], platform=platform,
                    status="failed", error=error,
                )
                failed += 1
                continue

            try:
                media_ref = (
                    self.media_resolver.resolve(variant["media_ref"])
                    if variant["media_ref"] else None
                )
                request = PublishRequest(
                    post_id=post_id,
                    variant_id=variant["id"],
                    platform=platform,
                    body=variant["body"],
                    title=variant["title"],
                    media_ref=media_ref,
                    parts=tuple(variant.get("parts") or ()),
                )
                result = provider.publish(request)
            except Exception as exc:
                error = str(exc) or exc.__class__.__name__
                self.repository.mark_variant_failed(variant["id"], error)
                self.repository.record_attempt(
                    post_id=post_id, variant_id=variant["id"], platform=platform,
                    status="failed", error=error,
                )
                failed += 1
            else:
                self.repository.mark_variant_published(
                    variant["id"], content_id=result.content_id, url=result.url,
                )
                self.repository.record_attempt(
                    post_id=post_id, variant_id=variant["id"], platform=platform,
                    status="published", remote_id=result.content_id,
                )
                published += 1

        status = self.repository.refresh_status(post_id)
        return PublishSummary(post_id=post_id, status=status, published=published, failed=failed)
