import os
import tempfile
import unittest
from pathlib import Path

from golide_engine.storage.database import Database
from golide_engine.youtube.uploader import YouTubeUploader


class YouTubeGateTests(unittest.TestCase):
    def test_upload_lock_blocks_before_network(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Database(Path(temp) / "db.sqlite3")
            database.initialize()
            os.environ.pop("GOLIDE_ENABLE_YOUTUBE_UPLOAD", None)
            uploader = YouTubeUploader(object(), database, "channel")
            with self.assertRaisesRegex(RuntimeError, "lock is closed"):
                uploader._assert_release({"approved": True, "qa": {"passed": True}, "channel_id": "channel"})

    def test_wrong_channel_blocks_even_when_enabled(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Database(Path(temp) / "db.sqlite3")
            database.initialize()
            os.environ["GOLIDE_ENABLE_YOUTUBE_UPLOAD"] = "1"
            try:
                with self.assertRaisesRegex(RuntimeError, "wrong YouTube channel"):
                    YouTubeUploader(object(), database, "expected")._assert_release({"approved": True, "qa": {"passed": True}, "channel_id": "other"})
            finally:
                os.environ.pop("GOLIDE_ENABLE_YOUTUBE_UPLOAD", None)
