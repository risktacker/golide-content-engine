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
    def test_post_a_has_no_product_and_post_b_always_has_one(self):
        auto, seen = _automation()
        sunday_evening = datetime(2026, 10, 4, 18, 0, tzinfo=timezone.utc)
        results = auto.run_due(sunday_evening)
        self.assertEqual([r["slot"] for r in results], ["post-a", "post-b"])
        self.assertIsNone(seen["post-a"])
        self.assertIsNotNone(seen["post-b"])
        post_a, post_b = auto.bridge.created
        self.assertEqual(post_a["resolved_product_id"], "")
        self.assertEqual(post_b["resolved_product_id"], seen["post-b"].id)
        bodies = {v["platform"]: v["body"] for v in post_b["variants"]}
        url = seen["post-b"].marketplace_url
        self.assertIn(url, bodies["facebook"])
        self.assertIn(url, bodies["linkedin"])
        self.assertNotIn("http", bodies["instagram"])  # links in bio there
        self.assertNotIn("http", bodies["x"])          # X bills link posts ~13x
        self.assertIn("Link in bio", bodies["x"])

    def test_rulebook_differs_per_slot(self):
        a = static_post_instructions("post-a")
        b = static_post_instructions("post-b")
        self.assertIn("TREND POST", a)
        self.assertIn("Use web search", a)
        self.assertIn("Do not mention or promote", a)
        self.assertIn("PRODUCT POST", b)
        self.assertIn("subject of this post", b)


if __name__ == "__main__":
    unittest.main()
