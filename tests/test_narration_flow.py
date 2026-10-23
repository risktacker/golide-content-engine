"""2026-10-09: a script that reads as a list of points must be rejected."""
import json
import unittest
from pathlib import Path

from golide_engine.engine.content_rules import flow_problems, script_instructions

POINTS = """AI at work is moving from answering questions to taking responsibility for outcomes.
Google's Gemini agent can plan tasks, use company tools,
create documents, run code, and return finished work.
Ask for a leadership report, and it could review project emails,
pull Drive files, analyze numbers, and prepare the draft.
That pattern reaches beyond reports: sorting an inbox,
drafting follow-ups, building spreadsheets, or moving a customer inquiry
through a small-business workflow.
You give an outcome, while the agent chooses steps across tools.
If you ignore that shift, you may copy information between tabs
while software handles the chain.
Worse, it could read the wrong file, send the wrong reply,
or change something without a record.
So convenience without permission checks becomes a new source of risk.
The real product isn't a smarter chat reply.
It's delegated action with identity, limits, and an audit trail.
Start with one low-risk task, restrict access, and review every result.
So follow the channel, because we show what these agents can do
before you hand them your work.
Would you let an AI complete a task, or only suggest the steps?"""


def plan(text):
    return {"lines": [{"text": t} for t in text.splitlines()]}


class NarrationFlowTests(unittest.TestCase):
    def test_list_of_points_is_rejected(self):
        # 2026-10-23: list-style scripts are caught by colons, jargon and repeats; the
        # connective ratio is gone because it flagged the owner's own approved scripts.
        problems = " ".join(flow_problems(plan(POINTS)))
        self.assertIn("colons", problems)

    def test_the_owners_approved_scripts_pass(self):
        for name in ("golide-long-2026-10-22", "golide-short-2026-10-23"):
            approved = json.loads(Path(f"production-queue/{name}.script-plan.json").read_text())
            problems = [p for p in flow_problems(approved) if "stand-alone sentences" not in p]
            self.assertEqual([], problems, name)

    def test_approved_narration_passes(self):
        approved = json.loads(Path("production-queue/golide-short-2026-10-07.script-plan.json").read_text())
        self.assertEqual(flow_problems(approved), [])

    def test_short_template_asks_for_a_story_not_points(self):
        rules = script_instructions("short")
        self.assertIn("NARRATION", rules)
        self.assertIn("ONE CONNECTED EXPLANATION", rules)
        self.assertIn("Never open with", rules)

    def test_imagine_opening_is_rejected(self):
        text = "Imagine telling your computer to write a report,\n" + POINTS
        self.assertTrue(any("Imagine" in p for p in flow_problems(plan(text))))


if __name__ == "__main__":
    unittest.main()


class TeachingStyleTests(unittest.TestCase):
    def test_cake_script_teaching_style_holds_but_repeated_so_is_caught(self):
        # 2026-10-13: the owner flagged "So start..." then "So follow..." and a cold closing question.
        approved = json.loads(Path("production-queue/golide-short-2026-10-09.script-plan.json").read_text())
        problems = " ".join(flow_problems(approved))
        self.assertNotIn("list of points", problems)
        self.assertNotIn("final sentence must return", problems)
        self.assertIn("same word (so)", problems)
        self.assertIn("starts cold", problems)
        for fmt in ("short", "long"):
            self.assertIn("THE REAL THING FIRST", script_instructions(fmt))
            self.assertNotIn("comes from this world", script_instructions(fmt))
            self.assertIn("SOUND HUMAN", script_instructions(fmt))

    def test_ai_phrases_are_caught(self):
        approved = json.loads(Path("production-queue/golide-short-2026-10-07.script-plan.json").read_text())
        approved["lines"][4]["text"] = "Let's dive in, because this is a game-changer for shoppers."
        self.assertTrue(any("machine-written" in p for p in flow_problems(approved)))

    def test_a_two_sided_closing_question_need_not_echo_the_opening(self):
        # 2026-10-23: the owner's approved short ends on its own question.
        approved = json.loads(Path("production-queue/golide-short-2026-10-09.script-plan.json").read_text())
        approved["lines"][-1]["text"] = "So would you trust a robot with your job, yes or no?"
        self.assertFalse(any("final sentence" in p for p in flow_problems(approved)))


class VarietyTests(unittest.TestCase):
    def test_neighbouring_scripts_get_different_patterns(self):
        from golide_engine.engine.content_rules import script_variety
        a, b = script_variety("golide-short-2026-10-14"), script_variety("golide-short-2026-10-16")
        self.assertNotEqual(a.splitlines()[1], b.splitlines()[1])   # opening style
        # 2026-10-22: no rotating stock turn phrase any more; the turn is written fresh.
        self.assertIn("never a stock bridge", a)
        self.assertIn("VARIETY", script_instructions("short", "golide-short-2026-10-14"))

    def test_stock_phrases_are_caught(self):
        approved = json.loads(Path("production-queue/golide-short-2026-10-07.script-plan.json").read_text())
        approved["lines"][5]["text"] = "But here's the catch, think of it like a kitchen."
        self.assertTrue(any("here's the catch" in p for p in flow_problems(approved)))


class LearningNotShoppingTests(unittest.TestCase):
    def test_buying_chapter_is_refused(self):
        from golide_engine.engine.content_rules import chapter_problems

        plan = {"chapters": [{"number": "", "title": "Intro"}, {"number": "01", "title": "What It Does"},
                             {"number": "02", "title": "How It Works"}, {"number": "03", "title": "Your Buying Test"},
                             {"number": "", "title": "Close"}],
                "lines": [{"text": t, "chapter": c} for c, t in
                          [(0, "Intro line here."), (1, "What it does."), (2, "How it works."),
                           (3, "First, check this. Second, check that. Third, decide."), (4, "Close.")]]}
        self.assertTrue(any("learning, not shopping" in p for p in chapter_problems(plan, "long")))

    def test_rules_put_science_before_buying(self):
        from golide_engine.engine.content_rules import script_instructions

        text = script_instructions("long", "golide-long-2026-10-17")
        self.assertIn("SCIENCE FIRST", text)
        self.assertIn("LEARNING, NOT SHOPPING", text)
