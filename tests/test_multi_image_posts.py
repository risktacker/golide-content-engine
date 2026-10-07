import json
import os
import unittest
from unittest.mock import patch

from golide_engine.providers.base import PublishRequest
from golide_engine.providers.json_api import ApiResponse
from golide_engine.providers.linkedin import LinkedInProvider
from golide_engine.providers.meta import FacebookPageProvider
from tests.test_distribution_linkedin_x import FakeBinaryHttp, FakeJsonApi
from tests.test_distribution_meta_providers import FakeHttp


def _request(platform):
    return PublishRequest(post_id="p", variant_id="v", platform=platform, body="Two paragraphs.",
                          media_ref="https://media.example/cover.jpg",
                          extra_media=("https://media.example/s2.jpg", "https://media.example/s3.jpg"))


class MultiImageTests(unittest.TestCase):
    def test_facebook_posts_every_slide_in_one_post(self):
        http = FakeHttp(posts=[{"id": "ph1"}, {"id": "ph2"}, {"id": "ph3"}, {"id": "page_post"}])
        provider = FacebookPageProvider(api_version="v99.0", page_access_token="t", page_id="page", http=http)
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(_request("facebook"))
        self.assertEqual(result.content_id, "page_post")
        uploads = [c for c in http.calls if c[1].endswith("/photos")]
        self.assertEqual(len(uploads), 3)
        self.assertTrue(all(c[2]["published"] == "false" for c in uploads))
        feed = http.calls[-1]
        self.assertTrue(feed[1].endswith("/page/feed"))
        self.assertEqual(json.loads(feed[2]["attached_media"]), [{"media_fbid": "ph1"}, {"media_fbid": "ph2"}, {"media_fbid": "ph3"}])

    def test_linkedin_posts_every_slide_as_multi_image(self):
        uploads = [ApiResponse(200, {"value": {"uploadUrl": f"https://up/{i}", "image": f"urn:li:image:{i}"}}, {})
                   for i in range(3)]
        http = FakeJsonApi(posts=[*uploads, ApiResponse(201, {}, {"x-restli-id": "urn:li:share:multi"})])
        provider = LinkedInProvider(access_token="t", author_urn="urn:li:person:a", linkedin_version="202609",
                                    http=http, binary_http=FakeBinaryHttp(b"jpeg", "image/jpeg"))
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(_request("linkedin"))
        self.assertEqual(result.content_id, "urn:li:share:multi")
        content = http.calls[-1]["json_body"]["content"]
        self.assertEqual([i["id"] for i in content["multiImage"]["images"]],
                         ["urn:li:image:0", "urn:li:image:1", "urn:li:image:2"])
