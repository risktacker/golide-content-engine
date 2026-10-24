import json
import unittest
from pathlib import Path

from golide_engine.engine.content_rules import merge_spoken, script_instructions, spoken_pass_instructions


class SpokenPassTests(unittest.TestCase):
    """2026-10-24: scripts read like points that stop and start. The rules no longer hand the
    model joining words; a second pass rewrites the draft the way the owner talks."""

    def test_no_connective_templates_left_in_the_instructions(self):
        for fmt in ("short", "long"):
            text = script_instructions(fmt, f"golide-{fmt}-2026-10-24")
            for template in ("Rotate the", "Which leaves one question", "So where do you start?",
                             "spoken signpost", "joined to the takeaway before it with a connective",
                             "Never a cold question with no bridge"):
                self.assertNotIn(template, text)

    def test_spoken_pass_keeps_facts_and_learns_from_the_owner(self):
        text = spoken_pass_instructions("long")
        self.assertIn("same number of lines", text)
        self.assertIn("Add no new facts", text)
        self.assertIn("THE OWNER'S VOICE", text)

    def test_merge_replaces_words_and_keeps_the_visual_fields(self):
        plan = json.loads(Path("production-queue/golide-long-2026-10-22.script-plan.json").read_text())
        spoken = {"lines": [{"text": line["text"] + " really", "emphasis": "really"} for line in plan["lines"]]}
        merged = merge_spoken(plan, spoken)
        self.assertEqual(len(merged["lines"]), len(plan["lines"]))
        for a, b in zip(plan["lines"], merged["lines"]):
            self.assertEqual((a["visual"], a["subjects"], a["follow"], a["chapter"]),
                             (b["visual"], b["subjects"], b["follow"], b["chapter"]))
            self.assertTrue(b["text"].endswith("really"))

    def test_merge_refuses_a_pass_that_changed_the_line_count(self):
        plan = json.loads(Path("production-queue/golide-long-2026-10-22.script-plan.json").read_text())
        self.assertIsNone(merge_spoken(plan, {"lines": [{"text": "one", "emphasis": "one"}]}))

    def test_bad_emphasis_falls_back_to_a_word_in_the_line(self):
        plan = {"lines": [{"text": "old line", "emphasis": "old"}]}
        merged = merge_spoken(plan, {"lines": [{"text": "the motors push the car", "emphasis": "rocket"}]})
        self.assertIn(merged["lines"][0]["emphasis"].lower(), "the motors push the car")


if __name__ == "__main__":
    unittest.main()
