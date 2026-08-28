import json
import tempfile
import unittest
from pathlib import Path

from golide_engine.manifest import load_project
from golide_engine.models import ManifestError


class ManifestTests(unittest.TestCase):
    def test_short_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.json"
            path.write_text(json.dumps({
                "id": "x", "title": "x", "format": "short", "max_cost_usd": 1,
                "narration": "voice.mp3",
                "scenes": [{"id": "a", "media": "a.png", "duration": 5}],
            }))
            project = load_project(path)
            self.assertEqual((project.width, project.height), (1080, 1920))

    def test_long_rejects_over_five_minutes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.json"
            path.write_text(json.dumps({
                "id": "x", "title": "x", "format": "long", "max_cost_usd": 3,
                "narration": "voice.mp3",
                "scenes": [{"id": "a", "media": "a.png", "duration": 301}],
            }))
            with self.assertRaises(ManifestError):
                load_project(path)


if __name__ == "__main__":
    unittest.main()

