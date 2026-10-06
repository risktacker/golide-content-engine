import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from golide_engine.engine.content_rules import chapter_problems, flow_problems, script_display, script_text
from golide_engine.vector.chapters import ChapterMark, chapter_marks, with_chapters, youtube_chapters
from golide_engine.vector.illustrate import validate_scenes
from golide_engine.youtube_metadata import validate_chapters

PLAN = Path(__file__).resolve().parents[1] / "production-queue" / "golide-long-2026-10-06.script-plan.json"


def timed(plan, seconds_per_line=3.5):
    spoken = [l for l in plan["lines"] if l["text"].strip()]
    return [SimpleNamespace(index=i, start=i * seconds_per_line, section=l["section"]) for i, l in enumerate(spoken)]


class ChapterTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads(PLAN.read_text(encoding="utf-8"))

    def test_todays_plan_is_a_flowing_lesson(self):
        self.assertEqual(flow_problems(self.plan), [])
        self.assertEqual(chapter_problems(self.plan, "long"), [])

    def test_display_has_headings_but_spoken_text_does_not(self):
        display, spoken = script_display(self.plan), script_text(self.plan)
        self.assertIn("[02 · WHERE IT HIDES]", display)
        self.assertNotIn("[", spoken)
        self.assertEqual([r for r in display.splitlines() if r and not r.startswith("[")], spoken.splitlines())

    def test_marks_and_youtube_chapters_use_real_times(self):
        marks = chapter_marks(self.plan, timed(self.plan))
        self.assertEqual([m.title for m in marks][:3], ["Intro", "The real threat", "Where it hides"])
        self.assertEqual(marks[1].start, 6 * 3.5)
        rows = youtube_chapters(marks, 71 * 3.5)
        validate_chapters(rows)
        self.assertTrue(rows[0].startswith("0:00 Intro"))
        self.assertIn("0:21 The real threat", rows)

    def test_short_chapters_fold_into_previous(self):
        marks = [ChapterMark(0, "", "Intro"), ChapterMark(4, "01", "A"), ChapterMark(30, "02", "B"), ChapterMark(60, "03", "C")]
        self.assertEqual(youtube_chapters(marks, 100), ["0:00 Intro", "0:30 B", "1:00 C"])
        self.assertEqual(youtube_chapters(marks[:2], 100), [])

    def test_description_drops_guessed_timestamps(self):
        desc = "What this covers.\n\nChapters:\n00:00 Intro\n01:10 Guess\n\n#security #quantum"
        out = with_chapters(desc, ["0:00 Intro", "0:21 The real threat", "1:05 Map it"])
        self.assertNotIn("01:10 Guess", out)
        self.assertTrue(out.endswith("#security #quantum"))
        self.assertIn("Chapters\n0:00 Intro\n0:21 The real threat", out)

    def test_scenes_never_cross_a_chapter(self):
        scenes = [{"first_line": 0, "last_line": 9, "drawing": "a", "gold_element": "x"},
                  {"first_line": 10, "last_line": 19, "drawing": "b", "gold_element": "y"}]
        fixed = validate_scenes(scenes, 20, {6, 10, 15})
        self.assertEqual([(s["first_line"], s["last_line"]) for s in fixed], [(0, 5), (6, 9), (10, 14), (15, 19)])
        self.assertEqual([s["id"] for s in fixed], ["scene-01", "scene-02", "scene-03", "scene-04"])

    def test_long_plan_without_chapters_is_flagged(self):
        plan = {"chapters": [], "lines": [{"text": "x y z", "chapter": 0}] * 10}
        self.assertTrue(chapter_problems(plan, "long"))
        self.assertEqual(chapter_problems(plan, "short"), [])


if __name__ == "__main__":
    unittest.main()
