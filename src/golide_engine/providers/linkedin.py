from __future__ import annotations

import re
from pathlib import PurePosixPath

from .base import PublishRequest, PublishResult, SocialProvider
from .binary_http import (
    BinaryHttpClient,
    UrlLibBinaryHttpClient,
    probe_media,
    read_range,
)
from .json_api import JsonApiClient, UrlLibJsonApiClient
from .meta import _require_publish_enabled


class LinkedInProvider(SocialProvider):
    platform = "linkedin"

    def __init__(
        self,
        *,
        access_token: str,
        author_urn: str,
        linkedin_version: str,
        http: JsonApiClient | None = None,
        binary_http: BinaryHttpClient | None = None,
    ):
        self.access_token = access_token.strip()
        self.author_urn = author_urn.strip()
        self.linkedin_version = linkedin_version.strip()
        self.http = http or UrlLibJsonApiClient()
        self.binary_http = binary_http or UrlLibBinaryHttpClient()
        if not self.access_token or not self.author_urn:
            raise ValueError("LinkedIn token and author URN are required")
        if not re.fullmatch(r"\d{6}", self.linkedin_version):
            raise ValueError("LinkedIn-Version must use YYYYMM format")
        if not self.author_urn.startswith("urn:li:"):
            raise ValueError("LinkedIn author must be a URN")

    @property
    def api_headers(self) -> dict[str, str]:
        return {
            "Linkedin-Version": self.linkedin_version,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def publish(self, request: PublishRequest) -> PublishResult:
        _require_publish_enabled()
        media_urn = None
        if request.media_ref:
            probe = probe_media(self.binary_http, request.media_ref)
            if probe.content_type.startswith("image/"):
                media_urn = self._upload_image(request.media_ref)
            elif probe.content_type == "video/mp4" or _suffix(request.media_ref) == ".mp4":
                media_urn = self._upload_video(request.media_ref, probe.size_bytes)
            else:
                raise ValueError(
                    f"LinkedIn media type is not supported: {probe.content_type}"
                )
        return self._create_post(request, media_urn)

    def _upload_image(self, source_url: str) -> str:
        initialized = self.http.post(
            "https://api.linkedin.com/rest/images?action=initializeUpload",
            bearer_token=self.access_token,
            headers=self.api_headers,
            json_body={"initializeUploadRequest": {"owner": self.author_urn}},
        )
        value = initialized.data.get("value") or {}
        upload_url = str(value.get("uploadUrl", ""))
        image_urn = str(value.get("image", ""))
        if not upload_url or not image_urn:
            raise RuntimeError("LinkedIn image initialization returned incomplete data")
        source = self.binary_http.get(source_url)
        self.binary_http.put(
            upload_url,
            source.data,
            content_type="application/octet-stream",
        )
        return image_urn

    def _upload_video(self, source_url: str, size_bytes: int) -> str:
        if size_bytes < 75 * 1024 or size_bytes > 500 * 1024 * 1024:
            raise ValueError("LinkedIn feed video must be between 75 KB and 500 MB")
        initialized = self.http.post(
            "https://api.linkedin.com/rest/videos?action=initializeUpload",
            bearer_token=self.access_token,
            headers=self.api_headers,
            json_body={
                "initializeUploadRequest": {
                    "owner": self.author_urn,
                    "fileSizeBytes": size_bytes,
                    "uploadCaptions": False,
                    "uploadThumbnail": False,
                }
            },
        )
        value = initialized.data.get("value") or {}
        video_urn = str(value.get("video", ""))
        upload_token = str(value.get("uploadToken", ""))
        instructions = value.get("uploadInstructions") or []
        if not video_urn or not instructions:
            raise RuntimeError("LinkedIn video initialization returned incomplete data")

        etags: list[str] = []
        for item in instructions:
            first = int(item["firstByte"])
            last = int(item["lastByte"])
            upload_url = str(item["uploadUrl"])
            chunk = read_range(self.binary_http, source_url, first, last)
            uploaded = self.binary_http.put(
                upload_url,
                chunk,
                content_type="application/octet-stream",
            )
            etag = uploaded.headers.get("etag", "").strip('"')
            if not etag:
                raise RuntimeError("LinkedIn video part upload did not return an ETag")
            etags.append(etag)

        self.http.post(
            "https://api.linkedin.com/rest/videos?action=finalizeUpload",
            bearer_token=self.access_token,
            headers=self.api_headers,
            json_body={
                "finalizeUploadRequest": {
                    "video": video_urn,
                    "uploadToken": upload_token,
                    "uploadedPartIds": etags,
                }
            },
        )
        return video_urn

    def _create_post(
        self,
        request: PublishRequest,
        media_urn: str | None,
    ) -> PublishResult:
        payload: dict = {
            "author": self.author_urn,
            "commentary": request.body.strip() or "\n\n".join(request.parts),
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        if media_urn:
            payload["content"] = {
                "media": {
                    "title": request.title or "GOLIDE",
                    "id": media_urn,
                }
            }
        response = self.http.post(
            "https://api.linkedin.com/rest/posts",
            bearer_token=self.access_token,
            headers=self.api_headers,
            json_body=payload,
        )
        post_id = response.headers.get("x-restli-id") or str(response.data.get("id", ""))
        if not post_id:
            raise RuntimeError("LinkedIn did not return a post id")
        url = (
            f"https://www.linkedin.com/feed/update/{post_id}/"
            if post_id.startswith("urn:li:")
            else None
        )
        return PublishResult(content_id=post_id, url=url)


def _suffix(url: str) -> str:
    return PurePosixPath(url.split("?", 1)[0].lower()).suffix
