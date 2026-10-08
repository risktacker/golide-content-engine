from __future__ import annotations

import base64
import time
from typing import Callable

from .base import PublishRequest, PublishResult, SocialProvider
from .binary_http import BinaryHttpClient, UrlLibBinaryHttpClient, probe_media, read_range
from .json_api import JsonApiClient, UrlLibJsonApiClient
from .meta import _require_publish_enabled


class XProvider(SocialProvider):
    platform = "x"

    def __init__(
        self,
        *,
        user_access_token: str,
        http: JsonApiClient | None = None,
        binary_http: BinaryHttpClient | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        max_status_checks: int = 30,
    ):
        self.user_access_token = user_access_token.strip()
        self.http = http or UrlLibJsonApiClient()
        self.binary_http = binary_http or UrlLibBinaryHttpClient()
        self.sleeper = sleeper
        self.max_status_checks = max_status_checks
        if not self.user_access_token:
            raise ValueError("X user access token is required")

    def publish(self, request: PublishRequest) -> PublishResult:
        _require_publish_enabled()
        media_id = None
        if request.media_ref:
            probe = probe_media(self.binary_http, request.media_ref)
            if probe.content_type.startswith("image/"):
                media_id = self._upload_image(request.media_ref)
            elif probe.content_type.startswith("video/"):
                media_id = self._upload_video(
                    request.media_ref,
                    probe.size_bytes,
                    probe.content_type,
                )
            else:
                raise ValueError(f"X media type is not supported: {probe.content_type}")

        from golide_engine.engine.social_copy import X_LIMIT, x_length

        # The post is the body; parts are replies under it (GOLIDE posts two).
        # Older records without a body post their parts as a thread.
        parts = tuple(item.strip() for item in request.parts if item.strip())
        texts = (request.body.strip(), *parts) if request.body.strip() else parts
        if not texts:
            raise ValueError("X post has no text")
        if len(texts) > 4:
            raise ValueError("an X post carries at most three replies")
        for text in texts:  # check everything before anything is posted (and billed)
            if x_length(text) > X_LIMIT:
                raise ValueError(f"X post is {x_length(text)} characters; X allows {X_LIMIT}")
        root_id = ""
        previous_id = ""
        warning = None
        for index, text in enumerate(texts):
            payload: dict = {"text": text}
            if index == 0 and media_id:
                payload["media"] = {"media_ids": [media_id]}
            if previous_id:
                payload["reply"] = {"in_reply_to_tweet_id": previous_id}
            try:
                response = self.http.post(
                    "https://api.x.com/2/tweets",
                    bearer_token=self.user_access_token,
                    json_body=payload,
                )
            except Exception as exc:
                if root_id:  # the post is live; a failed reply must not repost it
                    warning = f"reply {index} of {len(texts) - 1} was not posted: {str(exc)[:200]}"
                    break
                raise
            data = response.data.get("data") or {}
            post_id = str(data.get("id", ""))
            if not post_id:
                if root_id:
                    warning = f"reply {index} of {len(texts) - 1} was not posted"
                    break
                raise RuntimeError("X did not return a post id")
            root_id = root_id or post_id
            previous_id = post_id
        return PublishResult(
            content_id=root_id,
            url=f"https://x.com/i/web/status/{root_id}",
            warning=warning,
        )

    def _upload_image(self, source_url: str) -> str:
        source = self.binary_http.get(source_url)
        if len(source.data) > 5 * 1024 * 1024:
            raise ValueError("X image upload exceeds the 5 MB post-image limit")
        response = self.http.post(
            "https://api.x.com/2/media/upload",
            bearer_token=self.user_access_token,
            json_body={
                "media": base64.b64encode(source.data).decode("ascii"),
                "media_category": "tweet_image",
            },
        )
        data = response.data.get("data") or {}
        media_id = str(data.get("id", ""))
        if not media_id:
            raise RuntimeError("X did not return a media id")
        return media_id

    def _upload_video(
        self,
        source_url: str,
        size_bytes: int,
        content_type: str,
    ) -> str:
        initialized = self.http.post(
            "https://api.x.com/2/media/upload/initialize",
            bearer_token=self.user_access_token,
            json_body={
                "media_type": content_type,
                "total_bytes": size_bytes,
                "media_category": "tweet_video",
            },
        )
        data = initialized.data.get("data") or {}
        media_id = str(data.get("id", ""))
        if not media_id:
            raise RuntimeError("X did not return a chunked-upload media id")

        chunk_size = 4 * 1024 * 1024
        segment = 0
        for first in range(0, size_bytes, chunk_size):
            last = min(first + chunk_size - 1, size_bytes - 1)
            chunk = read_range(self.binary_http, source_url, first, last)
            self.http.post(
                f"https://api.x.com/2/media/upload/{media_id}/append",
                bearer_token=self.user_access_token,
                json_body={
                    "media": base64.b64encode(chunk).decode("ascii"),
                    "segment_index": segment,
                },
            )
            segment += 1
            if segment > 1000:
                raise ValueError("X video requires more than 1000 upload segments")

        finalized = self.http.post(
            f"https://api.x.com/2/media/upload/{media_id}/finalize",
            bearer_token=self.user_access_token,
            json_body=None,
        )
        self._wait_for_processing(media_id, finalized.data)
        return media_id

    def _wait_for_processing(self, media_id: str, payload: dict) -> None:
        data = payload.get("data") or {}
        processing = data.get("processing_info")
        if not processing:
            return
        for _ in range(self.max_status_checks):
            state = str(processing.get("state", "")).lower()
            if state == "succeeded":
                return
            if state == "failed":
                error = processing.get("error") or {}
                raise RuntimeError(
                    f"X media processing failed: {error.get('message') or error or 'unknown error'}"
                )
            delay = max(0.0, float(processing.get("check_after_secs") or 1))
            self.sleeper(delay)
            status = self.http.get(
                "https://api.x.com/2/media/upload",
                bearer_token=self.user_access_token,
                params={"command": "STATUS", "media_id": media_id},
            )
            processing = (status.data.get("data") or {}).get("processing_info")
            if not processing:
                return
        raise RuntimeError("X media processing did not finish before timeout")
