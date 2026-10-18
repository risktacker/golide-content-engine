"""A replaced recording is never ignored (2026-10-18: a wrong upload was cancelled and replaced)."""

import tempfile
import unittest
from pathlib import Path

from golide_engine.orchestration.voice_reset import reset_if_recording_changed
from golide_engine.storage.database import Database


class VoiceResetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.root, self.work = root, root / "productions" / "p1"
        self.work.mkdir(parents=True)
        self.db = Database(root / "db.sqlite3")
        self.db.initialize()
        self.db.execute("INSERT INTO productions(production_id, format, concept_family, title, status, parameters_json, created_at, updated_at) "
                        "VALUES ('p1', 'short', 'tech', 't', 'running', '{}', 'now', 'now')")

    def tearDown(self):
        self.tmp.cleanup()

    def _stage(self, name):
        self.db.execute("INSERT INTO stage_runs(production_id, stage, attempt, status, started_at) "
                        "VALUES ('p1', ?, 1, 'completed', 'now')", (name,))

    def test_new_recording_clears_voice_work_but_keeps_pictures(self):
        (self.work / "timed-words-owner.json").write_text("[]")
        (self.work / "owner-voice-ref.txt").write_text("r2://old.wav")
        (self.work / "script.txt").write_text("keep")
        for stage in ("owner-voice", "metadata", "illustrations-v1"):
            self._stage(stage)
        self.assertTrue(reset_if_recording_changed(self.db, self.root, "p1", self.work, "r2://new.wav"))
        self.assertFalse((self.work / "timed-words-owner.json").exists())
        self.assertTrue((self.work / "script.txt").exists())
        stages = {r["stage"] for r in self.db.rows("SELECT stage FROM stage_runs WHERE production_id='p1'")}
        self.assertEqual(stages, {"illustrations-v1"})

    def test_same_recording_keeps_everything(self):
        (self.work / "timed-words-owner.json").write_text("[]")
        (self.work / "owner-voice-ref.txt").write_text("r2://same.wav")
        self.assertFalse(reset_if_recording_changed(self.db, self.root, "p1", self.work, "r2://same.wav"))
        self.assertTrue((self.work / "timed-words-owner.json").exists())

    def test_released_video_is_never_reset(self):
        (self.work / "timed-words-owner.json").write_text("[]")
        (self.work / "owner-voice-ref.txt").write_text("r2://old.wav")
        self._stage("release")
        self.assertFalse(reset_if_recording_changed(self.db, self.root, "p1", self.work, "r2://new.wav"))


if __name__ == "__main__":
    unittest.main()
