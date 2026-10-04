import tempfile
import unittest
from pathlib import Path

from golide_engine.engine.social_image import SocialImageProfile
from golide_engine.engine.typeset import compose_post, tokenize


class BlackThemeStillTests(unittest.TestCase):
    def test_prompt_is_black_theme_and_forbids_text(self):
        prompt = SocialImageProfile("config/social-image-profile.json").build_prompt(
            concept="A glass jar holding one small key.", glow_color="cyan")
        for phrase in ("Pure black", "Exactly one element", "bottom third", "ABSOLUTELY NO text", "cyan"):
            self.assertIn(phrase, prompt)

    def test_emphasis_phrase_is_marked(self):
        tokens = tokenize("Most people never notice who holds the key", "holds the key")
        self.assertEqual([t.text for t in tokens if t.emphasis], ["holds", "the", "key"])

    def test_compose_outputs_platform_sizes(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            master = Path(tmp) / "m.png"
            Image.new("RGB", (1024, 1536), (11, 11, 14)).save(master)
            for size in ((1080, 1350), (1080, 1080)):
                out = Path(tmp) / f"{size[1]}.jpg"
                compose_post(master, "Your words build the first minute", "first minute", out, size)
                with Image.open(out) as image:
                    self.assertEqual(image.size, size)


if __name__ == "__main__":
    unittest.main()
