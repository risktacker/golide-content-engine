"""The real illustration on screen (owner direction 2026-10-22: "let the illustrations
be more real and of quality"; broken stick-figure cars on the Roadster video)."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from golide_engine.vector import artwork
from golide_engine.vector.illustrate import picture_problems, vectorize


def car(width: int = 4, shaded: bool = False, glow: bool = False, gold_wheels: bool = False) -> Image.Image:
    im = Image.new("RGB", (1536, 1024), "black")
    d = ImageDraw.Draw(im)
    if shaded:
        d.rounded_rectangle((350, 420, 1180, 640), 60, fill=(95, 95, 100))
    white, gold = (235, 235, 235), (233, 190, 90)
    d.rounded_rectangle((350, 420, 1180, 640), 60, outline=white, width=width)
    d.line([(520, 420), (640, 300), (900, 300), (1010, 420)], fill=white, width=width)
    for cx in (520, 1010):
        d.ellipse((cx - 85, 560, cx + 85, 730), outline=gold if gold_wheels else white, width=width)
    d.line([(200, 735), (1340, 735)], fill=(200, 200, 200), width=max(2, width // 2))
    if glow:
        # Like the 22 Oct pictures: soft lines inside a wide glowing haze.
        soft = im.filter(ImageFilter.GaussianBlur(3))
        halo = im.filter(ImageFilter.GaussianBlur(30)).point(lambda v: min(255, int(v * 6)))
        im = Image.fromarray(np.maximum(np.asarray(soft), np.asarray(halo)))
    return im


def save(im: Image.Image, folder: str, name: str) -> Path:
    path = Path(folder) / name
    im.save(path)
    return path


class LineLayerTests(unittest.TestCase):
    def test_a_shaded_panel_is_not_line(self):
        alpha, _, _, _ = artwork.line_layer(np.asarray(car(shaded=True), np.float32))
        self.assertLess(alpha[530, 760], 0.1)            # inside the shaded body panel
        self.assertGreater(alpha[420:424, 760].max(), 0.6)  # the body's top edge

    def test_glow_halos_are_measured_and_removed(self):
        rgb = np.asarray(car(glow=True), np.float32)
        alpha, _, haze, _ = artwork.line_layer(rgb)
        self.assertGreater(haze, 0.6)   # a blurred picture reads as hazy
        self.assertLess(alpha[470, 760], 0.1)                     # halo space between lines stays dark
        crisp = artwork.line_layer(np.asarray(car(), np.float32))[2]
        self.assertLess(crisp, 0.3)

    def test_accent_part_is_found_and_all_gold_is_flagged(self):
        _, accent, _, all_gold = artwork.line_layer(np.asarray(car(gold_wheels=True), np.float32))
        self.assertFalse(all_gold)
        self.assertTrue(accent[640:650, 430:440].any() or accent[560:735, 430:610].any())
        self.assertFalse(accent[300:304, 700:800].any())


class VectorizeTests(unittest.TestCase):
    def test_shaded_car_keeps_its_outline_and_carries_the_art(self):
        with tempfile.TemporaryDirectory() as tmp:
            drawing = vectorize(save(car(shaded=True), tmp, "c.png"))
        self.assertIsNotNone(drawing.art)
        self.assertIsNone(drawing.fill)                    # no more hatched blobs
        x0, y0, x1, y1 = drawing.bbox
        scale = drawing.art.scale
        # The bbox spans the whole car, not a skeleton in the middle of the panel.
        self.assertLess(x0 * scale, 360 * 1280 / 1536)
        self.assertGreater(x1 * scale, 1170 * 1280 / 1536)
        self.assertEqual(drawing.art.tmap.shape, drawing.art.alpha.shape)

    def test_no_spur_hairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            drawing = vectorize(save(car(width=10), tmp, "c.png"))
        short = [s for s in drawing.strokes if s.length < 12]
        self.assertLessEqual(len(short), 2)

    def test_blurred_picture_is_reported_for_a_redraw(self):
        with tempfile.TemporaryDirectory() as tmp:
            drawing = vectorize(save(car(glow=True), tmp, "c.png"))
        self.assertTrue(any("blurred" in p for p in picture_problems(drawing)))


class RevealTests(unittest.TestCase):
    def test_reveal_follows_the_pen_and_ends_on_the_whole_art(self):
        with tempfile.TemporaryDirectory() as tmp:
            drawing = vectorize(save(car(), tmp, "c.png"))
        art = drawing.art
        white, gold = (1.0, 1.0, 1.0), (0.9, 0.7, 0.3)

        def shown(done):
            main, _ = artwork.frame_surfaces(art, done, white, gold)
            data = np.frombuffer(main.get_data(), np.uint8).reshape(art.shape + (4,))
            return float((data[..., 3] > 40).sum())

        nothing, half, full = shown(0.0), shown(0.5), shown(1.0)
        self.assertLess(nothing, full * 0.05)
        self.assertTrue(full * 0.2 < half < full * 0.95)
        self.assertAlmostEqual(full, float((art.alpha * 255 > 40).sum()), delta=full * 0.01)

    def test_every_inked_pixel_gets_a_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            drawing = vectorize(save(car(), tmp, "c.png"))
        tmap = drawing.art.tmap[drawing.art.alpha > 0.2]
        self.assertTrue(np.all((tmap >= 0) & (tmap <= 1)))


class PromptTests(unittest.TestCase):
    def test_prompt_asks_for_crisp_accurate_art_without_glow(self):
        from golide_engine.vector.illustrate import illustration_prompt

        prompt = illustration_prompt("a sports car on a road", "the wheels", "long")
        self.assertNotIn("glowing pen", prompt)
        self.assertIn("correct proportions", prompt)
        self.assertIn("No glow, no blur", prompt)
        self.assertIn("Nothing else is gold", prompt)

    def test_real_products_are_drawn_as_themselves(self):
        # 22 Oct: "we are talking about a Tesla Roadster, not a Honda Fit"; thrusters are air vents.
        from golide_engine.vector.illustrate import scene_plan_instructions
        from golide_engine.vector.thumbnail_style import thumbnail_prompt

        rules = scene_plan_instructions("long", 300.0)
        self.assertIn("THE REAL THING, NOT A GENERIC ONE", rules)
        self.assertIn("not rocket flames", rules)
        thumb = thumbnail_prompt("Elon Musk New Flying Car Explained", "a Tesla Roadster lifting off", ["rose"])
        self.assertIn("real, recognisable design", thumb)


if __name__ == "__main__":
    unittest.main()
