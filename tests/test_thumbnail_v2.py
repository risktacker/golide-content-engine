import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from golide_engine.vector.thumbnail_v2 import art_left_edge, stamp_overlap, thumbnail_prompt_v2, video_id


class ThumbnailV2Tests(unittest.TestCase):
    """2026-10-25: draw the real product from a reference; words never hide the art."""

    def test_video_id_from_urls(self):
        self.assertEqual("Nt6d62vN7CU", video_id("https://www.youtube.com/watch?v=Nt6d62vN7CU"))
        self.assertEqual("", video_id(""))

    def test_reference_prompt_asks_for_that_exact_product(self):
        self.assertIn("Draw THAT exact product", thumbnail_prompt_v2("t", "the Microduck", ["teal"], True))
        self.assertIn("left 42 percent", thumbnail_prompt_v2("t", "x", ["gold"], False))

    def test_words_end_before_the_art(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jpg"
            image = Image.new("RGB", (1280, 720), (10, 10, 14))
            ImageDraw.Draw(image).ellipse((640, 120, 1150, 650), fill=(200, 170, 60))
            image.save(path)
            edge = art_left_edge(image)
            self.assertAlmostEqual(0.5, edge, delta=0.03)
            stamp_overlap(path, "The Robot Wasn't the Story", "Robot", [(110, 220, 200)])
            out = np.asarray(Image.open(path).convert("RGB")).astype(int)
            white = np.argwhere((out > 225).all(axis=2))
            self.assertTrue(len(white))
            self.assertLess(white[:, 1].max(), 640)


if __name__ == "__main__":
    unittest.main()
