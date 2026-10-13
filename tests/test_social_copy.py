import unittest

from golide_engine.engine.social_copy import X_LIMIT, fit_x, strip_citations, x_length

TODAY = ("Prompting isn't the advantage. Building is.\n\nBasic AI skill demand fell 25%, while hands-on AI "
         "building and workflow automation rose 51% in Workday's latest report. Learn to connect AI to real "
         "work, then test the result. ([newsroom.workday.com](https://newsroom.workday.com/2026-10-05-Workday"
         "-Global-Workforce-Report?utm_source=openai))")


class SocialCopyTests(unittest.TestCase):
    def test_markdown_citations_are_removed(self):
        clean = strip_citations(TODAY)
        self.assertNotIn("](", clean)
        self.assertNotIn("utm_source", clean)
        self.assertTrue(clean.endswith("then test the result."))

    def test_plain_links_survive_without_tracking(self):
        self.assertEqual(strip_citations("Try it https://marketplace.golidee.com/jobsearch?utm_source=openai"),
                         "Try it https://marketplace.golidee.com/jobsearch")

    def test_x_copy_is_fitted_at_a_sentence(self):
        long = strip_citations(TODAY) + " " + "This sentence keeps going to push the post over the limit. " * 3
        fitted = fit_x(long + "\n\nhttps://marketplace.golidee.com/jobsearch")
        self.assertLessEqual(x_length(fitted), X_LIMIT)
        self.assertTrue(fitted.endswith("https://marketplace.golidee.com/jobsearch"))
        self.assertIn("then test the result.", fitted)

    def test_links_count_as_twenty_three(self):
        self.assertEqual(x_length("a https://example.com/" + "x" * 200), 2 + 23)


if __name__ == "__main__":
    unittest.main()


class PostShapeTests(unittest.TestCase):
    def test_x_posts_body_then_two_replies(self):
        import os
        from unittest.mock import patch

        from golide_engine.providers.base import PublishRequest
        from golide_engine.providers.http import JsonResponse
        from golide_engine.providers.x import XProvider

        class Api:
            def __init__(self):
                self.calls = []

            def post(self, url, *, bearer_token, json_body=None, headers=None):
                self.calls.append(json_body)
                return JsonResponse(201, {"data": {"id": f"t{len(self.calls)}"}})

        api = Api()
        provider = XProvider(user_access_token="s", http=api)
        request = PublishRequest(post_id="p", variant_id="v", platform="x", body="Main post.",
                                 parts=("Reply one.", "Reply two?"))
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(request)
        self.assertEqual(result.content_id, "t1")
        self.assertEqual([c["text"] for c in api.calls], ["Main post.", "Reply one.", "Reply two?"])
        self.assertEqual(api.calls[1]["reply"], {"in_reply_to_tweet_id": "t1"})
        self.assertEqual(api.calls[2]["reply"], {"in_reply_to_tweet_id": "t2"})

    def test_x_refuses_before_posting_anything_too_long(self):
        import os
        from unittest.mock import patch

        from golide_engine.providers.base import PublishRequest
        from golide_engine.providers.x import XProvider

        class Api:
            def post(self, *a, **k):
                raise AssertionError("nothing may be posted")

        provider = XProvider(user_access_token="s", http=Api())
        request = PublishRequest(post_id="p", variant_id="v", platform="x", body="ok", parts=("x" * 300,))
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            with self.assertRaises(ValueError):
                provider.publish(request)

    def test_instagram_carousel_cover_first_then_slides(self):
        import os
        from unittest.mock import patch

        from golide_engine.providers.base import PublishRequest
        from golide_engine.providers.http import JsonResponse
        from golide_engine.providers.meta import InstagramProvider

        class Http:
            def __init__(self):
                self.posts = []
                self.n = 0

            def get(self, url, *, params=None):
                return JsonResponse(200, {"status_code": "FINISHED"})

            def post(self, url, *, data=None, headers=None):
                self.posts.append((url, dict(data or {})))
                self.n += 1
                return JsonResponse(200, {"id": f"c{self.n}"})

        http = Http()
        provider = InstagramProvider(api_version="v99.0", access_token="t", instagram_user_id="ig",
                                     http=http, sleeper=lambda _: None)
        request = PublishRequest(post_id="p", variant_id="v", platform="instagram", body="Caption",
                                 media_ref="https://m.example/cover.jpg",
                                 extra_media=tuple(f"https://m.example/s{i}.jpg" for i in range(2, 6)))
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            provider.publish(request)
        items = [d for _, d in http.posts if d.get("is_carousel_item")]
        self.assertEqual([d["image_url"] for d in items][0], "https://m.example/cover.jpg")
        self.assertEqual(len(items), 5)
        parent = next(d for _, d in http.posts if d.get("media_type") == "CAROUSEL")
        self.assertEqual(parent["children"], "c1,c2,c3,c4,c5")
        self.assertEqual(parent["caption"], "Caption")
        self.assertTrue(http.posts[-1][0].endswith("media_publish"))


