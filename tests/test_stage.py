import unittest

import numpy as np

from golide_engine.vector.render import Layout
from golide_engine.vector.stage import KINDS, Stages, set_colour


class StageTests(unittest.TestCase):
    """2026-10-27: every drawing stands in a set, drawn in code, quiet behind the captions."""

    def test_every_set_draws_something_and_none_draws_nothing(self):
        for fmt in ("long", "short"):
            stages = Stages(Layout.for_format(fmt), fmt)
            for kind in KINDS:
                image = stages.image(kind, (110, 220, 200))
                if kind == "none":
                    self.assertIsNone(image)
                else:
                    self.assertGreater(float(image.max()), 20, f"{fmt} {kind}")

    def test_sets_stay_quiet_behind_the_captions(self):
        layout = Layout.for_format("long")
        image = Stages(layout, "long").image("grid", (110, 220, 200))
        row = int(layout.caption_y + layout.caption_size * 0.5)
        self.assertLess(float(image[row].max()), 45.0)   # a faint lift (0-255) under the words

    def test_warm_accents_never_fill_a_set(self):
        self.assertEqual(tuple(set_colour((233, 196, 106))), (110.0, 220.0, 200.0))
        self.assertEqual(tuple(set_colour((115, 165, 250))), (115.0, 165.0, 250.0))

    def test_storyboard_chooses_a_stage(self):
        from golide_engine.vector.illustrate import VISUAL_PLAN_SCHEMA, scene_plan_instructions
        scene = VISUAL_PLAN_SCHEMA["properties"]["scenes"]["items"]
        self.assertIn("stage", scene["required"])
        self.assertIn("STAGE", scene_plan_instructions("long", 400.0))


if __name__ == "__main__":
    unittest.main()


class MoneyTests(unittest.TestCase):
    """2026-10-27: money and markets are drawn exactly, with their real structure."""

    def test_chart_figure_draws_all_three_kinds(self):
        import tempfile
        from pathlib import Path
        from golide_engine.vector.figures import render_figure
        with tempfile.TemporaryDirectory() as tmp:
            for spec in ("chart: type=candles; values=100,104,101,108; unit=$; label=NVDA",
                         "chart: type=bar; values=12,18,25,40; labels=2023,2024,2025,2026",
                         "chart: type=line; values=9,7,6,4; unit=%"):
                out = render_figure(spec, Path(tmp) / "c.png", (1536, 1024))
                self.assertTrue(Path(out).exists())

    def test_storyboard_knows_money_objects_and_alignment(self):
        from golide_engine.vector.illustrate import scene_plan_instructions
        text = scene_plan_instructions("long", 400.0)
        for word in ("reeded", "pediment", "MONEY AND BUSINESS", "ALIGNMENT", "chart: type=candles"):
            self.assertIn(word, text)


class LayerTests(unittest.TestCase):
    """2026-10-29: background behind, stage below, the object in front, colours apart."""

    def test_floor_starts_where_the_object_stands(self):
        layout = Layout.for_format("long")
        stages = Stages(layout, "long")
        bottom = layout.height * 0.62
        image = stages.image("grid", (115, 165, 250), (layout.width * 0.3, layout.width * 0.7, bottom))
        shadow_row = int(np.unravel_index(np.argmin(image.sum(axis=2)), image.shape[:2])[0])
        self.assertLess(abs(shadow_row - bottom), layout.height * 0.02)   # the contact shadow sits under it
        other = stages.image("grid", (115, 165, 250), (layout.width * 0.3, layout.width * 0.7, layout.height * 0.5))
        self.assertFalse(np.array_equal(image, other))                     # and the floor moves with it

    def test_wall_is_dimmer_than_the_stage(self):
        layout = Layout.for_format("long")
        stages = Stages(layout, "long")
        from golide_engine.vector.stage import WALL
        col = np.array((115, 165, 250), np.float32)
        raw = stages._factory(col)
        layered = stages._planes(raw, col, None, floor_set=True)
        fy = int(stages.floor)
        wall_rows = slice(fy - 300, fy - 40)
        self.assertLessEqual(float(layered[wall_rows].sum()), float(raw[wall_rows].sum()) * (WALL + 0.05))

    def test_set_never_takes_the_objects_colour(self):
        from golide_engine.vector.stage import SAME_COLOUR, separate
        teal = np.array((110, 220, 200), np.float32)
        moved = separate(teal, (110, 220, 200))
        self.assertGreater(float(np.linalg.norm(moved - teal)), SAME_COLOUR)

    def test_object_shape_is_cut_out_of_the_set(self):
        from golide_engine.vector.render import VectorRenderer
        r = VectorRenderer("long")
        h, w = r.layout.height, r.layout.width
        alpha = np.zeros((h, w, 1), np.float32)
        yy, xx = np.mgrid[0:h, 0:w]
        ring = np.abs(np.hypot(xx - w / 2, yy - h / 2) - 200) < 3
        alpha[ring] = 1.0
        body = r._body(alpha)
        self.assertGreater(float(body[h // 2, w // 2, 0]), 0.9)   # the inside of a closed outline
        self.assertLess(float(body[h // 2, w // 2 + 400, 0]), 0.05)


class NoCollisionTests(unittest.TestCase):
    """2026-10-29: "never collide objects with background and stage"."""

    def test_every_set_keeps_the_object_box_clear(self):
        layout = Layout.for_format("short")
        stages = Stages(layout, "short")
        foot = (layout.width * 0.22, layout.width * 0.78, layout.height * 0.55, layout.height * 0.22)
        for kind in KINDS[:-1]:
            stages.image(kind, (115, 165, 250), foot)
        self.assertEqual(stages.fallbacks, 0)

    def test_a_set_that_lights_the_object_box_falls_back_to_grid(self):
        layout = Layout.for_format("long")
        stages = Stages(layout, "long")
        foot = (layout.width * 0.3, layout.width * 0.7, layout.height * 0.62, layout.height * 0.2)
        bright = np.full((layout.height, layout.width, 3), 120.0, np.float32)
        self.assertTrue(stages.collides(bright, (576, 1344, 672, 216)))
        stages._market = lambda col: bright           # a set that floods the object's box
        stages.image("market", (115, 165, 250), foot)
        self.assertEqual(stages.fallbacks, 1)

    def test_storyboard_offers_only_the_new_sets(self):
        from golide_engine.vector.illustrate import VISUAL_PLAN_SCHEMA
        enum = VISUAL_PLAN_SCHEMA["properties"]["scenes"]["items"]["properties"]["stage"]["enum"]
        self.assertEqual(set(enum), set(KINDS) - {"none"})
