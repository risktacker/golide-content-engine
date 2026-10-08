"""Regression tests for the issues found in the 2026-10-08 pipeline audit."""
import json
import tempfile
import unittest
from pathlib import Path

from golide_engine.engine.carousel import _split_pull
from golide_engine.orchestration.queue import pick_due_spec, record_failure
from golide_engine.vector.cover import clean_cover_text
from golide_engine.vector.illustrate import validate_scenes


def _spec(root: Path, name: str, **extra) -> Path:
    path = root / "production-queue" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"id": name, "owner_voice_required": True, **extra}), encoding="utf-8")
    return path


class QueueTests(unittest.TestCase):
    def test_unrecorded_video_does_not_block_the_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _spec(root, "old")
            (root / "productions" / "old").mkdir(parents=True)
            (root / "productions" / "old" / "script.txt").write_text("x")
            new = _spec(root, "new")
            self.assertEqual(pick_due_spec([old, new], root), new)

    def test_a_fresh_recording_goes_first_and_all_waiting_means_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = _spec(root, "a")
            b = _spec(root, "b", owner_voice_media_ref="r2://voice")
            self.assertEqual(pick_due_spec([a, b], root), b)
            for name in ("a",):
                (root / "productions" / name).mkdir(parents=True)
                (root / "productions" / name / "script.txt").write_text("x")
            self.assertIsNone(pick_due_spec([a], root))

    def test_repeated_failures_set_a_spec_aside(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _spec(Path(tmp), "broken")
            self.assertFalse(record_failure(path))
            self.assertFalse(record_failure(path))
            self.assertTrue(record_failure(path))
            self.assertFalse(path.exists())
            self.assertTrue(path.with_suffix(".failed.json").exists())


class SceneAndCoverTests(unittest.TestCase):
    def test_scene_count_is_capped_without_crossing_chapters(self):
        scenes = [{"first_line": i, "last_line": i, "drawing": "d", "gold_element": "g"} for i in range(14)]
        fixed = validate_scenes(scenes, 14, frozenset({7}), max_scenes=6)
        self.assertLessEqual(len(fixed), 6)
        self.assertTrue(any(s["first_line"] == 7 for s in fixed))  # chapter still starts a scene
        self.assertEqual(fixed[-1]["last_line"], 13)

    def test_cover_text_is_plain_and_short(self):
        text, gold = clean_cover_text("Meta’s AI \U0001F6D2 shops — for you, Amazon said no #AI extra words", "Amazon said no")
        self.assertNotIn("\U0001F6D2", text)
        self.assertNotIn("#", text)
        self.assertLessEqual(len(text.split()), 9)
        self.assertEqual(gold, "Amazon said no")


class CuriosityLineTests(unittest.TestCase):
    def test_only_real_sentence_ends_split(self):
        self.assertEqual(_split_pull("Apple Inc. launched it.", False)[1], "")
        self.assertEqual(_split_pull("One thing. But wait? and then more", False)[1], "")
        self.assertEqual(_split_pull("GPT-5.5 is out. But there's a catch.", False),
                         ("GPT-5.5 is out.", "But there's a catch."))
