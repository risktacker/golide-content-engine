import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from golide_engine.providers.openai_media import OpenAIImageProvider
from golide_engine.visual_identity import VisualIdentity


class VisualIdentityTests(unittest.TestCase):
    def test_locked_policy_describes_human_paper_cut_avatar_not_toon(self):
        identity = VisualIdentity(Path("config/visual-identity.json"))
        guarded = identity.apply("Esiah reacts to a damaged chip")
        self.assertIn("realistic adult human facial proportions", guarded)
        self.assertIn("normal human eye proportions", guarded)
        self.assertIn("oversized eyes", guarded)
        self.assertIn("Do not reinterpret the avatar as a cartoon", guarded)
        self.assertIn("deep navy", guarded)
        self.assertIn("G$LIDE gold", guarded)

    def test_provider_always_injects_locked_policy(self):
        guarded = OpenAIImageProvider._locked_prompt("A USB controller cutaway")
        self.assertIn("LOCKED G$LIDE VISUAL IDENTITY", guarded)
        self.assertIn("SCENE REQUEST", guarded)
        self.assertIn("A USB controller cutaway", guarded)

    def test_missing_policy_blocks_image_generation_before_api(self):
        provider = OpenAIImageProvider()
        with tempfile.TemporaryDirectory() as temp, patch("pathlib.Path.cwd", return_value=Path(temp)):
            with self.assertRaises(RuntimeError):
                provider._locked_prompt("thumbnail")


if __name__ == "__main__":
    unittest.main()
