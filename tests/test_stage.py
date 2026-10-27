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
        self.assertLess(float(image[row].max()), 0.45 * float(image.max()))

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
