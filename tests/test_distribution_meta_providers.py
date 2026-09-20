from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from golide_engine.providers.base import PublishRequest
from golide_engine.providers.http import JsonResponse
from golide_engine.providers.meta import (
    FacebookPageProvider,
    InstagramProvider,
    discover_managed_accounts,
)


class FakeHttp:
    def __init__(self, *, gets=None, posts=None):
        self.gets = list(gets or [])
        self.posts = list(posts or [])
        self.calls = []

    def get(self, url, *, params=None):
        self.calls.append(("GET", url, params or {}))
        if not self.gets:
            raise AssertionError("unexpected GET")
        return JsonResponse(200, self.gets.pop(0))

    def post(self, url, *, data=None):
        self.calls.append(("POST", url, data or {}))
        if not self.posts:
            raise AssertionError("unexpected POST")
        return JsonResponse(200, self.posts.pop(0))


class MetaProviderTests(unittest.TestCase):
    def request(self, platform: str, media_ref: str | None = None) -> PublishRequest:
        return PublishRequest(
            post_id="post-1",
            variant_id="variant-1",
            platform=platform,
            body="GOLIDE test copy",
            media_ref=media_ref,
        )

    def test_discover_managed_accounts_returns_ids_without_returning_tokens(self) -> None:
        http = FakeHttp(gets=[{
            "data": [{
                "id": "page-123",
                "name": "GOLIDE",
                "tasks": ["CREATE_CONTENT", "MODERATE"],
                "instagram_business_account": {"id": "ig-456"},
                "access_token": "should-not-be-returned",
            }]
        }])
        accounts = discover_managed_accounts(
            api_version="v99.0",
            user_access_token="secret-user-token",
            http=http,
        )
        self.assertEqual(accounts[0].page_id, "page-123")
        self.assertEqual(accounts[0].instagram_user_id, "ig-456")
        self.assertFalse(hasattr(accounts[0], "access_token"))

    def test_real_publish_is_locked_by_default(self) -> None:
        provider = FacebookPageProvider(
            api_version="v99.0",
            page_access_token="secret",
            page_id="page-1",
            http=FakeHttp(),
        )
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "publishing is locked"):
                provider.publish(self.request("facebook"))

    def test_facebook_text_post_uses_page_feed(self) -> None:
        http = FakeHttp(posts=[{"id": "page-1_999"}])
        provider = FacebookPageProvider(
            api_version="v99.0",
            page_access_token="secret",
            page_id="page-1",
            http=http,
        )
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(self.request("facebook"))
        self.assertEqual(result.content_id, "page-1_999")
        method, url, data = http.calls[0]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/v99.0/page-1/feed"))
        self.assertEqual(data["message"], "GOLIDE test copy")
        self.assertEqual(data["access_token"], "secret")

    def test_facebook_photo_post_uses_photo_edge(self) -> None:
        http = FakeHttp(posts=[{"post_id": "page-1_1000"}])
        provider = FacebookPageProvider(
            api_version="v99.0",
            page_access_token="secret",
            page_id="page-1",
            http=http,
        )
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(
                self.request("facebook", "https://cdn.example.com/post.png")
            )
        self.assertEqual(result.content_id, "page-1_1000")
        self.assertTrue(http.calls[0][1].endswith("/page-1/photos"))
        self.assertEqual(http.calls[0][2]["url"], "https://cdn.example.com/post.png")

    def test_instagram_image_container_waits_then_publishes(self) -> None:
        http = FakeHttp(
            gets=[
                {"status_code": "IN_PROGRESS", "status": "Processing"},
                {"status_code": "FINISHED", "status": "Finished"},
            ],
            posts=[{"id": "container-1"}, {"id": "media-999"}],
        )
        sleeps = []
        provider = InstagramProvider(
            api_version="v99.0",
            access_token="secret",
            instagram_user_id="ig-1",
            http=http,
            sleeper=sleeps.append,
            poll_attempts=3,
            poll_seconds=0.1,
        )
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(
                self.request("instagram", "https://cdn.example.com/post.jpg")
            )
        self.assertEqual(result.content_id, "media-999")
        self.assertEqual(sleeps, [0.1])
        self.assertTrue(http.calls[0][1].endswith("/ig-1/media"))
        self.assertEqual(http.calls[0][2]["image_url"], "https://cdn.example.com/post.jpg")
        self.assertTrue(http.calls[-1][1].endswith("/ig-1/media_publish"))

    def test_instagram_reel_uses_video_container(self) -> None:
        http = FakeHttp(
            gets=[{"status_code": "FINISHED", "status": "Finished"}],
            posts=[{"id": "container-video"}, {"id": "reel-1"}],
        )
        provider = InstagramProvider(
            api_version="v99.0",
            access_token="secret",
            instagram_user_id="ig-1",
            http=http,
            sleeper=lambda _: None,
        )
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            provider.publish(
                self.request("instagram", "https://cdn.example.com/reel.mp4")
            )
        payload = http.calls[0][2]
        self.assertEqual(payload["media_type"], "REELS")
        self.assertEqual(payload["video_url"], "https://cdn.example.com/reel.mp4")
        self.assertEqual(payload["share_to_feed"], "true")

    def test_meta_rejects_non_https_media(self) -> None:
        provider = InstagramProvider(
            api_version="v99.0",
            access_token="secret",
            instagram_user_id="ig-1",
            http=FakeHttp(),
        )
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            with self.assertRaisesRegex(ValueError, "HTTPS media URL"):
                provider.publish(self.request("instagram", "temp://image/abc"))


if __name__ == "__main__":
    unittest.main()
