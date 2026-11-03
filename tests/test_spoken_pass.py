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
        self.assertIn("ONE continuous talk", text)
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

    def test_spoken_pass_studies_draft_and_owner_versions(self):
        # 2026-10-25: the pass ran but changed too little; it now sees before and after pairs.
        text = spoken_pass_instructions("short")
        self.assertIn("BEFORE AND AFTER", text)
        self.assertIn("The engineering principle is feedback control.", text)
        self.assertIn("A robot is painting walls in India now", text)

    def test_spoken_pass_runs_at_high_effort(self):
        from golide_engine.engine.content_rules import SPOKEN_PASS_EFFORT
        self.assertEqual(SPOKEN_PASS_EFFORT, "high")

if __name__ == "__main__":
    unittest.main()


def test_chapters_are_rewritten_freely_and_split_back_into_screen_lines():
    from golide_engine.engine.content_rules import CHAPTER_MARK, draft_chapters, merge_spoken_chapters, script_text
    plan = json.loads(Path("production-queue/golide-long-2026-10-22.script-plan.json").read_text())
    draft = draft_chapters(plan)
    rewritten = CHAPTER_MARK.sub(lambda m: f"[[{m.group(1)}]] And that brings us here.", draft)
    merged = merge_spoken_chapters(plan, {"script": rewritten})
    assert merged is not None
    assert script_text(merged).split() == CHAPTER_MARK.sub("", rewritten).split()
    assert all(len(line["text"].split()) <= 14 for line in merged["lines"])
    chapters = [line["chapter"] for line in merged["lines"]]
    assert chapters == sorted(chapters)                       # chapter order is kept
    lost = rewritten.replace("[[1]]", "")
    assert merge_spoken_chapters(plan, {"script": lost}) is None   # a lost marker keeps the draft
