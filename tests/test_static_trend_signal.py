"""Both daily posts read the live trend signal (owner direction 2026-10-18)."""

import json
import unittest
from unittest import mock

from golide_engine.engine.content_rules import static_post_instructions
from golide_engine.orchestration.static_automation import StaticAutomation


class FakeText:
    def __init__(self):
        self.calls = []

    def generate_json(self, instructions, body, schema, web_search=False, max_output_tokens=0):
        self.calls.append({"body": body, "web_search": web_search})
        value = {"image_hook": "A robot just learned to fold laundry", "title": "t"}
        return mock.Mock(value=value, request_id="req")


class FakeBridge:
    def recent_posts(self, days):
        return []


def _automation(text):
    auto = StaticAutomation.__new__(StaticAutomation)
    auto.bridge = FakeBridge()
    auto.providers = mock.Mock(text=lambda live=True: text)
    auto._fresh = None
    return auto


HEADLINES = [{"source": "hacker news", "title": "Robot folds laundry", "points": 900, "comments": 300}]


class StaticTrendSignalTests(unittest.TestCase):
    def test_both_slots_search_and_see_headlines_fetched_once(self):
        text = FakeText()
        auto = _automation(text)
        with mock.patch("golide_engine.youtube.pulse.fresh_headlines", return_value=HEADLINES) as fetch, \
                mock.patch("golide_engine.engine.content_rules.hook_problems", return_value=[]):
            for slot in ("post-a", "post-b"):
                auto._draft(content_id=f"id-{slot}", slot=slot, product=None)
        self.assertEqual(1, fetch.call_count)
        self.assertEqual([True, True], [c["web_search"] for c in text.calls])
        for call in text.calls:
            line = next(l for l in call["body"].splitlines() if l.startswith("FRESH_HEADLINES="))
            self.assertEqual(HEADLINES, json.loads(line.split("=", 1)[1]))

    def test_headline_outage_never_blocks_a_post(self):
        text = FakeText()
        auto = _automation(text)
        with mock.patch("golide_engine.youtube.pulse.fresh_headlines", side_effect=OSError("down")), \
                mock.patch("golide_engine.engine.content_rules.hook_problems", return_value=[]):
            draft = auto._draft(content_id="id", slot="post-b", product=None)
        self.assertEqual("req", draft["_request_id"])
        self.assertIn("FRESH_HEADLINES=[]", text.calls[0]["body"])

    def test_both_rulebooks_use_the_headlines(self):
        for slot in ("post-a", "post-b"):
            self.assertIn("FRESH_HEADLINES", static_post_instructions(slot))

    def test_a_31_day_month_of_posts_fits_the_guard(self):
        self.assertLessEqual(62 * StaticAutomation.ESTIMATED_POST_USD, 3.5)


if __name__ == "__main__":
    unittest.main()
