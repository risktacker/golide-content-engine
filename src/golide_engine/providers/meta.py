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


class MetaGraph:
    def __init__(
        self,
        *,
        api_version: str,
        access_token: str,
        http: JsonHttpClient | None = None,
    ):
        api_version = api_version.strip()
        access_token = access_token.strip()
        if not api_version or not access_token:
            raise ValueError("Meta API version and access token are required")
        self.api_version = api_version
        self.access_token = access_token
        self.http = http or UrlLibJsonClient()

    def url(self, edge: str) -> str:
        return f"https://graph.facebook.com/{self.api_version}/{edge.lstrip('/')}"

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
    ):
        self.graph = MetaGraph(
            api_version=api_version,
            access_token=access_token,
            http=http,
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
        payload: dict[str, object] = {"caption": request.body}
        if _looks_like_video(media_url):
            payload.update(
                {
                    "media_type": "REELS",
                    "video_url": media_url,
                    "share_to_feed": "true",
                }
            )
        else:
            payload["image_url"] = media_url

        created = self.graph.post(f"{self.instagram_user_id}/media", **payload)
        container_id = str(created.get("id", ""))
        if not container_id:
            raise RuntimeError("Instagram did not return a media container id")

        self._wait_until_ready(container_id)
        published = self.graph.post(
            f"{self.instagram_user_id}/media_publish",
            creation_id=container_id,
        )
        media_id = str(published.get("id", ""))
        if not media_id:
            raise RuntimeError("Instagram did not return a published media id")
        return PublishResult(content_id=media_id, url=None)

    def _wait_until_ready(self, container_id: str) -> None:
        for attempt in range(self.poll_attempts):
            status = self.graph.get(container_id, fields="status_code,status")
            code = str(status.get("status_code", "")).upper()
            if code == "FINISHED":
                return
            if code in {"ERROR", "EXPIRED"}:
                raise RuntimeError(
                    f"Instagram media container failed: {status.get('status') or code}"
                )
            if attempt + 1 < self.poll_attempts:
                self.sleeper(self.poll_seconds)
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
        if not request.media_ref:
            result = self.graph.post(f"{self.page_id}/feed", message=request.body)
        else:
            media_url = _require_https_media(request.media_ref)
            if _looks_like_video(media_url):
                raise NotImplementedError(
                    "Facebook video/reel upload is handled by the dedicated video adapter, not the photo/text publisher"
                )
            result = self.graph.post(
                f"{self.page_id}/photos",
                url=media_url,
                caption=request.body,
            )
        content_id = str(result.get("post_id") or result.get("id") or "")
        if not content_id:
            raise RuntimeError("Facebook did not return a post id")
        return PublishResult(content_id=content_id, url=None)
