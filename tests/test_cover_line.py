import tempfile
import unittest
from pathlib import Path

from golide_engine.vector.cover_line import line_problems, recent_lines, record_line
from golide_engine.vector.illustrate import scene_plan_instructions


class CoverLineTests(unittest.TestCase):
    """2026-10-25: the opening card's line is the thumbnail text."""

    def test_strong_lines_pass(self):
        for line, title in (("The Robot Wasn't the Story", "Jensen Huang's Tiny Microduck Robots Steal the Spotlight"),
                            ("Five Percent Is Not Public Money", "Anthropic Wants to Give Away 5% of the Company")):
            self.assertEqual([], line_problems(line, title, []))

    def test_worn_who_shape_title_repeat_and_length_are_caught(self):
        self.assertTrue(any("Who" in p for p in line_problems("Who Taught It?", "Tiny robots at GTC", [])))
        self.assertTrue(any("repeats the title" in p for p in
                            line_problems("Tiny Microduck Robots Spotlight", "Tiny Microduck Robots Steal the Spotlight", [])))
        self.assertTrue(any("3 to 6" in p for p in line_problems("Wow", "t", [])))

    def test_recent_opening_and_sibling_line_are_caught(self):
        recent = [{"text": "The Robot Wasn't the Story", "topic": "u"}]
        self.assertTrue(any("opened" in p for p in line_problems("The Robot Learned Elsewhere", "t", recent)))
        self.assertTrue(any("other video" in p for p in line_problems("The Robot Wasn't the Story", "t", recent, "u")))

    def test_lines_are_logged_and_read_back_without_the_current_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record_line(root, "a", "short", "T", "Line One Here")
            record_line(root, "b", "long", "T", "Line Two Here")
            self.assertEqual(["Line One Here"], [r["text"] for r in recent_lines(root, "b")])

    def test_storyboard_prompt_asks_for_the_line_not_three_words(self):
        text = scene_plan_instructions("long", 400.0)
        self.assertIn("3 to 6", text)
        self.assertNotIn("ONE TO THREE words", text)


if __name__ == "__main__":
    unittest.main()
