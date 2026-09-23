from __future__ import annotations

import os
from datetime import datetime, timezone

from golide_engine.providers.base import PublishRequest
from golide_engine.providers.social_factory import provider_from_studio_credentials
from golide_engine.storage.r2 import r2_store_from_environment
from golide_engine.studio_bridge import StudioBridge


class StudioSocialPublisher:
    """Publish due D1-backed static posts from the credentialed Actions runtime."""

    def __init__(self, *, bridge: StudioBridge | None = None):
        self.bridge = bridge or StudioBridge(
            os.getenv("GOLIDE_STUDIO_BASE_URL", "https://studio.golidee.com")
        )
        self.providers = {}
        for platform in ("instagram", "facebook", "linkedin", "x"):
            try:
                credential = self.bridge.social_credentials(platform)
                provider = provider_from_studio_credentials(platform, credential)
            except Exception:
                # A disconnected provider must not block the other routes.
                continue
            self.providers[provider.platform] = provider
        self.media_store = r2_store_from_environment()
        if self.media_store is None:
            raise RuntimeError("R2 temporary storage is required for social publishing")

    def run_due(
        self,
        *,
        now: datetime | None = None,
        max_posts: int = 10,
    ) -> list[dict]:
        moment = now or datetime.now(timezone.utc)
        results: list[dict] = []

        for _ in range(max_posts):
            post = self.bridge.claim_due_social(moment)
            if not post:
                break

            last_status = post.get("status", "publishing")
            media_refs = {
                str(item.get("media_ref"))
                for item in post.get("variants", [])
                if item.get("media_ref")
            }

            for variant in post.get("variants", []):
                platform = str(variant.get("platform", "")).strip().lower()
                provider = self.providers.get(platform)
                if provider is None:
                    updated = self.bridge.report_social_variant(
                        post["id"],
                        variant["id"],
                        status="failed",
                        error=f"no connected provider for {platform}",
                    )
                    last_status = updated["status"]
                    continue

                try:
                    raw_ref = str(variant.get("media_ref") or "").strip()
                    media_url = (
                        self.media_store.resolve(raw_ref, expires_seconds=3600)
                        if raw_ref
                        else None
                    )
                    request = PublishRequest(
                        post_id=post["id"],
                        variant_id=variant["id"],
                        platform=platform,
                        body=str(variant.get("body") or ""),
                        title=str(variant.get("title") or ""),
                        media_ref=media_url,
                        parts=tuple(variant.get("parts") or ()),
                    )
                    published = provider.publish(request)
                except Exception as exc:
                    updated = self.bridge.report_social_variant(
                        post["id"],
                        variant["id"],
                        status="failed",
                        error=str(exc) or exc.__class__.__name__,
                    )
                else:
                    updated = self.bridge.report_social_variant(
                        post["id"],
                        variant["id"],
                        status="published",
                        remote_id=published.content_id,
                        url=published.url,
                    )
                last_status = updated["status"]

            if last_status == "published":
                deleted: list[str] = []
                for ref in sorted(media_refs):
                    try:
                        self.media_store.delete(ref)
                    except Exception:
                        continue
                    deleted.append(ref)
                if deleted:
                    self.bridge.mark_media_deleted(deleted)

            results.append({
                "post_id": post["id"],
                "status": last_status,
            })

        return results
