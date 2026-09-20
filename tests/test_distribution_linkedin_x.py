from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from golide_engine.providers.base import PublishRequest
from golide_engine.providers.binary_http import BinaryResponse
from golide_engine.providers.json_api import ApiResponse
from golide_engine.providers.linkedin import LinkedInProvider
from golide_engine.providers.x import XProvider


class FakeJsonApi:
    def __init__(self, posts=None, gets=None):
        self.posts = list(posts or [])
        self.gets = list(gets or [])
        self.calls = []

    def post(self, url, *, bearer_token, json_body=None, headers=None):
        self.calls.append({
            "method": "POST",
            "url": url,
            "bearer_token": bearer_token,
            "json_body": json_body,
            "headers": headers or {},
        })
        if not self.posts:
            raise AssertionError(f"unexpected POST {url}")
        return self.posts.pop(0)

    def get(self, url, *, bearer_token, params=None, headers=None):
        self.calls.append({
            "method": "GET",
            "url": url,
            "bearer_token": bearer_token,
            "params": params or {},
            "headers": headers or {},
        })
        if not self.gets:
            raise AssertionError(f"unexpected GET {url}")
        return self.gets.pop(0)


class FakeBinaryHttp:
    def __init__(self, data: bytes, content_type: str, put_etags=None):
        self.data = data
        self.content_type = content_type
        self.put_etags = list(put_etags or [])
        self.calls = []

    def get(self, url, *, headers=None):
        headers = headers or {}
        self.calls.append(("GET", url, headers))
        byte_range = headers.get("Range")
        if byte_range:
            spec = byte_range.replace("bytes=", "")
            first_s, last_s = spec.split("-", 1)
            first, last = int(first_s), int(last_s)
            chunk = self.data[first:last + 1]
            return BinaryResponse(
                status=206,
                data=chunk,
                headers={
                    "content-type": self.content_type,
                    "content-range": f"bytes {first}-{last}/{len(self.data)}",
                    "content-length": str(len(chunk)),
                },
            )
        return BinaryResponse(
            status=200,
            data=self.data,
            headers={
                "content-type": self.content_type,
                "content-length": str(len(self.data)),
            },
        )

    def put(self, url, data, *, content_type="application/octet-stream", headers=None):
        self.calls.append(("PUT", url, {"bytes": len(data), "content_type": content_type}))
        etag = self.put_etags.pop(0) if self.put_etags else "etag-default"
        return BinaryResponse(status=200, data=b"", headers={"etag": f'"{etag}"'})


