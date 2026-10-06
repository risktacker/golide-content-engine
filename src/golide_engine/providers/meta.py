from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Callable

from .base import PublishRequest, PublishResult, SocialProvider
from .http import JsonHttpClient, UrlLibJsonClient


@dataclass(frozen=True)
class ManagedMetaAccount:
    page_id: str
    page_name: str
    instagram_user_id: str | None
    tasks: tuple[str, ...]


@dataclass(frozen=True)
class InstagramIdentity:
    id: str
    username: str


class MetaGraph:
    def __init__(
        self,
        *,
        api_version: str,
        access_token: str,
        http: JsonHttpClient | None = None,
        host: str = "graph.facebook.com",
    ):
        api_version = api_version.strip()
        access_token = access_token.strip()
        host = host.strip().strip("/")
        if not api_version or not access_token:
            raise ValueError("Meta API version and access token are required")
        if not host:
            raise ValueError("Meta Graph host is required")
        self.api_version = api_version
        self.access_token = access_token
        self.http = http or UrlLibJsonClient()
        self.host = host

    def url(self, edge: str) -> str:
        return f"https://{self.host}/{self.api_version}/{edge.lstrip('/')}"

    def get(self, edge: str, **params):
        payload = {"access_token": self.access_token, **params}
        return self.http.get(self.url(edge), params=payload).data

    def post(self, edge: str, **data):
        payload = {"access_token": self.access_token, **data}
        return self.http.post(self.url(edge), data=payload).data


def discover_managed_accounts(
    *,
    api_version: str,
    user_access_token: str,
    http: JsonHttpClient | None = None,
) -> list[ManagedMetaAccount]:
    graph = MetaGraph(
        api_version=api_version,
        access_token=user_access_token,
        http=http,
    )
    response = graph.get(
        "me/accounts",
        fields="name,tasks,instagram_business_account",
    )
    accounts: list[ManagedMetaAccount] = []
    for page in response.get("data", []):
        ig = page.get("instagram_business_account") or {}
        accounts.append(
            ManagedMetaAccount(
                page_id=str(page["id"]),
                page_name=str(page.get("name", "")),
                instagram_user_id=str(ig["id"]) if ig.get("id") else None,
                tasks=tuple(str(item) for item in page.get("tasks", [])),
            )
        )
    return accounts


def discover_instagram_identity(
    *,
    api_version: str,
    instagram_access_token: str,
    http: JsonHttpClient | None = None,
) -> InstagramIdentity:
    graph = MetaGraph(
        api_version=api_version,
        access_token=instagram_access_token,
        http=http,
        host="graph.instagram.com",
    )
    response = graph.get("me", fields="id,username")
    ig_id = str(response.get("id", "")).strip()
    username = str(response.get("username", "")).strip()
    if not ig_id:
        raise RuntimeError("Instagram Login did not return an account id")
    return InstagramIdentity(id=ig_id, username=username)


def social_publish_enabled() -> bool:
    return os.getenv("GOLIDE_ENABLE_SOCIAL_PUBLISH", "").strip() == "1"


def _require_publish_enabled() -> None:
    if not social_publish_enabled():
        raise RuntimeError(
            "real social publishing is locked; set GOLIDE_ENABLE_SOCIAL_PUBLISH=1 only after account verification"
        )


def _require_https_media(media_ref: str | None) -> str:
    if not media_ref or not media_ref.startswith("https://"):
        raise ValueError("Meta publishing requires a temporary HTTPS media URL")
    return media_ref


def _looks_like_video(url: str) -> bool:
    path = PurePosixPath(url.split("?", 1)[0].lower())
    return path.suffix in {".mp4", ".mov", ".m4v", ".mpeg", ".mpg", ".webm"}


