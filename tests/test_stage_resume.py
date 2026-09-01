import json
import tempfile
import unittest
from pathlib import Path

from golide_engine.operations.budget import BudgetPaused
from golide_engine.operations.notifications import Notifier
from golide_engine.orchestration.stage_runner import StageRunner
from golide_engine.storage.database import Database


class StageResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = Database(self.root / "state.sqlite3")
        self.db.initialize()
        self.db.upsert_production({
            "id": "resume-1",
            "format": "short",
            "concept": {"family": "science"},
            "release": {"approved": True},
        })
        self.runner = StageRunner(self.db, Notifier(self.root / "failures"))

    def tearDown(self):
        self.temp.cleanup()

    def test_funds_pause_is_not_failure_and_resumes_same_stage(self):
        calls = []
        def paused():
            calls.append("paused")
            raise BudgetPaused(
                "recharge needed",
                required_usd=0.1,
                remaining_usd=0.02,
            )
        with self.assertRaises(BudgetPaused):
            self.runner.run("resume-1", "asset:a", paused, attempts=1)
        row = self.db.rows(
            "SELECT status FROM stage_runs WHERE production_id='resume-1'"
        )[0]
        self.assertEqual("paused_funds", row["status"])
        self.assertFalse((self.root / "failures" / "resume-1.json").exists())

        self.assertEqual("finished", self.runner.run(
            "resume-1", "asset:a", lambda: "finished", attempts=1
        ))
        rows = self.db.rows(
            "SELECT status FROM stage_runs WHERE production_id='resume-1' ORDER BY attempt"
        )
        self.assertEqual(["paused_funds", "completed"], [row["status"] for row in rows])

    def test_completed_stage_is_not_repeated(self):
        count = []
        self.runner.run("resume-1", "research", lambda: count.append(1), attempts=1)
        self.runner.run("resume-1", "research", lambda: count.append(2), attempts=1)
        self.assertEqual([1], count)
