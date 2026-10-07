import unittest

from golide_engine.engine.content_rules import SCRIPT_SCHEMA, follow_problems, script_instructions


def _plan(follow_at=(1,), text="Follow the channel, because the feed won't show us to you again.", n=12):
    lines = [{"text": f"line {i} about the idea", "follow": False} for i in range(n)]
    for i in follow_at:
        lines[i] = {"text": text, "follow": True}
    return {"lines": lines}


class FollowCalloutTests(unittest.TestCase):
    def test_schema_and_instructions_carry_the_follow(self):
        item = SCRIPT_SCHEMA["properties"]["lines"]["items"]
        self.assertIn("follow", item["required"])
        for fmt in ("short", "long"):
            rules = script_instructions(fmt)
            self.assertIn("FOLLOW CALL-OUT", rules)
            self.assertIn("NEVER ask people to comment", rules)

    def test_early_short_follow_passes(self):
        self.assertEqual(follow_problems(_plan(), "short"), [])

    def test_missing_late_or_comment_bait_is_caught(self):
        self.assertTrue(follow_problems(_plan(follow_at=()), "short"))
        self.assertTrue(follow_problems(_plan(follow_at=(9,)), "short"))
        bait = _plan(text="Follow and comment AI to receive the guide.")
        self.assertTrue(any("comments" in p for p in follow_problems(bait, "short")))

    def test_long_needs_a_closing_follow(self):
        self.assertTrue(follow_problems(_plan(follow_at=(2,)), "long"))
        self.assertEqual(follow_problems(_plan(follow_at=(2, 10)), "long"), [])

    def test_brand_name_is_never_said_aloud(self):
        plan = _plan(text="Follow GOLIDE, because the feed won't show us to you again.")
        self.assertTrue(any("brand name" in p for p in follow_problems(plan, "short")))
