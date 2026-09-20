from __future__ import annotations

from .base import PublishRequest, PublishResult, SocialProvider
from .json_api import JsonApiClient, UrlLibJsonApiClient
from .meta import _require_publish_enabled


class XProvider(SocialProvider):
    platform = "x"

    def __init__(
        self,
        *,
        user_access_token: str,
        http: JsonApiClient | None = None,
    ):
        self.user_access_token = user_access_token.strip()
        self.http = http or UrlLibJsonApiClient()
        if not self.user_access_token:
            raise ValueError("X user access token is required")

    def publish(self, request: PublishRequest) -> PublishResult:
        _require_publish_enabled()
        if request.media_ref:
            raise NotImplementedError(
                "X media upload is not enabled yet; text publishing is available"
            )
        response = self.http.post(
            "https://api.x.com/2/tweets",
            bearer_token=self.user_access_token,
            json_body={"text": request.body},
        )
        data = response.data.get("data") or {}
        post_id = str(data.get("id", ""))
        if not post_id:
            raise RuntimeError("X did not return a post id")
        return PublishResult(
            content_id=post_id,
            url=f"https://x.com/i/web/status/{post_id}",
        )
