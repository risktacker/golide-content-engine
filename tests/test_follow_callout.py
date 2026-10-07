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

    def test_closing_follow_passes(self):
        self.assertEqual(follow_problems(_plan(follow_at=(10, 11)), "short"), [])
        self.assertEqual(follow_problems(_plan(follow_at=(11,)), "long"), [])

    def test_missing_late_or_comment_bait_is_caught(self):
        self.assertTrue(follow_problems(_plan(follow_at=()), "short"))
        self.assertTrue(follow_problems(_plan(follow_at=(1,)), "short"))  # before the value
        self.assertTrue(follow_problems(_plan(follow_at=(2, 11)), "long"))  # also mid-script
        bait = _plan(follow_at=(11,), text="Follow and comment AI to receive the guide.")
        self.assertTrue(any("comments" in p for p in follow_problems(bait, "short")))


    def test_brand_name_is_never_said_aloud(self):
        plan = _plan(follow_at=(11,), text="Follow GOLIDE, because the feed won't show us to you again.")
        self.assertTrue(any("brand name" in p for p in follow_problems(plan, "short")))
