import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from golide_engine.orchestration.schedule import materialize_due


class AutomationScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = self.root / "schedule.json"
        self.config.write_text(json.dumps({
            "timezone": "Africa/Lusaka",
            "channel_id": "locked-channel",
            "rules": [
                {"id": "long", "format": "long", "start_date": "2026-09-01",
                 "weekdays": ["tuesday"], "generate_time": "06:00",
                 "publish_time": "18:00", "openai_allocation_usd": 0.5},
                {"id": "shorts", "format": "short", "start_date": "2026-09-09",
                 "weekdays": ["wednesday", "friday", "sunday"],
                 "generate_time": "09:00", "publish_time": "13:00",
                 "openai_allocation_usd": 0.2},
            ],
        }))

    def tearDown(self):
        self.temp.cleanup()

    def test_first_tuesday_long_materializes_once(self):
        queue = self.root / "queue"
        now = datetime(2026, 9, 1, 12, 30, tzinfo=timezone.utc)
        created = materialize_due(queue, self.config, now)
        self.assertEqual(1, len(created))
        spec = json.loads(created[0].read_text())
        self.assertEqual("long", spec["format"])
        self.assertEqual("2026-09-01T16:00:00Z", spec["release"]["scheduled_at"])
        self.assertTrue(spec["production_authorized"])
        self.assertEqual([], materialize_due(queue, self.config, now))

    def test_short_starts_on_locked_date(self):
        queue = self.root / "queue"
        before = datetime(2026, 9, 2, 8, tzinfo=timezone.utc)
        self.assertEqual([], materialize_due(queue, self.config, before))
        start = datetime(2026, 9, 9, 8, tzinfo=timezone.utc)
        created = materialize_due(queue, self.config, start)
        self.assertEqual("short", json.loads(created[0].read_text())["format"])

    def test_never_creates_after_publish_time(self):
        queue = self.root / "queue"
        now = datetime(2026, 9, 1, 16, 1, tzinfo=timezone.utc)
        self.assertEqual([], materialize_due(queue, self.config, now))


class LockedScheduleTests(unittest.TestCase):
    """The real schedule: long videos Tue, Thu and Sat (owner direction 2026-10-18)."""

    def test_thursday_long_materializes_from_locked_config(self):
        config = Path(__file__).resolve().parents[1] / "config" / "automation-schedule.json"
        with tempfile.TemporaryDirectory() as temp:
            thursday = datetime(2026, 10, 22, 5, tzinfo=timezone.utc)   # 07:00 Lusaka
            created = materialize_due(Path(temp), config, thursday)
            self.assertEqual(["golide-long-2026-10-22.json"], [p.name for p in created])
            spec = json.loads(created[0].read_text())
            self.assertEqual("2026-10-22T17:30:00Z", spec["release"]["scheduled_at"])
            self.assertEqual("owner-recording-only", spec["generation_parameters"]["voice"])
