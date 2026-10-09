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
        problems = " ".join(flow_problems(plan(POINTS)))
        self.assertIn("list of points", problems)
        self.assertIn("colons", problems)
        self.assertIn("hook", problems)

    def test_approved_narration_passes(self):
        approved = json.loads(Path("production-queue/golide-short-2026-10-07.script-plan.json").read_text())
        self.assertEqual(flow_problems(approved), [])

    def test_short_template_asks_for_a_story_not_points(self):
        rules = script_instructions("short")
        self.assertIn("NARRATION", rules)
        self.assertIn("WALK-THROUGH", rules)
        self.assertNotIn("Name 2 to 4 cases", rules)


if __name__ == "__main__":
    unittest.main()
