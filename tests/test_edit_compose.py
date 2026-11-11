import json
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from golide_engine.edit.compose import Composer
from golide_engine.engine.source_capture import phrases


class EditComposeTest(unittest.TestCase):
    def build(self, tmp: Path, dark: bool = False) -> str:
        shot = tmp / "page.png"
        Image.new("RGB", (2160, 1350), (20, 20, 20) if dark else (250, 250, 250)).save(shot)
        edit = {"format": "long", "scenes": [
            {"type": "kinetic_title", "start": 0, "duration": 2, "data": {
                "words": [{"text": "Big", "at": 0}, {"text": "news", "at": 0.3}], "punch": "news"}},
            {"type": "browser_shot", "start": 2, "duration": 3, "in": "whip", "data": {
                "image": shot, "url": "https://example.com", "highlights": [{"rect": [800, 300, 40, 28], "ring": True}]}},
            {"type": "stat_counter", "start": 5, "duration": 2, "data": {"value": 40, "prefix": "$", "label": "x"}},
            {"type": "follow_cta", "start": 7, "duration": 2, "data": {}},
        ]}
        out = tmp / "comp"
        Composer("long").build(edit, out)
        return (out / "index.html").read_text()

    def test_contract(self):
        with TemporaryDirectory() as t:
            page = self.build(Path(t))
            self.assertIn('data-composition-id="main"', page)
            self.assertIn('data-duration="9.000"', page)
            self.assertIn('window.__timelines["main"]=tl', page)
            self.assertEqual(page.count('class="scene clip"'), 4)
            self.assertNotIn("autoAlpha", page)
            self.assertTrue((Path(t) / "comp/fonts/poppins-latin-900-normal.woff").exists())
            self.assertTrue((Path(t) / "comp/gsap.min.js").exists())
            self.assertTrue(list((Path(t) / "comp/media").glob("*page.png")))
            sfx = json.loads((Path(t) / "comp/sfx.json").read_text())
            self.assertIn("whoosh", {c["kind"] for c in sfx})
            # the camera drift never fights the entrance on the same element
            self.assertFalse(re.search(r'fromTo\("#s\d+-\w+ \.stage",\{scale:1\}', page))

    def test_dark_page_gets_underline(self):
        with TemporaryDirectory() as t:
            self.assertIn('class="hl dark"', self.build(Path(t), dark=True))
        with TemporaryDirectory() as t:
            self.assertNotIn('class="hl dark"', self.build(Path(t)))

    def test_claim_phrases_longest_first(self):
        groups = phrases(["Fable 5.2 costs $40 per million output tokens."])
        self.assertEqual(len(groups), 1)
        self.assertGreaterEqual(len(groups[0][0]), len(groups[0][-1]))
        self.assertIn("$40", groups[0])


class MascotTest(unittest.TestCase):
    def test_every_pose_and_mouth_draws(self):
        from golide_engine.edit import mascot

        for pose in mascot.POSES:
            s = mascot.character(pose, uid="t")
            for k in mascot.MOUTHS:
                self.assertIn(f'id="t-m{k}"', s)
            self.assertIn('id="t-lid"', s)
        self.assertTrue(mascot.svg("shock").startswith("<svg"))

    def test_host_scene_lip_syncs(self):
        with TemporaryDirectory() as t:
            edit = {"format": "long", "scenes": [{"type": "host", "start": 0, "duration": 3, "data": {
                "place": "full", "cues": [{"start": 0.1, "value": "C"}, {"start": 0.3, "value": "A"}],
                "poses": [{"pose": "talk", "at": 0}, {"pose": "point", "at": 1.5}]}}]}
            Composer("long").build(edit, Path(t) / "c")
            page = (Path(t) / "c/index.html").read_text()
            self.assertIn('[id$=-mC]",{opacity:1}', page)
            self.assertIn('id="pg-plate"', page)       # shared gradients present once
            self.assertIn("s1-host-p1", page)


if __name__ == "__main__":
    unittest.main()
