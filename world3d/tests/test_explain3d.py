import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

from world3d.explain3d import blueprint, catalog, director, stage
from world3d.explain3d.clips import ClipTrack

GEAR = {"name": "Two gears", "sources": ["https://example.org/gears"], "simplified": [], "parts": [
    {"id": "big", "label": "Drive gear", "builder": "gear", "material": "steel",
     "params": [{"name": "diameter", "value": 0.2}, {"name": "teeth", "value": 24}],
     "at": [0, 0, 0], "explode": [0, 0, 0.1], "anchor": [0, 0, 0.1]},
    {"id": "shaft", "label": "Shaft", "builder": "barrel", "material": "steel",
     "params": [{"name": "length", "value": 0.3}, {"name": "diameter", "value": 0.03}],
     "at": [-0.1, 0, 0], "explode": [-0.1, 0, 0], "anchor": [0.1, 0, 0.02]},
]}
WORDS = [{"word": w, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, w in enumerate(
    "inside the gearbox the drive gear turns the shaft and that shaft spins the wheels every time".split())]
TIMES = [(0.0, 4.0), (4.0, 8.0)]
SHOT = {"first_line": 0, "last_line": 1, "subject": "Two gears", "world": "studio", "move": "orbit_slow", "beats": [
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
    def test_saved_hubble_is_valid(self):
        bp = json.loads((catalog.WORLD3D / "blueprints" / "hubble-space-telescope.json").read_text())
        self.assertEqual(blueprint.problems(bp), [])

    def test_problems_are_named(self):
        bad = json.loads(json.dumps(GEAR))
        bad["parts"][0]["builder"] = "wing"
        bad["parts"][1]["params"] = []
        found = " ".join(blueprint.problems(bad))
        self.assertIn("unknown builder", found)
        self.assertIn("needs length", found)

    def test_retries_with_the_problems_then_saves_once(self):
        bad = {**GEAR, "sources": []}
        text = FakeText([bad, GEAR])
        with tempfile.TemporaryDirectory() as tmp:
            path, used = blueprint.obtain("Two gears", "", text, Path(tmp))
            self.assertEqual(len(used), 2)
            self.assertEqual(json.loads(path.read_text())["parts"][0]["params"]["teeth"], 24)
            _, again = blueprint.obtain("Two gears", "", text, Path(tmp))
            self.assertEqual(again, [])
            self.assertEqual(text.calls, 2)


class Director(unittest.TestCase):
    def test_motion_lands_on_the_spoken_word(self):
        bp = {"parts": blueprint.clean(GEAR)["parts"]}
        shot = director.compile_shot(SHOT, bp, "two-gears", "/tmp", 0.0, 8.0, WORDS)
        explode = next(a for a in shot["actions"] if a["type"] == "explode")
        glow = next(a for a in shot["actions"] if a["type"] == "glow")
        self.assertEqual(explode["start"], 0.0)
        self.assertEqual(glow["part"], "big")
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


def shell_part(**over):
    part = {"id": "body", "label": "Body", "builder": "shell", "material": "paint_red",
            "params": [{"name": "length", "value": 4.4}, {"name": "width", "value": 1.9}, {"name": "height", "value": 1.0}],
            "profile": {"top": [[0, .5], [1.5, .8], [2.6, .9], [4.4, .6]], "bottom": [[0, .2], [4.4, .2]],
                        "width": [[0, 1.6], [2.2, 1.9], [4.4, 1.6]]},
            "at": [0, 0, 0], "turn": [0, 0, 0], "explode": [0, 0, 1], "anchor": [2, 0, .8]}
    part.update(over)
    return {"name": "Any car", "sources": ["https://example.org"], "simplified": [], "parts": [part]}


class Shapes(unittest.TestCase):
    def test_curved_body_from_outlines_passes(self):
        self.assertEqual(blueprint.problems(shell_part()), [])

    def test_body_without_outlines_is_sent_back(self):
        found = " ".join(blueprint.problems(shell_part(profile={"top": [], "bottom": [], "width": []})))
        self.assertIn("top points", found)

    def test_outline_outside_the_body_is_sent_back(self):
        bad = shell_part(profile={"top": [[0, .5], [9, .8]], "bottom": [], "width": [[0, 1], [4.4, 1]]})
        self.assertIn("between 0 and length", " ".join(blueprint.problems(bad)))

    def test_empty_profile_is_dropped_for_plain_parts(self):
        cleaned = blueprint.clean({**GEAR, "parts": [{**GEAR["parts"][0], "profile": {"top": [], "bottom": [], "width": []}}]})
        self.assertNotIn("profile", cleaned["parts"][0])

    def test_writer_is_told_to_use_real_outlines(self):
        self.assertIn("Never build a curved", blueprint.instructions())


class Directing(unittest.TestCase):
    def test_signal_only_leaves_things_that_send(self):
        bp = {"parts": blueprint.clean(GEAR)["parts"]}
        plan = {**SHOT, "beats": [{"action": "signal", "part_hint": "drive gear", "label": "", "cue_word": "drive"}]}
        self.assertEqual(director.compile_shot(plan, bp, "g", "/tmp", 0, 8, WORDS)["effects"], [])

    def test_objects_on_a_floor_turn_and_never_roll(self):
        bp = {"parts": blueprint.clean(GEAR)["parts"]}
        shot = director.compile_shot(SHOT, bp, "g", "/tmp", 0, 8, WORDS)
        self.assertEqual(shot["actions"][0]["axis"], "z")
        self.assertEqual(shot["object"]["rotate"][:2], [0, 0])

    def test_no_subject_back_to_back_or_more_than_twice(self):
        times = [(i * 6.0, i * 6.0 + 6.0) for i in range(6)]
        plans = [{**SHOT, "first_line": i, "last_line": i, "subject": s}
                 for i, s in enumerate(["Car", "Car", "Plane", "Car", "Plane", "Car"])]
        kept = [k["subject"] for k in director.accepted(plans, times, 6, 60)]
        self.assertEqual(kept, ["Car", "Plane", "Car", "Plane"])


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
