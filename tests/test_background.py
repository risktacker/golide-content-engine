"""The background answers the scene on screen, quietly (owner direction 2026-10-18)."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from golide_engine.vector.ambience import AmbientState, Ambience, StarField, crossfade, mix
from golide_engine.vector.render import Layout
from golide_engine.theme import load_theme

TEAL, ROSE = (127, 224, 210), (240, 138, 128)


def _ambience(fmt):
    layout = Layout.for_format(fmt)
    return layout, Ambience(layout, load_theme(), fmt)


class BackgroundTests(unittest.TestCase):
    def test_nothing_coloured_behind_captions_or_number_cards(self):
        for fmt in ("short", "long"):
            layout, amb = _ambience(fmt)
            a = amb.frame(3.0, AmbientState(TEAL, 1.0, 0.05))
            b = amb.frame(3.0, AmbientState(ROSE, 1.0, 0.05))
            top = slice(0, int(layout.card_zone[1]))
            caption = slice(int(layout.caption_y - layout.caption_size), layout.height)
            for band in (top, caption):
                self.assertTrue(np.allclose(a[band], b[band]), fmt)
                self.assertTrue(np.allclose(amb.sky(AmbientState(TEAL, 1.0))[band], amb.base[band]), fmt)

    def test_scene_light_takes_the_scene_colour_and_stays_quiet(self):
        layout, amb = _ambience("long")
        lit = amb.sky(AmbientState(TEAL, 0.0)) - amb.base
        centre = lit[int(layout.cy), int(layout.cx)]
        self.assertGreater(centre[1], centre[0])          # teal: more green than red
        self.assertLess(lit.max(), 0.11 * 255)            # never louder than a tenth
        dark = amb.sky(AmbientState(TEAL, 0.0, light=0.0)) - amb.base
        self.assertAlmostEqual(float(np.abs(dark).max()), 0.0)

    def test_grid_only_on_lesson_scenes(self):
        _, amb = _ambience("short")
        story = amb.sky(AmbientState(TEAL, 0.0)).copy()
        lesson = amb.sky(AmbientState(TEAL, 1.0))
        self.assertGreater(float((lesson - story).max()), 4.0)
        self.assertGreaterEqual(float((lesson - story).min()), -1e-4)

    def test_lit_sky_is_cached_between_scene_changes(self):
        _, amb = _ambience("short")
        first = amb.sky(AmbientState(TEAL, 1.0))
        self.assertIs(first, amb.sky(AmbientState(TEAL, 1.0, push=0.03)))

    def test_cross_fade_is_smooth_and_complete(self):
        weights = [crossfade(t, 10.0, 0.4, 0.9) for t in np.arange(9.0, 11.5, 0.033)]
        self.assertEqual(0.0, weights[0])
        self.assertEqual(1.0, weights[-1])
        self.assertTrue(all(b >= a for a, b in zip(weights, weights[1:])))
        self.assertLess(max(b - a for a, b in zip(weights, weights[1:])), 0.05)
        half = mix(AmbientState(TEAL, 1.0, 0.06), AmbientState(ROSE, 0.0, 0.0), 0.5)
        self.assertEqual(0.5, half.lesson)
        self.assertAlmostEqual(0.03, half.push)

    def test_near_stars_move_more_than_far_ones_on_a_push(self):
        stars = StarField(400, 400, centre=(200, 200))
        still = stars.add(np.zeros((400, 400, 3), np.float32), 1.0, AmbientState(push=0.0))
        pushed = stars.add(np.zeros((400, 400, 3), np.float32), 1.0, AmbientState(push=0.08))
        self.assertFalse(np.allclose(still, pushed))
        self.assertLess(stars.layers[0]["parallax"], stars.layers[-1]["parallax"])

    def test_exact_figures_are_marked_as_lessons(self):
        from golide_engine.vector.figures import render_figure
        from golide_engine.vector.illustrate import load_figure

        with tempfile.TemporaryDirectory() as temp:
            path = render_figure("right_triangle: a=3; b=4", Path(temp) / "f.png", (800, 800))
            self.assertTrue(load_figure(path).figure)


if __name__ == "__main__":
    unittest.main()
