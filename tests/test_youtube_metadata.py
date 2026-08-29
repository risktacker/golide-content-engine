import unittest
from pathlib import Path

from golide_engine.youtube_metadata import (
    YouTubeMetadataError,
    load_metadata_policy,
    validate_chapters,
    validate_upload_metadata,
)


class YouTubeMetadataTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_metadata_policy(Path("config/youtube-metadata-policy.json"))

    def test_valid_long_metadata(self):
        validate_upload_metadata({
            "format": "long",
            "title": "The Invisible Particles Rewriting Computer Memory",
            "description": "A visual explanation.\n\n#Science",
            "tags": ["cosmic rays", "computer memory", "GOLIDE"],
            "video_language": "en",
            "altered_content": False,
            "chapters": ["00:00 The impossible error", "00:20 The particle", "00:50 The protection"],
        }, self.policy)

    def test_rejects_hashtag_in_title(self):
        with self.assertRaises(YouTubeMetadataError):
            validate_upload_metadata({
                "format": "short", "title": "Cosmic Rays #Shorts", "description": "",
                "tags": [], "video_language": "en", "altered_content": False,
            }, self.policy)

    def test_chapters_require_ten_seconds(self):
        with self.assertRaises(YouTubeMetadataError):
            validate_chapters(["00:00 A", "00:05 B", "00:20 C"])

    def test_location_cannot_be_used_as_targeting(self):
        with self.assertRaises(YouTubeMetadataError):
            validate_upload_metadata({
                "format": "short", "title": "A Computer Error From Space", "description": "",
                "tags": [], "video_language": "en", "altered_content": False,
                "recording_location": "Zambia", "location_is_material": False,
            }, self.policy)


if __name__ == "__main__":
    unittest.main()
