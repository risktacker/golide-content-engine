import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from golide_engine.vector.illustrate import illustration_prompt, validate_scenes, vectorize


def _drawing(path: Path) -> Path:
    image = Image.new("RGB", (400, 600), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 120, 320, 420), outline=(240, 240, 240), width=3)  # a box
    draw.line((80, 120, 200, 40, 320, 120), fill=(240, 240, 240), width=3)  # a roof
    draw.ellipse((170, 220, 230, 280), outline=(233, 196, 106), width=3)  # gold window
    image.save(path)
    return path


class IllustrationTests(unittest.TestCase):
    def test_line_art_becomes_ordered_strokes_with_gold_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            drawing = vectorize(_drawing(Path(tmp) / "house.png"))
        self.assertGreater(drawing.total, 900)
        golds = [s.gold for s in drawing.strokes]
        self.assertIn(True, golds)
        self.assertEqual(golds, sorted(golds))  # white first, gold strokes last
        x0, y0, x1, y1 = drawing.bbox
        self.assertLess(x0, 90)
        self.assertGreater(y1, 410)

    def test_scenes_cover_every_line_once(self):
        scenes = validate_scenes([
            {"first_line": 0, "last_line": 3, "drawing": "a", "gold_element": "g"},
            {"first_line": 2, "last_line": 6, "drawing": "b", "gold_element": "g"},  # overlaps
            {"first_line": 9, "last_line": 9, "drawing": "c", "gold_element": "g"},  # leaves a gap
        ], 12)
        self.assertEqual([(s["first_line"], s["last_line"]) for s in scenes], [(0, 3), (4, 6), (7, 11)])
        self.assertEqual(scenes[0]["id"], "scene-01")

    def test_prompt_locks_the_style(self):
        prompt = illustration_prompt("a server rack with heat rising", "the heat lines", "short")
        for phrase in ("pure flat black", "No text", "warm gold", "server rack", "margins on the left and right"):
            self.assertIn(phrase, prompt)


if __name__ == "__main__":
    unittest.main()
