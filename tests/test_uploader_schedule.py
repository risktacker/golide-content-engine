import os
import unittest
from unittest.mock import patch

from golide_engine.youtube.uploader import YouTubeUploader


class _Request:
    def execute(self):
        return {"ok": True}


class _Videos:
    def __init__(self):
        self.body = None

    def update(self, *, part, body):
        self.body = body
        return _Request()


class _YouTube:
    def __init__(self):
        self.resource = _Videos()

    def videos(self):
        return self.resource


class _Database:
    def __init__(self):
        self.calls = []

    def execute(self, query, parameters=()):
        self.calls.append((query, parameters))


class UploaderScheduleTests(unittest.TestCase):
    def test_missed_approved_release_publishes_after_qa(self):
        youtube = _YouTube()
        database = _Database()
        release = {
            "approved": True,
            "qa": {"passed": True},
            "channel_id": "channel-1",
        }
        with patch.dict(os.environ, {"GOLIDE_ENABLE_YOUTUBE_UPLOAD": "1"}):
            YouTubeUploader(youtube, database, "channel-1").schedule(
                "production-1", "video-1", "2020-01-01T00:00:00Z", release
            )
        self.assertEqual("public", youtube.resource.body["status"]["privacyStatus"])
        self.assertNotIn("publishAt", youtube.resource.body["status"])
        self.assertTrue(any("status=?" in query and params[0] == "published"
                            for query, params in database.calls))


if __name__ == "__main__":
    unittest.main()
