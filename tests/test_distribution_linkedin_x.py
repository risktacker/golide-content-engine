from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from golide_engine.providers.base import PublishRequest
from golide_engine.providers.json_api import ApiResponse
from golide_engine.providers.linkedin import LinkedInProvider
from golide_engine.providers.x import XProvider


class FakeJsonApi:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, *, bearer_token, json_body, headers=None):
        self.calls.append({
            "url": url,
            "bearer_token": bearer_token,
            "json_body": json_body,
            "headers": headers or {},
        })
        if not self.responses:
            raise AssertionError("unexpected POST")
        return self.responses.pop(0)


class LinkedInXProviderTests(unittest.TestCase):
    def request(self, platform: str, media_ref: str | None = None) -> PublishRequest:
        return PublishRequest(
            post_id="post-1",
            variant_id="variant-1",
            platform=platform,
            body="GOLIDE distribution post",
            media_ref=media_ref,
        )

    def test_linkedin_text_post_uses_current_posts_endpoint_contract(self) -> None:
        http = FakeJsonApi([
            ApiResponse(
                status=201,
                data={},
                headers={"x-restli-id": "urn:li:share:12345"},
            )
        ])
        provider = LinkedInProvider(
            access_token="secret-linkedin",
            author_urn="urn:li:person:abc123",
            linkedin_version="202609",
            http=http,
        )
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(self.request("linkedin"))
        self.assertEqual(result.content_id, "urn:li:share:12345")
        call = http.calls[0]
        self.assertEqual(call["url"], "https://api.linkedin.com/rest/posts")
        self.assertEqual(call["headers"]["X-Restli-Protocol-Version"], "2.0.0")
        self.assertEqual(call["headers"]["Linkedin-Version"], "202609")
        self.assertEqual(call["json_body"]["author"], "urn:li:person:abc123")
        self.assertEqual(call["json_body"]["lifecycleState"], "PUBLISHED")

    def test_linkedin_media_is_explicitly_blocked_until_upload_adapter_exists(self) -> None:
        provider = LinkedInProvider(
            access_token="secret",
            author_urn="urn:li:person:abc",
            linkedin_version="202609",
            http=FakeJsonApi([]),
        )
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            with self.assertRaisesRegex(NotImplementedError, "media upload"):
                provider.publish(
                    self.request("linkedin", "https://cdn.example.com/post.png")
                )

    def test_x_text_post_uses_v2_tweets(self) -> None:
        http = FakeJsonApi([
            ApiResponse(
                status=201,
                data={"data": {"id": "999", "text": "GOLIDE distribution post"}},
                headers={},
            )
        ])
        provider = XProvider(user_access_token="secret-x", http=http)
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(self.request("x"))
        self.assertEqual(result.content_id, "999")
        self.assertEqual(result.url, "https://x.com/i/web/status/999")
        call = http.calls[0]
        self.assertEqual(call["url"], "https://api.x.com/2/tweets")
        self.assertEqual(call["json_body"], {"text": "GOLIDE distribution post"})

    def test_x_media_is_explicitly_blocked_until_upload_adapter_exists(self) -> None:
        provider = XProvider(user_access_token="secret-x", http=FakeJsonApi([]))
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            with self.assertRaisesRegex(NotImplementedError, "media upload"):
                provider.publish(self.request("x", "https://cdn.example.com/post.jpg"))


if __name__ == "__main__":
    unittest.main()
