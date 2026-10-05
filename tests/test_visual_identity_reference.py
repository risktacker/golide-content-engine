import hashlib
import unittest
from pathlib import Path

from golide_engine.providers.openai_media import OpenAIImageProvider
from golide_engine.visual_identity import VisualIdentity


class VisualIdentityReferenceTests(unittest.TestCase):
    def setUp(self):
        self.identity = VisualIdentity(Path("config/visual-identity.json"))

    def test_canonical_reference_decodes_and_matches_locked_checksum(self):
        reference = self.identity.canonical_avatar_reference()
        self.assertTrue(reference.is_file())
        expected = self.identity.avatar["canonical_reference_sha256"]
        actual = hashlib.sha256(reference.read_bytes()).hexdigest()
        self.assertEqual(expected, actual)

    def test_black_theme_thumbnail_has_no_avatar_unless_asked(self):
        # Locked 2026-10-04: GOLIDE Black thumbnails are single-subject line art.
        refs = OpenAIImageProvider._references_for(
            "Chicken vision stability explainer thumbnail",
            None,
            thumbnail=True,
        )
        self.assertEqual([], refs)

    def test_explicit_avatar_scene_receives_reference_but_topic_scene_does_not(self):
        avatar_refs = OpenAIImageProvider._references_for(
            "G$LIDE Esiah avatar reacting beside a camera gimbal",
            None,
            thumbnail=False,
        )
        topic_refs = OpenAIImageProvider._references_for(
            "Paper-cut chicken head stabilization mechanism diagram",
            None,
            thumbnail=False,
        )
        self.assertEqual(1, len(avatar_refs))
        self.assertEqual([], topic_refs)

    def test_prompt_guard_blocks_substitute_presenters_in_topic_visuals(self):
        prompt = self.identity.apply("Chicken vestibulo-ocular reflex diagram")
        self.assertIn("must not invent a host, presenter or substitute avatar", prompt)


if __name__ == "__main__":
    unittest.main()
