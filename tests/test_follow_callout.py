import unittest

from golide_engine.engine.content_rules import closing_question_problems, static_post_instructions

from golide_engine.engine.content_rules import SCRIPT_SCHEMA, follow_problems, script_instructions


CLOSING = "Which leaves one question: should OpenCode pay back everyone, yes or no?"


def _plan(follow_at=(1,), text="Follow the channel, because the feed won't show us to you again.", n=12):
    lines = [{"text": f"line {i} about the idea", "follow": False} for i in range(n)]
    for i in follow_at:
        lines[i] = {"text": text, "follow": True}
    if follow_at and max(follow_at) < n - 1:
        lines[-1] = {"text": CLOSING, "follow": False}
    return {"lines": lines}


class FollowCalloutTests(unittest.TestCase):
    def test_brand_name_is_never_said_aloud(self):
        plan = _plan(follow_at=(10,), text="Follow GOLIDE, because the feed won't show us to you again.")
        self.assertTrue(any("brand name" in p for p in follow_problems(plan, "short")))


class DebateQuestionTests(unittest.TestCase):
    """2026-10-20: the ending splits people into two sides; polite questions are rewritten."""

    def test_two_sided_question_passes(self):
        self.assertEqual([], closing_question_problems("Is a fifty-thousand-dollar flying car a breakthrough or a toy?"))

    def test_polite_or_missing_question_is_caught(self):
        self.assertTrue(closing_question_problems("Would you trust it?"))
        self.assertTrue(closing_question_problems("So what do you think about all this?"))
        self.assertTrue(closing_question_problems("And that is why it matters."))
