"""Order on screen (owner direction 2026-10-18): no text touches a line or another text."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from golide_engine.vector.figures import EXAMPLES, render_figure, sidecar_path


def collisions(spec: str, size) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = render_figure(spec, Path(tmp) / "f.png", size)
        meta = json.loads(sidecar_path(path).read_text())
        mask = Image.new("L", (meta["width"], meta["height"]), 0)
        draw = ImageDraw.Draw(mask)
        for stroke in meta["strokes"]:
            draw.line([tuple(p) for p in stroke["points"]], fill=255, width=max(1, round(stroke["width"])))
        lines = np.asarray(mask) > 0
        boxes = []
        for label in meta["labels"]:
            alpha = np.asarray(Image.open(Path(tmp) / label["file"]))[..., 3] > 40
            ys, xs = np.nonzero(alpha)
            if len(xs):
                boxes.append((label["text"], int(label["x"] + xs.min()), int(label["y"] + ys.min()),
                              int(label["x"] + xs.max()), int(label["y"] + ys.max())))
        found = [f"a line runs through '{t}'" for t, x0, y0, x1, y1 in boxes
                 if lines[max(0, y0):y1 + 1, max(0, x0):x1 + 1].any()]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                if a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]:
                    found.append(f"'{a[0]}' overlaps '{b[0]}'")
        return found


class NoCollisionTests(unittest.TestCase):
    def test_every_figure_kind_portrait_and_landscape(self):
        for kind, example in EXAMPLES.items():
            spec = example.split("  (")[0].strip()
            for size in ((1024, 1536), (1536, 1024)):
                with self.subTest(kind=kind, size=size):
                    self.assertEqual(collisions(spec, size), [])

    def test_owner_reported_cases(self):
        for spec in ("forces: 80@0; 20@180; unit=kN", "motion: points=0,0 1,26.8",
                     "motion: points=0,0 4,20 10,20 12,0"):
            with self.subTest(spec=spec):
                self.assertEqual(collisions(spec, (1024, 1536)), [])


class CardZoneTests(unittest.TestCase):
    def test_number_zone_is_clear_of_the_drawing_area(self):
        from golide_engine.vector.illustrate import REGIONS
        from golide_engine.vector.render import Layout

        for fmt in ("short", "long"):
            layout = Layout.for_format(fmt)
            drawing_top = layout.cy + REGIONS[fmt][1] * layout.size / 2
            self.assertLessEqual(layout.card_zone[1], drawing_top, fmt)
            self.assertGreater(layout.card_zone[0], 0)

    def test_card_fits_its_zone(self):
        from golide_engine.vector.render import CaptionRenderer, Layout
        from golide_engine.theme import load_theme

        for fmt in ("short", "long"):
            layout = Layout.for_format(fmt)
            tile = CaptionRenderer(layout, load_theme()).number_card("$552 BILLION", (233, 196, 106), 1.0, 1.0)
            self.assertLessEqual(tile.width, layout.width)


if __name__ == "__main__":
    unittest.main()
