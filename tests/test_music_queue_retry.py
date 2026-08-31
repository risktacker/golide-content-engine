import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from golide_engine.music.registry import MusicRegistry
from golide_engine.operations.retry import with_retry
from golide_engine.orchestration.queue import due_specs


class MusicQueueRetryTests(unittest.TestCase):
    def test_empty_music_registry_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "music.json"
            path.write_text('{"tracks": []}')
            with self.assertRaises(RuntimeError):
                MusicRegistry(path).select("curious")

    def test_completed_queue_item_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = {"generate_at": "2026-01-01T00:00:00Z", "production_authorized": True}
            (root / "due.json").write_text(json.dumps(job))
            (root / "old.completed.json").write_text(json.dumps(job))
            self.assertEqual([root / "due.json"], due_specs(root, datetime(2026, 2, 1, tzinfo=timezone.utc)))

    def test_http_status_attribute_is_retryable(self):
        class APIError(RuntimeError):
            status_code = 429
        attempts = []
        def operation():
            attempts.append(1)
            if len(attempts) == 1:
                raise APIError("rate limited")
            return "ok"
        self.assertEqual("ok", with_retry(operation, sleeper=lambda _: None))
        self.assertEqual(2, len(attempts))

    def test_transient_failure_retries(self):
        attempts = []
        def operation():
            attempts.append(1)
            if len(attempts) == 1:
                raise ConnectionError("temporary")
            return "ok"
        self.assertEqual("ok", with_retry(operation, sleeper=lambda _: None))
        self.assertEqual(2, len(attempts))
