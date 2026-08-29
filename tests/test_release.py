import json
import tempfile
import unittest
from pathlib import Path

from golide_engine.release.package import ReleasePackager


class ReleasePackageTests(unittest.TestCase):
    def test_builds_and_verifies_checksummed_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = {}
            names = {
                "video": "video.mp4", "thumbnail": "thumbnail.png", "metadata": "metadata.json",
                "spoken_captions": "spoken.srt", "visual_captions": "visual.srt",
                "source_ledger": "sources.json", "generation_parameters": "params.json", "qa_report": "qa.json",
            }
            for role, name in names.items():
                path = root / name
                path.write_text('{"passed": true}' if role == "qa_report" else role)
                files[role] = path
            packager = ReleasePackager(root / "releases")
            archive = packager.build("p1", files, {"approved": True}, {"total_usd": 0.2})
            self.assertTrue(archive.exists())
            package = root / "releases" / "p1"
            self.assertEqual([], packager.verify(package))
            (package / "video.mp4").write_text("changed")
            self.assertIn("video: checksum mismatch", packager.verify(package))
