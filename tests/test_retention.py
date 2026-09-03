import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from golide_engine.storage.database import Database
from golide_engine.storage.retention import cleanup_expired_media


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = Database(self.root / "data/golide.sqlite3")
        self.database.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def _production(self, production_id: str, status: str, uploaded_at: str | None):
        spec = {
            "id": production_id,
            "format": "long",
            "concept": {"family": "science", "title": production_id},
            "title": production_id,
            "release": {"approved": True},
            "generation_parameters": {},
        }
        self.database.upsert_production(spec, status)
        self.database.execute(
            "UPDATE productions SET status=?, youtube_video_id=? WHERE production_id=?",
            (status, f"yt-{production_id}" if uploaded_at else None, production_id),
        )
        if uploaded_at:
            self.database.execute(
                """INSERT INTO uploads
                   (production_id, youtube_video_id, privacy_status, upload_status,
                    request_fingerprint, uploaded_at, updated_at)
                   VALUES (?, ?, 'private', ?, ?, ?, ?)""",
                (
                    production_id, f"yt-{production_id}", status,
                    f"fp-{production_id}", uploaded_at, uploaded_at,
                ),
            )
        for directory in ("productions", "build", "release-packages", "generated"):
            target = self.root / directory / production_id
            target.mkdir(parents=True, exist_ok=True)
            (target / "keep.bin").write_bytes(b"media")

    def test_generated_but_never_uploaded_is_never_purged(self):
        self._production("not-uploaded", "qa_blocked", None)
        now = datetime(2026, 9, 3, 12, tzinfo=timezone.utc)
        self.assertEqual([], cleanup_expired_media(self.root, self.database, now))
        self.assertTrue((self.root / "generated/not-uploaded/keep.bin").exists())

    def test_uploaded_media_is_retained_before_48_hours(self):
        now = datetime(2026, 9, 3, 12, tzinfo=timezone.utc)
        uploaded = (now - timedelta(hours=47, minutes=59)).isoformat()
        self._production("fresh-upload", "published", uploaded)
        self.assertEqual([], cleanup_expired_media(self.root, self.database, now))
        self.assertTrue((self.root / "build/fresh-upload/keep.bin").exists())

    def test_successful_terminal_upload_is_purged_after_48_hours(self):
        now = datetime(2026, 9, 3, 12, tzinfo=timezone.utc)
        uploaded = (now - timedelta(hours=48, minutes=1)).isoformat()
        self._production("old-upload", "published", uploaded)
        purged = cleanup_expired_media(self.root, self.database, now)
        self.assertEqual("old-upload", purged[0]["production_id"])
        for directory in ("productions", "build", "release-packages", "generated"):
            self.assertFalse((self.root / directory / "old-upload").exists())
        row = self.database.rows(
            "SELECT media_purged_at FROM uploads WHERE production_id='old-upload'"
        )[0]
        self.assertIsNotNone(row["media_purged_at"])

    def test_correction_state_is_retained_even_with_old_upload_timestamp(self):
        now = datetime(2026, 9, 3, 12, tzinfo=timezone.utc)
        uploaded = (now - timedelta(days=4)).isoformat()
        self._production("correction", "correction_required", uploaded)
        self.assertEqual([], cleanup_expired_media(self.root, self.database, now))
        self.assertTrue((self.root / "productions/correction/keep.bin").exists())


if __name__ == "__main__":
    unittest.main()