class LinkedInXProviderTests(unittest.TestCase):
    def request(self, platform: str, media_ref: str | None = None) -> PublishRequest:
        return PublishRequest(
            post_id="post-1",
            variant_id="variant-1",
            platform=platform,
            body="GOLIDE distribution post",
            title="GOLIDE proof",
            media_ref=media_ref,
        )

    def test_linkedin_text_post(self) -> None:
        http = FakeJsonApi(posts=[
            ApiResponse(201, {}, {"x-restli-id": "urn:li:share:12345"})
        ])
        provider = LinkedInProvider(
            access_token="secret-linkedin",
            author_urn="urn:li:person:abc123",
            linkedin_version="202609",
            http=http,
            binary_http=FakeBinaryHttp(b"", "application/octet-stream"),
        )
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(self.request("linkedin"))
        self.assertEqual(result.content_id, "urn:li:share:12345")
        self.assertEqual(http.calls[0]["url"], "https://api.linkedin.com/rest/posts")
        self.assertNotIn("content", http.calls[0]["json_body"])

    def test_linkedin_image_upload_then_post(self) -> None:
        image = b"jpeg-image-bytes"
        binary = FakeBinaryHttp(image, "image/jpeg")
        http = FakeJsonApi(posts=[
            ApiResponse(200, {"value": {
                "uploadUrl": "https://linkedin-upload.example/image",
                "image": "urn:li:image:img123",
            }}, {}),
            ApiResponse(201, {}, {"x-restli-id": "urn:li:share:post-image"}),
        ])
        provider = LinkedInProvider(
            access_token="secret",
            author_urn="urn:li:person:abc",
            linkedin_version="202609",
            http=http,
            binary_http=binary,
        )
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(
                self.request("linkedin", "https://temp.example/image.jpg")
            )
        self.assertEqual(result.content_id, "urn:li:share:post-image")
        self.assertTrue(any(call[0] == "PUT" for call in binary.calls))
        post_payload = http.calls[-1]["json_body"]
        self.assertEqual(post_payload["content"]["media"]["id"], "urn:li:image:img123")

    def test_linkedin_video_parts_are_finalized_in_etag_order(self) -> None:
        video = b"v" * (80 * 1024)
        halfway = len(video) // 2
        binary = FakeBinaryHttp(video, "video/mp4", put_etags=["part-a", "part-b"])
        http = FakeJsonApi(posts=[
            ApiResponse(200, {"value": {
                "video": "urn:li:video:vid123",
                "uploadToken": "token-1",
                "uploadInstructions": [
                    {"firstByte": 0, "lastByte": halfway - 1, "uploadUrl": "https://upload/1"},
                    {"firstByte": halfway, "lastByte": len(video) - 1, "uploadUrl": "https://upload/2"},
                ],
            }}, {}),
            ApiResponse(200, {"value": {}}, {}),
            ApiResponse(201, {}, {"x-restli-id": "urn:li:share:post-video"}),
        ])
        provider = LinkedInProvider(
            access_token="secret",
            author_urn="urn:li:organization:123",
            linkedin_version="202609",
            http=http,
            binary_http=binary,
        )
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(
                self.request("linkedin", "https://temp.example/video.mp4")
            )
        self.assertEqual(result.content_id, "urn:li:share:post-video")
        finalize = next(
            call for call in http.calls
            if call["url"].endswith("videos?action=finalizeUpload")
        )
        self.assertEqual(
            finalize["json_body"]["finalizeUploadRequest"]["uploadedPartIds"],
            ["part-a", "part-b"],
        )
        self.assertEqual(
            http.calls[-1]["json_body"]["content"]["media"]["id"],
            "urn:li:video:vid123",
        )

    def test_x_text_post(self) -> None:
        http = FakeJsonApi(posts=[
            ApiResponse(201, {"data": {"id": "999"}}, {})
        ])
        provider = XProvider(
            user_access_token="secret-x",
            http=http,
            binary_http=FakeBinaryHttp(b"", "application/octet-stream"),
        )
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(self.request("x"))
        self.assertEqual(result.url, "https://x.com/i/web/status/999")
        self.assertEqual(http.calls[-1]["json_body"], {"text": "GOLIDE distribution post"})

    def test_x_image_upload_then_post(self) -> None:
        binary = FakeBinaryHttp(b"png-data", "image/png")
        http = FakeJsonApi(posts=[
            ApiResponse(200, {"data": {"id": "media-image"}}, {}),
            ApiResponse(201, {"data": {"id": "tweet-image"}}, {}),
        ])
        provider = XProvider(user_access_token="secret-x", http=http, binary_http=binary)
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(self.request("x", "https://temp.example/image.png"))
        self.assertEqual(result.content_id, "tweet-image")
        self.assertEqual(
            http.calls[-1]["json_body"]["media"]["media_ids"],
            ["media-image"],
        )

    def test_x_video_chunked_upload_waits_for_processing(self) -> None:
        video = b"x" * (5 * 1024 * 1024)
        binary = FakeBinaryHttp(video, "video/mp4")
        http = FakeJsonApi(
            posts=[
                ApiResponse(200, {"data": {"id": "media-video"}}, {}),
                ApiResponse(200, {"data": {}}, {}),
                ApiResponse(200, {"data": {}}, {}),
                ApiResponse(200, {"data": {
                    "id": "media-video",
                    "processing_info": {"state": "pending", "check_after_secs": 0},
                }}, {}),
                ApiResponse(201, {"data": {"id": "tweet-video"}}, {}),
            ],
            gets=[
                ApiResponse(200, {"data": {
                    "processing_info": {"state": "succeeded"}
                }}, {}),
            ],
        )
        provider = XProvider(
            user_access_token="secret-x",
            http=http,
            binary_http=binary,
            sleeper=lambda _: None,
        )
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(self.request("x", "https://temp.example/video.mp4"))
        self.assertEqual(result.content_id, "tweet-video")
        append_calls = [
            call for call in http.calls
            if call["method"] == "POST" and call["url"].endswith("/append")
        ]
        self.assertEqual(len(append_calls), 2)
        status = next(call for call in http.calls if call["method"] == "GET")
        self.assertEqual(status["params"]["media_id"], "media-video")


if __name__ == "__main__":
    unittest.main()