class InstagramProvider(SocialProvider):
    platform = "instagram"

    def __init__(
        self,
        *,
        api_version: str,
        access_token: str,
        instagram_user_id: str,
        http: JsonHttpClient | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        poll_attempts: int = 30,
        poll_seconds: float = 2.0,
        graph_host: str = "graph.facebook.com",
    ):
        self.graph = MetaGraph(
            api_version=api_version,
            access_token=access_token,
            http=http,
            host=graph_host,
        )
        self.instagram_user_id = instagram_user_id.strip()
        self.sleeper = sleeper
        self.poll_attempts = poll_attempts
        self.poll_seconds = poll_seconds
        if not self.instagram_user_id:
            raise ValueError("Instagram professional account id is required")

    def publish(self, request: PublishRequest) -> PublishResult:
        _require_publish_enabled()
        media_url = _require_https_media(request.media_ref)
        body = request.body.strip() or "\n\n".join(request.parts)
        if request.extra_media and not _looks_like_video(media_url):
            try:
                return self._publish_carousel(media_url, request.extra_media, body)
            except Exception as exc:  # never lose the post: fall back to the cover alone
                print({"status": "carousel_fallback_single_image", "error": str(exc)})
        payload: dict[str, object] = {"caption": body}
        if _looks_like_video(media_url):
            payload.update(
                {
                    "media_type": "REELS",
                    "video_url": media_url,
                    "share_to_feed": "true",
                }
            )
            if request.cover_url:
                payload["cover_url"] = request.cover_url
        else:
            payload["image_url"] = media_url

        created = self.graph.post(f"{self.instagram_user_id}/media", **payload)
        container_id = str(created.get("id", ""))
        if not container_id:
            raise RuntimeError("Instagram did not return a media container id")

        # Reels need server-side processing (often 30 to 90 seconds); images
        # are ready almost at once.
        if "video_url" in payload:
            self._wait_until_ready(container_id, attempts=max(self.poll_attempts, 60), seconds=max(self.poll_seconds, 5.0))
        else:
            self._wait_until_ready(container_id)
        published = self.graph.post(
            f"{self.instagram_user_id}/media_publish",
            creation_id=container_id,
        )
        media_id = str(published.get("id", ""))
        if not media_id:
            raise RuntimeError("Instagram did not return a published media id")
        return PublishResult(content_id=media_id, url=None)

    def _publish_carousel(self, cover_url: str, extra: tuple[str, ...], caption: str) -> PublishResult:
        """Cover image first, then the text slides (Instagram allows up to 10)."""
        urls = [cover_url, *(_require_https_media(u) for u in extra)][:10]
        children: list[str] = []
        for url in urls:
            child = self.graph.post(f"{self.instagram_user_id}/media", image_url=url, is_carousel_item="true")
            child_id = str(child.get("id", ""))
            if not child_id:
                raise RuntimeError("Instagram did not return a carousel item id")
            self._wait_until_ready(child_id)
            children.append(child_id)
        parent = self.graph.post(
            f"{self.instagram_user_id}/media",
            media_type="CAROUSEL", children=",".join(children), caption=caption,
        )
        container_id = str(parent.get("id", ""))
        if not container_id:
            raise RuntimeError("Instagram did not return a carousel container id")
        self._wait_until_ready(container_id)
        published = self.graph.post(f"{self.instagram_user_id}/media_publish", creation_id=container_id)
        media_id = str(published.get("id", ""))
        if not media_id:
            raise RuntimeError("Instagram did not return a published media id")
        return PublishResult(content_id=media_id, url=None)

    def _wait_until_ready(self, container_id: str, *, attempts: int | None = None,
                          seconds: float | None = None) -> None:
        attempts = attempts or self.poll_attempts
        seconds = self.poll_seconds if seconds is None else seconds
        for attempt in range(attempts):
            status = self.graph.get(container_id, fields="status_code,status")
            code = str(status.get("status_code", "")).upper()
            if code == "FINISHED":
                return
            if code in {"ERROR", "EXPIRED"}:
                raise RuntimeError(
                    f"Instagram media container failed: {status.get('status') or code}"
                )
            if attempt + 1 < attempts:
                self.sleeper(seconds)
        raise RuntimeError("Instagram media container did not finish before timeout")


class FacebookPageProvider(SocialProvider):
    platform = "facebook"

    def __init__(
        self,
        *,
        api_version: str,
        page_access_token: str,
        page_id: str,
        http: JsonHttpClient | None = None,
    ):
        self.graph = MetaGraph(
            api_version=api_version,
            access_token=page_access_token,
            http=http,
        )
        self.page_id = page_id.strip()
        if not self.page_id:
            raise ValueError("Facebook Page id is required")

    def publish(self, request: PublishRequest) -> PublishResult:
        _require_publish_enabled()
        body = request.body.strip() or "\n\n".join(request.parts)
        if not request.media_ref:
            result = self.graph.post(f"{self.page_id}/feed", message=body)
        else:
            media_url = _require_https_media(request.media_ref)
            if _looks_like_video(media_url):
                if request.title.strip():  # a long landscape video, not a Reel
                    return self._publish_video(media_url, request.title.strip(), body)
                return self._publish_reel(media_url, body)
            result = self.graph.post(
                f"{self.page_id}/photos",
                url=media_url,
                caption=body,
            )
        content_id = str(result.get("post_id") or result.get("id") or "")
        if not content_id:
            raise RuntimeError("Facebook did not return a post id")
        return PublishResult(content_id=content_id, url=None)

    def _publish_video(self, video_url: str, title: str, description: str) -> PublishResult:
        """A normal Page video (keeps 16:9); Facebook fetches the hosted file itself."""
        result = self.graph.post(
            f"{self.page_id}/videos", file_url=video_url, title=title[:255], description=description,
            published="true",
        )
        video_id = str(result.get("id", ""))
        if not video_id:
            raise RuntimeError("Facebook did not return a video id")
        return PublishResult(content_id=video_id, url=f"https://www.facebook.com/{self.page_id}/videos/{video_id}")

    def _publish_reel(self, video_url: str, description: str) -> PublishResult:
        """Facebook Reels: start an upload, let Facebook fetch the hosted file, publish.

        Uses the Page Reels API (video_reels) with a hosted file URL, so the
        video never passes through this process.
        """
        started = self.graph.post(f"{self.page_id}/video_reels", upload_phase="start")
        video_id = str(started.get("video_id", ""))
        if not video_id:
            raise RuntimeError("Facebook did not return a reel video id")
        upload_url = str(started.get("upload_url") or
                         f"https://rupload.facebook.com/video-upload/{self.graph.api_version}/{video_id}")
        uploaded = self.graph.http.post(
            upload_url,
            data={},
            headers={"Authorization": f"OAuth {self.graph.access_token}", "file_url": video_url},
        ).data
        if not uploaded.get("success"):
            raise RuntimeError(f"Facebook reel upload failed: {uploaded}")
        finished = self.graph.post(
            f"{self.page_id}/video_reels",
            upload_phase="finish",
            video_id=video_id,
            video_state="PUBLISHED",
            description=description,
        )
        if not finished.get("success", True):
            raise RuntimeError(f"Facebook reel publish failed: {finished}")
        return PublishResult(content_id=str(finished.get("post_id") or video_id), url=None)
