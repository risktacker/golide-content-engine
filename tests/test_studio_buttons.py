"""Owner 2026-11-25: "these buttons have to correspond with the backend". The Studio side of every control is pressed
in tests/worker/studio_buttons.test.mjs; here the engine side: what it reads from those fields, and the Made with
report it sends back so the card shows what was really used."""
import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("GOLIDE_PAUSED_PLATFORMS", "")

from golide_engine.edit import editor  # noqa: E402
from golide_engine.orchestration.made_with import made_with  # noqa: E402
from golide_engine.orchestration.reels import chosen_platforms  # noqa: E402


class StudioButtonsReachTheEngine(unittest.TestCase):
    def test_the_engine_reads_every_choice_studio_saves(self):
        spec = {"video_style": "goli", "platforms": ["youtube", "instagram"],
                "looks": {"free": ["layers", "puppets"], "paid": {}}}
        self.assertEqual(chosen_platforms(spec), {"youtube", "instagram"})
        looks = editor.looks_for(spec["looks"], "long")
        self.assertEqual(looks, {"free": ["layers", "puppets"], "paid": {}})
        text = editor.instructions("long", looks)
        self.assertIn("puppets may be used", text)
        self.assertNotIn("circuit", text.split("How to fill them")[0])

    def test_made_with_reports_what_the_video_really_used(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            (work / "edit").mkdir()
            (work / "edit" / "edit-list.json").write_text(json.dumps({"scenes": [
                {"type": "browser_shot", "data": {}}, {"type": "photo", "data": {}},
                {"type": "recipe_clip", "data": {"recipe": "layers"}}, {"type": "host", "data": {}}],
                "plan_misses": [{"named": "x"}]}))
            (work / "edit" / "kit.json").write_text(json.dumps({"kit": "ember"}))
            (work / "edit" / "doctor.json").write_text(json.dumps({"rounds": [
                {"found": [{"kind": "empty"}, {"kind": "repeat"}]}, {"found": []}]}))
            got = made_with({"video_style": "goli", "looks": {"free": ["layers"]}}, work, {"youtube"})
        self.assertEqual(got["style"], "goli")
        self.assertEqual(got["blocks"], {"pages": 1, "photos": 1, "styles": 1})
        self.assertEqual(got["recipes"], {"layers": 1})
        self.assertEqual(got["platforms"], ["youtube"])
        self.assertEqual(got["kit"], "ember")
        self.assertEqual(got["doctor_fixed"], {"empty": 1, "repeat": 1})
        self.assertEqual(got["plan_misses"], 1)


if __name__ == "__main__":
    unittest.main()


def test_the_living_studio_tick_switches_the_3d_room_on_for_that_video_only(monkeypatch):
    # owner 2026-11-26: the TRIAL tick next to the styles in Studio
    from golide_engine.edit.pipeline import live_switch
    monkeypatch.delenv("GOLIDE_LIVE_STUDIO", raising=False)
    assert live_switch({"looks": {"free": ["layers"], "paid": {}, "live": True}}, {"live_studio": False})
    assert not live_switch({"looks": {"free": ["layers"], "paid": {}}}, {"live_studio": False})
    assert live_switch({}, {"live_studio": True})
