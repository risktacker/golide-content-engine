"""Locked 2026-10-04: post-a is a trend post, post-b is a product post."""

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


def _automation(monkeypatch):
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


def test_post_a_has_no_product_and_post_b_always_has_one(monkeypatch):
    auto, seen = _automation(monkeypatch)
    sunday_evening = datetime(2026, 10, 4, 18, 0, tzinfo=timezone.utc)
    results = auto.run_due(sunday_evening)
    assert [r["slot"] for r in results] == ["post-a", "post-b"]
    assert seen["post-a"] is None
    assert seen["post-b"] is not None
    post_a, post_b = auto.bridge.created
    assert post_a["resolved_product_id"] == ""
    assert post_b["resolved_product_id"] == seen["post-b"].id
    assert seen["post-b"].marketplace_url in post_b["variants"][0]["body"]


def test_rulebook_differs_per_slot():
    a = static_post_instructions("post-a")
    b = static_post_instructions("post-b")
    assert "TREND POST" in a and "Use web search" in a and "Do not mention or promote" in a
    assert "PRODUCT POST" in b and "subject of this post" in b
