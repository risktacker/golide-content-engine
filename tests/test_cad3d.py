import json
import math
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from golide_engine.vector import cad3d, motion3d

GEARS = """
from build123d import *
import math


def gear(teeth, module, width):
    r_tip, r_root = module * (teeth + 2) / 2, module * (teeth - 2.5) / 2
    pts = []
    for i in range(teeth):
        for u, r in ((0.0, r_root), (0.22, r_root), (0.36, r_tip), (0.64, r_tip), (0.78, r_root)):
            a = 2 * math.pi * (i + u) / teeth
            pts.append((r * math.cos(a), r * math.sin(a)))
    with BuildPart() as g:
        with BuildSketch(Plane.XZ):
            Polygon(*pts)
            Circle(module * 2.2, mode=Mode.SUBTRACT)
        extrude(amount=width, both=True)
    return g.part


def build():
    with BuildPart() as case:
        Box(0.26, 0.06, 0.02, align=(Align.CENTER, Align.CENTER, Align.MIN))
        fillet(case.edges().filter_by(Axis.Z), 0.006)
    return {"case": case.part.moved(Location((0.05, 0, 0))),
            "drive_gear": gear(36, 0.004, 0.012).moved(Location((0, 0, 0.09))),
            "pinion": gear(14, 0.004, 0.012).moved(Location((0.1, 0, 0.09)))}
"""
OBJECT = {"name": "Gear set", "sources": ["https://example.org"], "code": GEARS, "parts": [
    {"id": "case", "label": "Case", "gold": False, "mover": False, "explode": [0, 0, 0], "color": [40, 42, 48]},
    {"id": "drive_gear", "label": "Drive gear", "gold": True, "mover": True, "explode": [0, 0, 0.05], "color": [170, 174, 180]},
    {"id": "pinion", "label": "Pinion", "gold": False, "mover": True, "explode": [0.03, 0, 0.05], "color": [184, 115, 51]}]}


class FakeText:
    def __init__(self, answers):
        self.answers, self.calls = list(answers), 0

    def generate_json(self, *_, **__):
        self.calls += 1
        return SimpleNamespace(value=json.loads(json.dumps(self.answers.pop(0))))


class Cad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(cad3d, "CACHE", Path(self.tmp.name))
        self.patch.start()
        cad3d.parts.cache_clear()
        motion3d._SPECS.clear()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_only_plain_cad_code_runs(self):
        self.assertEqual(cad3d.unsafe(GEARS), [])
        self.assertTrue(cad3d.unsafe("import os\ndef build():\n    return {}"))
        self.assertTrue(cad3d.unsafe("def build():\n    return open('x')"))

    def test_storyboard_names_are_found_presets_and_part_lists_are_not(self):
        scenes = [{"figure": "3d: object=Gear set; move=explode; on=inside"},
                  {"figure": "3d: object=laptop; on=opens"},
                  {"figure": "3d: object=vault; box 0 0 0 3 3 3"}]
        self.assertEqual(cad3d.named_objects(scenes), ["Gear set"])

    def test_build_error_goes_back_then_object_draws_in_the_house_look(self):
        broken = {**OBJECT, "code": GEARS.replace('"pinion"', '"ghost"')}
        text = FakeText([broken, OBJECT])
        used = cad3d.make("Gear set", "", text)
        self.assertEqual(len(used), 2)
        self.assertTrue(cad3d.available("Gear set"))
        self.assertTrue(motion3d.is_model({"object": "Gear set"}))
        closed, _ = motion3d.render({"object": "Gear set", "move": "explode"}, 0.0, math.radians(-30), 300)
        opened, _ = motion3d.render({"object": "Gear set", "move": "explode"}, 1.0, math.radians(-30), 300)
        self.assertGreater(closed.getbbox()[2], 0)
        self.assertNotEqual(closed.tobytes(), opened.tobytes())
        px = [p for p in closed.convert("RGBA").getdata() if p[3] == 255]
        self.assertTrue(any(r > g + 25 for r, g, b, _ in px))   # the copper pinion shows in its real colour

    def test_live_since_owner_approval_and_failures_never_stop_a_video(self):
        self.assertTrue(cad3d.settings()["enabled"])      # owner approved 2026-11-07
        with mock.patch.object(cad3d, "settings", return_value={"enabled": True, "max_objects_per_video": 4}):
            failed = cad3d.prepare([{"figure": "3d: object=Thing; move=lift"}], "", FakeText([{"parts": []}] * 4),
                                   lambda *_: None)
        self.assertEqual(failed, ["Thing"])


if __name__ == "__main__":
    unittest.main()


class Marks(Cad):
    """Owner 2026-11-07: what the narration names is measured, pointed at, lit or magnified."""

    def test_marks_parse_from_the_storyboard_line(self):
        from golide_engine.vector.figures.core import parse_figure
        from golide_engine.vector.figures.devices import parse_marks

        _, _, items = parse_figure("3d: object=Gear set; on=inside; mark drive gear|measure|2 m|metres; "
                                   "mark pinion|zoom|Pinion|pinion; mark nothing|wave|x")
        marks = parse_marks(items)
        self.assertEqual([m["kind"] for m in marks], ["measure", "zoom"])
        self.assertEqual((marks[0]["text"], marks[0]["on"]), ("2 m", "metres"))

    def test_lit_part_changes_colour_and_parts_report_their_place(self):
        cad3d.make("Gear set", "", FakeText([OBJECT]))
        spec = {"object": "Gear set", "move": "explode"}
        self.assertEqual(motion3d.labels(spec), ["Case", "Drive gear", "Pinion"])
        self.assertEqual(motion3d.part_index(spec, "the pinion"), 2)
        plain, _ = motion3d.render(spec, 0.0, math.radians(-30), 300)
        geo = list(motion3d.GEOMETRY["parts"])
        lit, _ = motion3d.render(spec, 0.0, math.radians(-30), 300, highlight=(1,), tint=(255, 0, 0))
        x0, _, x1, _ = geo[1]["box"]
        self.assertLess(x0, x1)
        self.assertEqual(len(geo[1]["ends"]), 2)
        red = lambda im: sum(1 for r, g, b, a in im.convert("RGBA").getdata() if a == 255 and r > g + 60)
        self.assertGreater(red(lit), red(plain))
