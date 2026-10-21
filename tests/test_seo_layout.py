"""SEO layout: summary, chapters, hashtags; more than 20 tags.

2026-10-13 layout; 2026-10-21 the comma-separated keyword line left YouTube
descriptions (keyword stuffing under YouTube's spam policy). The keywords still
feed the tags.
"""
import unittest

from golide_engine.vector.chapters import with_chapters
from golide_engine.youtube_metadata import compose_description, fit_tags, seo_body, social_caption

KEYS = ["AI agents", "Gemini agent", "Google AI", "AI at work", "automation tools", "AI news", "tech news",
        "AI productivity", "workplace AI", "AI assistant", "Google Workspace AI", "AI safety"]
TAGS = ["ai", "gemini"]


class DescriptionLayoutTests(unittest.TestCase):
    def test_order_with_chapters_and_no_keyword_line(self):
        desc = compose_description("Para one.\n\nPara two.\n#old", KEYS, ["AI", "#TechNews", "Gemini agent"])
        full = with_chapters(desc, ["00:00 Intro", "00:40 01 What it is", "02:10 02 Steps"])
        rows = [r for r in full.split("\n\n") if r]
        self.assertEqual(rows[:2], ["Para one.", "Para two."])
        self.assertTrue(rows[2].startswith("Chapters"))
        self.assertEqual(rows[3], "#AI #TechNews #Geminiagent")
        self.assertNotIn("#old", full)
        self.assertNotIn("Gemini agent, Google AI", full)
        self.assertNotIn("AI agents", full)

    def test_keywords_still_reach_the_tags(self):
        tags = fit_tags(TAGS, KEYS)
        self.assertIn("AI agents", tags)
        self.assertGreater(len(tags), 20)
        self.assertLessEqual(sum(len(t) + (2 if " " in t else 0) for t in tags) + len(tags) - 1, 500)

    def test_citations_never_reach_descriptions(self):
        body = seo_body("They run Android. ([aboutamazon.com](https://www.aboutamazon.com/x?utm_source=openai))"
                        "\n\nMore. https://t.co/x")
        self.assertEqual(body, "They run Android.\n\nMore.")
        desc = compose_description("Tablets. ([site.com](https://site.com/a?utm_source=openai))", KEYS, ["AI"])
        self.assertNotIn("utm", desc)
        self.assertNotIn("http", desc)


class SocialCaptionTests(unittest.TestCase):
    def test_caption_keeps_hashtags_when_trimmed(self):
        meta = {"seo_body": "word " * 1000, "keywords": KEYS, "hashtags": ["AI", "Tech"], "chapters": []}
        cap = social_caption("Title", meta, 2200)
        self.assertLessEqual(len(cap), 2200)
        self.assertTrue(cap.endswith("#AI #Tech"))

    def test_static_posts_get_hashtags(self):
        from golide_engine.orchestration.static_automation import add_seo
        copies = {"instagram": "Hook.\n\nBody.", "facebook": "Hook.", "linkedin": "Hook.", "x": "Short post."}
        out = add_seo(copies, KEYS, ["CanvaAI", "AI", "TechNews", "Design", "Automation"])
        for p in ("instagram", "facebook", "linkedin"):
            self.assertTrue(out[p].endswith("#CanvaAI #AI #TechNews #Design #Automation"))
        self.assertTrue(out["x"].endswith("#CanvaAI #AI"))


if __name__ == "__main__":
    unittest.main()
