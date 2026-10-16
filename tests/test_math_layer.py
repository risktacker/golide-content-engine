"""Math layer (owner direction 2026-10-16): exact figures drawn in code."""

import json
import math
import tempfile
import unittest
from pathlib import Path

from golide_engine.vector.figures import FigureError, check_figure, parse_figure, render_figure, sidecar_path


def _render(spec: str, size=(1024, 1536)):
    tmp = tempfile.TemporaryDirectory()
    path = render_figure(spec, Path(tmp.name) / "scene-01.png", size)
    meta = json.loads(sidecar_path(path).read_text())
    return tmp, path, meta


def _texts(meta) -> list[str]:
    return [label["text"] for label in meta["labels"]]


class SpecTests(unittest.TestCase):
    def test_parses_kind_params_and_items(self):
        kind, params, items = parse_figure("Forces: 20@0; 15@120; unit=kN")
        self.assertEqual(kind, "forces")
        self.assertEqual(params, {"unit": "kN"})
        self.assertEqual(items, ["20@0", "15@120"])

    def test_unknown_or_bad_specs_are_refused_not_crashed(self):
        for spec in ["", "spaceship: a=1", "right_triangle: a=-3; b=4", "function: f=__import__('os')",
                     "projectile: speed=10; angle=95", "vectors: a=1"]:
            self.assertTrue(check_figure(spec), spec)


class AccuracyTests(unittest.TestCase):
    def test_pythagoras_hypotenuse_and_angle_are_computed(self):
        tmp, _, meta = _render("right_triangle: a=3; b=4; angle=yes; formula=yes")
        with tmp:
            texts = _texts(meta)
            self.assertIn("5", texts)
            self.assertIn("53.1°", texts)
            self.assertIn("a² + b² = c²", texts)

    def test_right_angle_is_square_on_screen(self):
        tmp, _, meta = _render("right_triangle: a=5; b=2")
        with tmp:
            base, side = meta["strokes"][0]["points"], meta["strokes"][1]["points"]
            v1 = (base[-1][0] - base[0][0], base[-1][1] - base[0][1])
            v2 = (side[-1][0] - side[0][0], side[-1][1] - side[0][1])
            self.assertAlmostEqual(v1[0] * v2[0] + v1[1] * v2[1], 0.0, delta=1e-6)
            ratio = math.hypot(*v1) / math.hypot(*v2)
            self.assertAlmostEqual(ratio, 5 / 2, places=3)

    def test_vector_sum(self):
        tmp, _, meta = _render("vectors: a=3,1; b=1,2; sum=yes")
        with tmp:
            self.assertIn("(4, 3)", _texts(meta))
            self.assertTrue(any(s["gold"] for s in meta["strokes"]))

    def test_tangent_slope_and_area(self):
        tmp, _, meta = _render("function: f=x^2; x=-2,2; tangent=1", (1536, 1024))
        with tmp:
            self.assertIn("slope = 2", _texts(meta))
        tmp, _, meta = _render("function: f=sin(x); x=0,6.28; area=0,pi", (1536, 1024))
        with tmp:
            self.assertIn("area ≈ 2", _texts(meta))

    def test_unit_circle_keeps_precision(self):
        tmp, _, meta = _render("unit_circle: angle=30; wave=yes", (1536, 1024))
        with tmp:
            self.assertIn("sin 0.5", _texts(meta))
            self.assertIn("cos 0.87", _texts(meta))

    def test_projectile_range_and_peak(self):
        tmp, _, meta = _render("projectile: speed=20; angle=45", (1536, 1024))
        with tmp:
            reach = 20 ** 2 * math.sin(math.radians(90)) / 9.8
            self.assertIn(f"{reach:.1f} m", _texts(meta))
            self.assertIn("peak 10.2 m", _texts(meta))

    def test_beam_reactions_balance(self):
        tmp, _, meta = _render("beam: length=6; load=10; at=2", (1536, 1024))
        with tmp:
            texts = _texts(meta)
            self.assertIn("6.67 kN", texts)
            self.assertIn("3.33 kN", texts)

    def test_net_force(self):
        tmp, _, meta = _render("forces: 20@0; 15@120")
        with tmp:
            rx, ry = 20 + 15 * math.cos(math.radians(120)), 15 * math.sin(math.radians(120))
            self.assertIn(f"net {math.hypot(rx, ry):.0f} N at {math.degrees(math.atan2(ry, rx)):.1f}°", _texts(meta))


class RenderPathTests(unittest.TestCase):
    def test_figure_loads_as_a_pen_drawn_scene_with_labels(self):
        from golide_engine.vector.illustrate import load_figure

        tmp, path, meta = _render("right_triangle: a=3; b=4")
        with tmp:
            drawing = load_figure(path)
            self.assertIsNotNone(drawing)
            self.assertEqual(drawing.entrance, "pen")
            self.assertEqual(len(drawing.labels), len(meta["labels"]))
            self.assertTrue(all(0.0 <= label[3] <= 1.0 for label in drawing.labels))
            # Construction order is kept: the hypotenuse (gold) is drawn last.
            self.assertTrue(drawing.strokes[-1].gold or any(s.gold for s in drawing.strokes[-3:]))

    def test_ordinary_picture_has_no_figure(self):
        from PIL import Image

        from golide_engine.vector.illustrate import load_figure

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scene-01.png"
            Image.new("RGB", (10, 10)).save(path)
            self.assertIsNone(load_figure(path))

    def test_storyboard_offers_the_figure_field(self):
        from golide_engine.vector.illustrate import VISUAL_PLAN_SCHEMA, scene_plan_instructions

        item = VISUAL_PLAN_SCHEMA["properties"]["scenes"]["items"]
        self.assertIn("figure", item["required"])
        text = scene_plan_instructions("long")
        for kind in ("vectors:", "right_triangle:", "function:", "unit_circle:", "projectile:", "beam:", "forces:"):
            self.assertIn(kind, text)

    def test_bad_figure_raises_figure_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FigureError):
                render_figure("function: f=1/0*x; x=1,2", Path(tmp) / "x.png", (512, 512))


