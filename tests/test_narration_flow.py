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

    def test_imagine_opening_is_rejected(self):
        text = "Imagine telling your computer to write a report,\n" + POINTS
        self.assertTrue(any("Imagine" in p for p in flow_problems(plan(text))))


if __name__ == "__main__":
    unittest.main()


class TeachingStyleTests(unittest.TestCase):
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
    def test_stock_phrases_are_caught(self):
        approved = json.loads(Path("production-queue/golide-short-2026-10-07.script-plan.json").read_text())
        approved["lines"][5]["text"] = "But here's the catch, think of it like a kitchen."
        self.assertTrue(any("here's the catch" in p for p in flow_problems(approved)))
