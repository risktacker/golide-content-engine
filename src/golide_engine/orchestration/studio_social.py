from __future__ import annotations

import os
from datetime import datetime, timezone

from golide_engine.providers.base import PublishRequest
from golide_engine.providers.linkedin import LinkedInProvider
from golide_engine.providers.meta import FacebookPageProvider, InstagramProvider
from golide_engine.providers.x import XProvider
from golide_engine.storage.r2 import r2_store_from_environment
from golide_engine.studio_bridge import StudioBridge


class StudioSocialPublisher:
    """Publish due D1-backed static posts from the credentialed Actions runtime."""

    def __init__(self, *, bridge: StudioBridge | None = None):
        self.bridge = bridge or StudioBridge(
            os.getenv("GOLIDE_STUDIO_BASE_URL", "https://studio.golidee.com")
        )
        self.providers = {}
        meta_version = os.getenv("GOLIDE_META_API_VERSION", "").strip()
        linkedin_version = os.getenv("GOLIDE_LINKEDIN_VERSION", "").strip()
        try:
            c = self.bridge.social_credentials("instagram")
            self.providers["instagram"] = InstagramProvider(
                api_version=meta_version, access_token=str(c["access_token"]),
                instagram_user_id=str(c.get("account_id") or ""),
                graph_host=str(c.get("graph_host") or "graph.instagram.com"),
            )
        except Exception:
            self.providers.pop("instagram", None)
        try:
            c = self.bridge.social_credentials("facebook")
            self.providers["facebook"] = FacebookPageProvider(
                api_version=meta_version, page_access_token=str(c["access_token"]),
                page_id=str(c.get("page_id") or c.get("account_id") or ""),
            )
        except Exception:
            self.providers.pop("facebook", None)
        try:
            c = self.bridge.social_credentials("linkedin")
            self.providers["linkedin"] = LinkedInProvider(
                access_token=str(c["access_token"]),
                author_urn=str(c.get("author_urn") or ""),
                linkedin_version=linkedin_version,
            )
        except Exception:
            self.providers.pop("linkedin", None)
        try:
            c = self.bridge.social_credentials("x")
            self.providers["x"] = XProvider(user_access_token=str(c["access_token"]))
        except Exception:
            self.providers.pop("x", None)
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
