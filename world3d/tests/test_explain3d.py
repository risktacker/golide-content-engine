import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

from world3d.explain3d import blueprint, catalog, director, stage
from world3d.explain3d.clips import ClipTrack
from world3d.tests.fixtures_cad import GEARBOX

GEAR = GEARBOX
WORDS = [{"word": w, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, w in enumerate(
    "inside the gearbox the drive gear turns the shaft and that shaft spins the wheels every time".split())]
TIMES = [(0.0, 4.0), (4.0, 8.0)]
SHOT = {"first_line": 0, "last_line": 1, "subject": "Two gears", "focus": "", "world": "studio", "move": "orbit_slow", "beats": [
    {"action": "explode", "part_hint": "", "label": "", "cue_word": "inside"},
    {"action": "glow", "part_hint": "drive gear", "label": "Drive gear", "cue_word": "drive"},
    {"action": "label", "part_hint": "shaft", "label": "Shaft", "cue_word": "shaft"},
]}


class FakeText:
    def __init__(self, answers):
        self.answers, self.calls = list(answers), 0

    def generate_json(self, *_, **__):
        self.calls += 1
        return SimpleNamespace(value=self.answers.pop(0))


class Blueprints(unittest.TestCase):
    def test_problems_are_named(self):
        bad = json.loads(json.dumps(GEAR))
        bad["parts"][0]["material"] = "unobtainium"
        bad["code"] = "import os\n" + bad["code"]
        found = " ".join(blueprint.problems(bad))
        self.assertIn("unknown material", found)
        self.assertIn("import os is not allowed", found)

    def test_code_must_be_plain_cad(self):
        self.assertTrue(blueprint.cad.unsafe("def build():\n    return open('x')"))
        self.assertTrue(blueprint.cad.unsafe("x = 1"))
        self.assertEqual(blueprint.cad.unsafe(GEAR["code"]), [])

    def test_build_errors_go_back_then_saves_once(self):
        broken = {**GEAR, "code": GEAR["code"].replace("return {", "return {'ghost': None, ")}
        text = FakeText([broken, json.loads(json.dumps(GEAR))])
        with tempfile.TemporaryDirectory() as tmp:
            path, used = blueprint.obtain("Two gears", "", text, Path(tmp))
            self.assertEqual(len(used), 2)
            saved = json.loads(path.read_text())
            self.assertTrue(all((path.parent / p["mesh"]).exists() for p in saved["parts"]))
            _, again = blueprint.obtain("Two gears", "", text, Path(tmp))
            self.assertEqual(again, [])

    def test_writer_is_told_to_use_real_cad(self):
        self.assertIn("never stacks of boxes", blueprint.instructions())


class Director(unittest.TestCase):
    def test_motion_lands_on_the_spoken_word(self):
        bp = {"parts": GEAR["parts"]}
        shot = director.compile_shot(SHOT, bp, "two-gears", "/tmp", 0.0, 8.0, WORDS)
        explode = next(a for a in shot["actions"] if a["type"] == "explode")
        glow = next(a for a in shot["actions"] if a["type"] == "glow")
        self.assertEqual(explode["start"], 0.0)
        self.assertEqual(glow["part"], "drive_gear")
        self.assertEqual(glow["start"], 2.0)
        self.assertEqual({lb["text"] for lb in shot["labels"]}, {"Drive gear", "Shaft"})
        self.assertTrue(shot["camera"]["fit_exploded"])

    def test_bad_shots_are_dropped_and_budget_holds(self):
        plans = [{**SHOT}, {**SHOT, "first_line": 1, "last_line": 9}, {**SHOT, "world": "moon"}]
        kept = director.accepted(plans, TIMES, 1, 20)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["blueprint_name"], "two-gears")

    def test_every_catalog_move_is_defined(self):
        self.assertEqual(set(catalog.load()["moves"]), set(director.MOVES))


class WholePath(unittest.TestCase):
    def run_path(self, render):
        text = FakeText([{"shots": [SHOT]}, GEAR])
        with tempfile.TemporaryDirectory() as tmp:
            return stage.run(Path(tmp), "long", ["inside the gearbox", "that shaft spins"], TIMES, WORDS, "facts",
                             text, lambda *_: None, render=render)

    def test_script_reaches_a_clip_without_hand_written_shots(self):
        seen = []
        clips = self.run_path(lambda path, folder, quality: seen.append(json.loads(Path(path).read_text())))
        self.assertEqual(len(clips), 1)
        self.assertEqual(seen[0]["object"]["blueprint"], "two-gears")

    def test_a_failed_render_never_stops_the_video(self):
        def broken(*_):
            raise RuntimeError("renderer down")
        self.assertEqual(self.run_path(broken), [])


class Directing(unittest.TestCase):
    def test_signal_only_leaves_things_that_send(self):
        bp = {"parts": GEAR["parts"]}
        plan = {**SHOT, "beats": [{"action": "signal", "part_hint": "drive gear", "label": "", "cue_word": "drive"}]}
        self.assertEqual(director.compile_shot(plan, bp, "g", "/tmp", 0, 8, WORDS)["effects"], [])

    def test_objects_on_a_floor_turn_and_never_roll(self):
        bp = {"parts": GEAR["parts"]}
        shot = director.compile_shot(SHOT, bp, "g", "/tmp", 0, 8, WORDS)
        self.assertEqual(shot["actions"][0]["axis"], "z")
        self.assertEqual(shot["object"]["rotate"][:2], [0, 0])

    def test_one_object_many_shots_but_never_the_same_view_twice(self):
        times = [(i * 6.0, i * 6.0 + 6.0) for i in range(5)]
        views = [("Car", ""), ("Car", "battery"), ("Car", "battery"), ("Car", "motor"), ("Car", "")]
        plans = [{**SHOT, "first_line": i, "last_line": i, "subject": s, "focus": f} for i, (s, f) in enumerate(views)]
        kept = [(k["subject"], k["focus"]) for k in director.accepted(plans, times, 5, 60)]
        self.assertEqual(kept, [("Car", ""), ("Car", "battery"), ("Car", "motor")])

    def test_focus_part_is_framed_and_lit(self):
        bp = {"parts": GEAR["parts"]}
        shot = director.compile_shot({**SHOT, "beats": [], "focus": "shaft"}, bp, "g", "/tmp", 0, 8, WORDS)
        self.assertEqual(shot["camera"]["focus"], "shaft")
        self.assertTrue(any(a["type"] == "glow" and a["part"] == "shaft" for a in shot["actions"]))


class Composer(unittest.TestCase):
    def test_clip_fades_in_and_is_absent_between_shots(self):
        with tempfile.TemporaryDirectory() as tmp:
            Image.new("RGB", (32, 18), (200, 10, 10)).save(Path(tmp) / "f00000.png")
            track = ClipTrack([{"start": 1.0, "end": 3.0, "frames": tmp, "fps": 24}])
            self.assertIsNone(track.at(0.5, (64, 36)))
            picture, alpha = track.at(1.1, (64, 36))
            self.assertEqual(picture.shape, (36, 64, 3))
            self.assertLess(alpha, 1)
            self.assertEqual(track.at(2.0, (64, 36))[1], 1)
            self.assertTrue(np.isclose(picture[0, 0, 0], 200, atol=2))


if __name__ == "__main__":
    unittest.main()
