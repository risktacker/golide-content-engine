"""Long-video layouts (owner direction 2026-10-16): wide, duo and single scenes."""

import unittest

from golide_engine.vector.layouts import art_size, duo_regions, normalize, second_id
from golide_engine.vector.scene_art import parts


def _scene(i, layout, b=""):
    return {"id": f"scene-{i:02d}", "first_line": i, "last_line": i, "drawing": "a", "gold_element": "g",
            "figure": "", "layout": layout, "drawing_b": b, "gold_element_b": "g" if b else "", "figure_b": ""}


class LayoutTests(unittest.TestCase):
    def test_shorts_are_always_single(self):
        scenes = normalize([_scene(0, "duo", "b"), _scene(1, "wide")], "short")
        self.assertEqual([s["layout"] for s in scenes], ["single", "single"])
        self.assertEqual(scenes[0]["drawing_b"], "")

    def test_duo_needs_a_second_drawing_and_is_capped(self):
        scenes = normalize([_scene(i, "duo", "b") for i in range(6)] + [_scene(6, "duo")], "long")
        layouts = [s["layout"] for s in scenes]
        self.assertEqual(layouts.count("duo"), 2)          # one in three of seven scenes
        self.assertEqual(layouts[-1], "wide")             # no second drawing: becomes wide
        self.assertTrue(all(s["drawing_b"] == "" for s in scenes if s["layout"] != "duo"))

    def test_duo_has_two_pictures(self):
        scene = normalize([_scene(0, "duo", "right side")], "long")[0]
        got = parts(scene)
        self.assertEqual([p.picture_id for p in got], ["scene-00", second_id("scene-00")])
        self.assertEqual(art_size("long", "duo"), "1024x1024")
        self.assertEqual(art_size("long", "wide"), "1536x1024")

    def test_duo_halves_split_the_region(self):
        left, right = duo_regions((-2.0, -0.77, 2.0, 1.12))
        self.assertLess(left[2], right[0])
        self.assertAlmostEqual(left[0], -2.0)
        self.assertAlmostEqual(right[2], 2.0)

    def test_storyboard_schema_has_layout(self):
        from golide_engine.vector.illustrate import VISUAL_PLAN_SCHEMA, scene_plan_instructions

        props = VISUAL_PLAN_SCHEMA["properties"]["scenes"]["items"]["properties"]
        self.assertEqual(props["layout"]["enum"], ["single", "wide", "duo"])
        self.assertIn('"duo"', scene_plan_instructions("long"))

    def test_prompt_follows_layout(self):
        from golide_engine.vector.illustrate import illustration_prompt

        self.assertIn("Panoramic", illustration_prompt("a street", "the bus", "long", "wide"))
        self.assertIn("Square", illustration_prompt("a cup", "the steam", "long", "duo"))
        self.assertIn("Portrait", illustration_prompt("a cup", "the steam", "short", "duo"))


class DuoRenderTests(unittest.TestCase):
    def test_duo_scene_loads_both_drawings(self):
        import tempfile
        from pathlib import Path

        from golide_engine.vector.align import align_lines
        from golide_engine.vector.figures import render_figure
        from golide_engine.vector.illustrate import SCENES
        from golide_engine.vector.render import VectorRenderer

        with tempfile.TemporaryDirectory() as tmp:
            a = render_figure("reflection: angle=40", Path(tmp) / "scene-01.png", (1024, 1024))
            b = render_figure("refraction: angle=40", Path(tmp) / "scene-01-b.png", (1024, 1024))
            plan = {"title": "t", "lines": [{"section": "proof", "text": "Light bounces and bends.",
                                             "emphasis": "bends", "visual": "icon_hero", "label": ""}],
                    "scenes": [{**_scene(0, "duo", "x"), "id": "scene-01", "figure": "f", "figure_b": "f"}]}
            words = [{"word": w, "start": 0.3 * i, "end": 0.3 * i + 0.25} for i, w in enumerate("Light bounces and bends.".split())]
            lines = align_lines(plan, words, 2.0)
            VectorRenderer._use_illustrations(plan, lines, {"scene-01": a, "scene-01-b": b})
            self.assertIsNotNone(SCENES["scene-01"].companion)
            self.assertEqual(lines[0].visual, "illustration")


if __name__ == "__main__":
    unittest.main()