class LongVideoRouteTests(unittest.TestCase):
    def test_long_video_goes_to_facebook_as_video_and_linkedin_at_release(self):
        from golide_engine.orchestration.reels import long_social_payload

        payload = long_social_payload(content_id="L-social", metadata={"title": "T", "description": "D\n\nChapters\n0:00 Intro"},
                                      video_ref="r2://v.mp4", youtube_video_id="YT", owner_voice_ref="r2://voice",
                                      publish_at="2026-10-10T17:30:00Z")
        self.assertEqual(payload["content_class"], "long")
        self.assertEqual(payload["scheduled_at"], "2026-10-10T17:30:00Z")
        by = {v["platform"]: v for v in payload["variants"]}
        self.assertEqual(set(by), {"youtube", "instagram", "facebook", "linkedin"})
        self.assertLessEqual(len(by["instagram"]["body"]), 2200)
        self.assertEqual(by["facebook"]["title"], "T")  # titled = normal video, not a Reel
        self.assertEqual(by["youtube"]["parts"], ["youtube:YT"])

    def test_facebook_titled_video_uses_videos_endpoint(self):
        import os
        from unittest.mock import patch

        from golide_engine.providers.base import PublishRequest
        from golide_engine.providers.http import JsonResponse
        from golide_engine.providers.meta import FacebookPageProvider

        class Http:
            def __init__(self):
                self.posts = []

            def get(self, url, *, params=None):
                raise AssertionError

            def post(self, url, *, data=None, headers=None):
                self.posts.append((url, dict(data or {})))
                return JsonResponse(200, {"id": "vid1"})

        http = Http()
        provider = FacebookPageProvider(api_version="v99.0", page_access_token="t", page_id="pg", http=http)
        request = PublishRequest(post_id="p", variant_id="v", platform="facebook", body="Desc", title="Title",
                                 media_ref="https://m.example/video.mp4")
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            result = provider.publish(request)
        self.assertTrue(http.posts[0][0].endswith("pg/videos"))
        self.assertEqual(http.posts[0][1]["file_url"], "https://m.example/video.mp4")
        self.assertEqual(result.content_id, "vid1")


class QuestionMarkTests(unittest.TestCase):
    def test_questions_keep_their_question_mark(self):
        self.assertEqual(strip_citations("Which part feels scattered?"), "Which part feels scattered?")
        self.assertEqual(strip_citations("Ready?\n\nGo"), "Ready?\n\nGo")

    def test_slides_render_without_numpy(self):
        import builtins
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from golide_engine.engine.carousel import Slide, render_slide

        real = builtins.__import__

        def no_numpy(name, *a, **k):
            if name == "numpy" or name.startswith("numpy."):
                raise ImportError("numpy is not installed in the posts job")
            return real(name, *a, **k)

        with tempfile.TemporaryDirectory() as tmp, patch("builtins.__import__", no_numpy):
            out = render_slide(Slide("A clear heading", "One supporting line.", "clear"), 2, 5, Path(tmp) / "s.jpg")
            self.assertTrue(out.exists())
