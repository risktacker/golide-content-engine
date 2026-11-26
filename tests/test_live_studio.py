"""The living studio (owner 2026-11-26): long studio scenes as the 3D room with the live Goli, behind a switch."""
import json
from pathlib import Path

from golide_engine.edit.compose import Composer, live_ready


def _edit(live):
    return {"format": "long", "duration": 4.0, "live_studio": live,
            "captions": [{"start": 0, "end": 4, "words": [{"text": "Look", "at": 0.2}, {"text": "here.", "at": 0.6}], "keys": []}],
            "scenes": [{"type": "host", "start": 0.0, "duration": 4.0, "data": {
                "place": "studio", "cues": [{"start": 0.0, "value": "X"}, {"start": 0.3, "value": "B"}],
                "poses": [{"pose": "talk", "at": 0}, {"pose": "point", "at": 1.5}], "words": [{"text": "Hello"}]}}]}


def test_the_switch_off_keeps_todays_studio(tmp_path):
    page = Composer("long", outfit="royal").build(_edit(False), tmp_path / "c").read_text()
    assert "studio_live.js" not in page and 'window.__timelines["main"]=tl;' in page


def test_the_switch_on_plays_the_3d_room_and_waits_for_it(tmp_path):
    assert live_ready()
    out = tmp_path / "c"
    page = Composer("long", outfit="ember").build(_edit(True), out).read_text()
    assert "mountStudio" in page and "__liveWaits" in page
    assert 'Promise.all(window.__liveWaits||[]).then' in page            # the film waits until the room is loaded
    for f in ("three/g3d/studio_live.js", "three/g3d/goli_live.js", "goli3d/goli.glb", "goli3d/studio.glb"):
        assert (out / f).exists(), f
    plan = json.loads(page.split("plan: ", 1)[1].split("});", 1)[0])
    assert plan["sit"] == [[0, 1]] and plan["moves"] == [{"name": "point_screen", "at": 1.5}]
    assert [w[2] for w in plan["words"]] == ["Look", "here."]
    assert '"glasses": "aviator"' in page.replace("glasses: ", '"glasses": ') or "aviator" in page   # the kit's glasses


def test_a_short_never_uses_the_studio_room(tmp_path):
    e = _edit(True); e["format"] = "short"
    page = Composer("short", outfit="royal").build(e, tmp_path / "c").read_text()
    assert "studio_live.js" not in page


def test_a_short_plays_the_standing_goli_live_under_the_proof(tmp_path):
    e = _edit(True); e["format"] = "short"
    e["scenes"][0]["data"]["place"] = "side"
    page = Composer("short", outfit="royal").build(e, tmp_path / "c").read_text()
    assert 'import { mount } from "./three/g3d/goli_live.js"' in page and "studio_live.js" not in page
    plan = json.loads(page.split("plan: ", 1)[1].split("});", 1)[0])
    assert "sit" not in plan and plan["moves"] == [{"name": "point_up", "at": 1.5}]


def test_a_long_scene_with_a_picture_gets_up_walks_to_the_screen_and_sits_again(tmp_path):
    from PIL import Image
    pic = tmp_path / "page.png"; Image.new("RGB", (64, 36), "white").save(pic)
    e = _edit(True); e["duration"] = 22.0
    sc = e["scenes"][0]; sc["duration"] = 22.0; sc["data"]["screen"] = str(pic); sc["data"].pop("words")
    page = Composer("long", outfit="royal").build(e, tmp_path / "c").read_text()
    plan = json.loads(page.split("plan: ", 1)[1].split("});", 1)[0])
    assert any(k.get("glide") for k in plan["path"]) and [s[1] for s in plan["sit"]] == [1, 0, 1]
    assert {c["shot"] for c in plan["camera"]} >= {"main", "wide", "screen"}
    assert plan["tv"][0][1].endswith("page.png")                    # the picture is on the 3D screen too
    assert any(m["name"] == "point_screen" for m in plan["moves"])