if __name__ == "__main__":
    unittest.main()


class PhysicsTests(unittest.TestCase):
    def test_every_kind_in_the_menu_draws(self):
        from golide_engine.vector.figures import EXAMPLES

        for kind, example in EXAMPLES.items():
            spec = example.split("  (")[0].strip()
            self.assertEqual(check_figure(spec), "", kind)

    def test_newton_second_law(self):
        tmp, _, meta = _render("newton: force=10; mass=2; friction=4", (1536, 1024))
        with tmp:
            self.assertIn("a = 6 ÷ 2 = 3 m/s²", _texts(meta))

    def test_motion_graph_distance_and_slopes(self):
        tmp, _, meta = _render("motion: points=0,0 4,20 10,20 12,0", (1536, 1024))
        with tmp:
            texts = _texts(meta)
            self.assertIn("distance = 180 m", texts)
            self.assertIn("a = 5 m/s²", texts)
            self.assertIn("a = -10 m/s²", texts)

    def test_thin_lens_equation(self):
        tmp, _, meta = _render("lens: focal=10; object=25", (1536, 1024))
        with tmp:
            self.assertIn("image 16.67 from the lens", _texts(meta))
            self.assertIn("real, upside down, ×0.67", _texts(meta))
        tmp, _, meta = _render("lens: focal=10; object=6", (1536, 1024))
        with tmp:
            self.assertIn("virtual, upright, ×2.5", _texts(meta))

    def test_snell_and_total_internal_reflection(self):
        tmp, _, meta = _render("refraction: n1=1; n2=1.5; angle=40", (1024, 1024))
        with tmp:
            th2 = math.degrees(math.asin(math.sin(math.radians(40)) / 1.5))
            self.assertIn(f"{th2:.1f}°", _texts(meta))
        tmp, _, meta = _render("refraction: n1=1.5; n2=1; angle=50", (1024, 1024))
        with tmp:
            self.assertIn("total internal reflection", _texts(meta))
            self.assertIn("critical angle 41.8°", _texts(meta))

    def test_prism_uses_true_colours_in_order(self):
        tmp, _, meta = _render("prism: spread=8", (1536, 1024))
        with tmp:
            colours = [tuple(s["rgb"]) for s in meta["strokes"] if s.get("rgb") and s["width"] > 1.5]
            self.assertGreaterEqual(len(colours), 7)

    def test_gas_work_and_carnot(self):
        tmp, _, meta = _render("pv: process=isothermal; p1=200; v1=1; v2=3", (1536, 1024))
        with tmp:
            self.assertIn(f"work = {200 * math.log(3):.1f} J", _texts(meta))
        tmp, _, meta = _render("heat_engine: hot=500; cold=300; heat=1000", (1536, 1024))
        with tmp:
            self.assertIn("max efficiency 40%", _texts(meta))
            self.assertIn("work 400 J", _texts(meta))

    def test_time_dilation(self):
        tmp, _, meta = _render("light_clock: speed=0.8", (1536, 1024))
        with tmp:
            self.assertIn("1 tick takes 1.67× longer", _texts(meta))

    def test_wave_speed(self):
        tmp, _, meta = _render("wave: wavelength=2; amplitude=1; frequency=5", (1536, 1024))
        with tmp:
            self.assertIn("speed = 5 Hz × 2 m = 10 m/s", _texts(meta))

    def test_missing_greek_letters_are_spelled_out(self):
        tmp, _, meta = _render("function: f=x^2; x=-2,2; label=γ curve", (1536, 1024))
        with tmp:
            self.assertTrue(all("γ" not in t for t in _texts(meta)))


class RoadmapKindTests(unittest.TestCase):
    def test_ohms_law_series_and_parallel(self):
        tmp, _, meta = _render("circuit: voltage=12; resistors=4,2", (1536, 1024))
        with tmp:
            self.assertIn("current = 12 V ÷ 6 ohms = 2 A", _texts(meta))
            self.assertIn("8 V", _texts(meta))
        tmp, _, meta = _render("circuit: voltage=12; resistors=4,6,12; layout=parallel", (1536, 1024))
        with tmp:
            self.assertIn("total 6 A (combined 2 ohms)", _texts(meta))

    def test_molecule_angles(self):
        tmp, _, meta = _render("molecule: name=H2O", (1024, 1024))
        with tmp:
            self.assertIn("bond angle 104.5°", _texts(meta))
        self.assertTrue(check_figure("molecule: name=unobtainium"))

    def test_truss_is_symmetric_and_balanced(self):
        tmp, _, meta = _render("truss: span=6; height=2; load=10; panels=4", (1536, 1024))
        with tmp:
            texts = _texts(meta)
            self.assertEqual(texts.count("5 kN"), 2)                 # reactions share a central load
            self.assertEqual(texts.count("3.8 push"), 2)             # symmetric members read the same
            self.assertIn("7.5 push", texts)

    def test_solid_volumes(self):
        cases = {"solid: shape=cylinder; radius=3; height=5": f"volume {math.pi * 45:.2f} cm³",
                 "solid: shape=sphere; radius=2": f"volume {4 / 3 * math.pi * 8:.2f} cm³",
                 "solid: shape=cube; a=3": "volume 27 cm³"}
        for spec, expected in cases.items():
            tmp, _, meta = _render(spec, (1536, 1024))
            with tmp:
                self.assertIn(expected, _texts(meta), spec)
