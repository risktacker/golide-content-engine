from __future__ import annotations

import re

from .base import PublishRequest, PublishResult, SocialProvider
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
    ):
        self.access_token = access_token.strip()
        self.author_urn = author_urn.strip()
        self.linkedin_version = linkedin_version.strip()
        self.http = http or UrlLibJsonApiClient()
        if not self.access_token or not self.author_urn:
            raise ValueError("LinkedIn token and author URN are required")
        if not re.fullmatch(r"\d{6}", self.linkedin_version):
            raise ValueError("LinkedIn-Version must use YYYYMM format")
        if not self.author_urn.startswith("urn:li:"):
            raise ValueError("LinkedIn author must be a URN")

    def publish(self, request: PublishRequest) -> PublishResult:
        _require_publish_enabled()
        if request.media_ref:
            raise NotImplementedError(
                "LinkedIn media upload is not enabled yet; text publishing is available"
            )
        response = self.http.post(
            "https://api.linkedin.com/rest/posts",
            bearer_token=self.access_token,
            headers={
                "Linkedin-Version": self.linkedin_version,
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json_body={
                "author": self.author_urn,
                "commentary": request.body,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            },
        )
        post_id = response.headers.get("x-restli-id") or str(response.data.get("id", ""))
        if not post_id:
            raise RuntimeError("LinkedIn did not return a post id")
        return PublishResult(content_id=post_id)
