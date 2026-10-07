"""Locked 2026-10-04: post-a is a trend post, post-b is a product post."""

import unittest

from datetime import datetime, timezone
from pathlib import Path

from golide_engine.engine.content_rules import static_post_instructions
from golide_engine.engine.products import ProductRegistry
from golide_engine.orchestration.static_automation import StaticAutomation


class FakeBridge:
    def __init__(self):
        self.created = []

    def static_month_count(self, month):
        return 0

    def content_exists(self, content_id):
        return False

    def create_content(self, payload):
        self.created.append(payload)
        return {"status": "scheduled"}


def _automation():
    auto = StaticAutomation.__new__(StaticAutomation)
    auto.root = Path(".").resolve()
    auto.bridge = FakeBridge()
    auto.calendar = {
        "timezone": "Africa/Lusaka",
        "daily_posts": [
            {"slot": "post-a", "time": "08:30", "days": ["sunday"], "platforms": ["x"]},
            {"slot": "post-b", "time": "17:30", "days": ["sunday"], "platforms": ["x"]},
        ],
    }
    auto.budget = {"openai": {"static_post_cap_usd": 3}}
    auto._live_registry = lambda: ProductRegistry("config/product-registry.json")
    seen = {}

    def fake_draft(*, content_id, slot, product):
        seen[slot] = product
        return {
            "title": "t", "weekly_theme": "w", "content_lane": "education",
            "value_units": ["one", "two", "three"],
            "platform_copy": {p: "copy" for p in ("instagram", "facebook", "linkedin", "x")},
            "image_hook": "Most people never notice this", "image_hook_emphasis": "never notice",
            "image_concept": "a glass jar", "glow_color": "gold",
            "use_product": False, "product_bridge_position": 0,
        }

    auto._draft = fake_draft
    auto._generate_image = lambda draft: ({"media_ref": "r2://a"}, {"media_ref": "r2://b"})
    return auto, seen


class StaticPostSplitTests(unittest.TestCase):
    def test_both_posts_are_trend_posts_with_a_product_slide(self):
        auto, seen = _automation()
        sunday_evening = datetime(2026, 10, 4, 18, 0, tzinfo=timezone.utc)
        results = auto.run_due(sunday_evening)
        self.assertEqual([r["slot"] for r in results], ["post-a", "post-b"])
        self.assertIsNotNone(seen["post-a"])  # every carousel gets one marketplace slide
        self.assertIsNotNone(seen["post-b"])
        post_a, post_b = auto.bridge.created
        for post in (post_a, post_b):
            self.assertEqual(post["product_mode"], "brand")
            self.assertEqual(post["resolved_product_id"], "")
            bodies = {v["platform"]: v["body"] for v in post["variants"]}
            self.assertNotIn(seen["post-b"].marketplace_url, " ".join(bodies.values()))
            self.assertNotIn("http", bodies["x"])

    def test_rulebook_differs_per_slot(self):
        a = static_post_instructions("post-a")
        b = static_post_instructions("post-b")
        self.assertIn("TREND POST", a)
        self.assertIn("Use web search", a)
        self.assertIn("Do not mention or promote", a)
        self.assertIn("EVENING TREND POST", b)
        self.assertIn("second to last", b)
        self.assertIn("CANDIDATE_PRODUCT", b)
        self.assertIn("THE CATCH", a)
        self.assertIn("leave heading", static_post_instructions("post-a", has_product=False))


if __name__ == "__main__":
    unittest.main()


def test_draft_sees_recent_posts():
    from types import SimpleNamespace

    seen = {}

    class Text:
        def generate_json(self, instructions, body, schema, **kw):
            seen["instructions"], seen["body"] = instructions, body
            return SimpleNamespace(value={}, request_id="r")

    auto = StaticAutomation.__new__(StaticAutomation)
    auto.bridge = SimpleNamespace(recent_posts=lambda days: [{"hook": "More applications aren't the fix. A scattered search is."}])
    auto.providers = SimpleNamespace(text=lambda live: Text())
    auto._draft(content_id="c", slot="post-b", product=None)
    assert "RECENT_POSTS=" in seen["body"] and "scattered search" in seen["body"]
    assert "NEVER REPEAT YOURSELF" in seen["instructions"]


def test_carousel_is_five_story_slides_then_marketplace_then_callout():
    from types import SimpleNamespace

    from golide_engine.orchestration.static_automation import StaticAutomation

    rendered = []
    auto = StaticAutomation.__new__(StaticAutomation)
    auto.media_store = SimpleNamespace(upload_bytes=lambda **kw: SimpleNamespace(
        media_ref="r2://s/" + kw["filename"], expires_at=datetime(2026, 10, 8, tzinfo=timezone.utc)))
    auto.bridge = SimpleNamespace(register_media=lambda refs: None)
    import golide_engine.engine.carousel as carousel
    real = carousel.render_slide

    def fake_render(slide, number, total, output, theme=None):
        rendered.append((slide.heading, slide.product, slide.final, number, total))
        output.write_bytes(b"x")
        return output

    carousel.render_slide = fake_render
    try:
        point = lambda h: {"heading": h, "emphasis": "", "text": "t"}
        draft = {"image_hook": "AI glasses are here.",
                 "carousel": {"points": [point(x) for x in ("1", "2", "3", "4", "5")], "callout": point("Follow")},
                 "product_slide": point("Buy")}
        refs = auto._carousel(draft, product=object())
    finally:
        carousel.render_slide = real
    assert [r[0] for r in rendered] == ["1", "2", "3", "4", "5", "Buy", "Follow"]
    assert rendered[5][1] and rendered[-1][2] and rendered[0][4] == 8  # 8 images with the cover
    assert len(refs) == 7
