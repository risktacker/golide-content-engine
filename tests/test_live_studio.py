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
    assert plan["sit"] == [[0, 1]] and {"name": "point_screen", "at": 1.5} in plan["moves"]
    assert {"name": "mic", "at": 0.4} in plan["moves"]           # the first studio scene: he pulls the mic in
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


def test_a_robot_or_a_lock_is_a_real_model_in_the_colour_of_the_named_thing(tmp_path):
    # owner 2026-11-26: "the robot is very stupid ... the lock for anything security"; "colour match to a said thing"
    from golide_engine.edit.compose import hero_for, thing_color
    assert hero_for({"object": "robot"}) == "robot" and hero_for({"object": {"name": "Optimus humanoid"}}) == "robot"
    assert hero_for({"object": "lock"}) == "padlock" and hero_for({"object": "x", "label": "security"}) == "shield"
    assert hero_for({"object": "laptop"}) == ""                     # the glass devices stay for the devices
    assert thing_color("Tesla's robot") == "#E31937" and thing_color("a plain line") == "#E8C268"
    e = {"format": "long", "duration": 4.0, "captions": [{"start": 0, "end": 4, "words": [{"text": "Tesla", "at": 0.3}], "keys": []}],
         "scenes": [{"type": "object3d", "start": 0.0, "duration": 4.0, "data": {"object": "robot", "label": "Optimus"}}]}
    out = tmp_path / "c"
    page = Composer("long", outfit="royal").build(e, out).read_text()
    assert "hero3d.js" in page and '"color": "#E31937"' in page and (out / "hero" / "robot.glb").exists()
    assert 'Promise.all(window.__liveWaits||[]).then' in page


def test_metaphors_are_3d_scenes_in_the_named_things_colours(tmp_path):
    # owner 2026-11-26: "rebuild in 3D and make them colour match to a said thing"
    e = {"format": "long", "duration": 4.0, "captions": [{"start": 0, "end": 4, "words": [{"text": "Claude", "at": 0.3}], "keys": []}],
         "scenes": [{"type": "metaphor", "start": 0.0, "duration": 4.0,
                     "data": {"kind": "scales", "left": "Claude", "right": "ChatGPT", "winner": "left", "at": 1.0}}]}
    out = tmp_path / "m"
    page = Composer("long", outfit="royal").build(e, out).read_text()
    assert "metaphor3d.js" in page and '"left": "#D97757"' in page and '"right": "#10A37F"' in page
    assert (out / "three" / "g3d" / "metaphor3d.js").exists() and (out / "hero" / "padlock.glb").exists()
    assert 'Promise.all(window.__liveWaits||[]).then' in page


def test_metaphor_words_are_shown_as_real_logos_icons_or_the_written_prompt(tmp_path):
    # owner 2026-11-26: real logos for apps and models, data looks like a chat, the word "prompt" never on screen
    import json
    from golide_engine.edit.thing_icons import picture
    assert json.loads(picture("Data"))["kind"] == "icon" and "M" in json.loads(picture("Data"))["svg"]
    assert json.loads(picture("Prompt")) == {"kind": "prompt"}
    assert json.loads(picture("ChatGPT"))["kind"] == "icon"            # no look-alike mark for a brand we have no mark for
    e = {"format": "long", "duration": 4.0, "captions": [{"start": 0, "end": 4, "words": [{"text": "prompt", "at": 0.3}], "keys": []}],
         "scenes": [{"type": "metaphor", "start": 0.0, "duration": 4.0,
                     "data": {"kind": "transform", "left": "Prompt", "right": "App", "at": 1.0, "prompt": "Build me a habit tracker"}}]}
    page = Composer("long", outfit="royal").build(e, tmp_path / "p").read_text()
    assert '"kind": "prompt"' in page and "Build me a habit tracker" in page


def test_split_render_covers_every_frame_once_and_stays_off_outside_github(monkeypatch):
    # owner 2026-11-26: a long video is filmed across many machines; each frame exactly once, joined in order
    from golide_engine.edit import remote
    for dur in (6.0, 61.3, 612.47):
        n = remote.parts_for(dur)
        sp = remote.spans(dur, n)
        assert sp[0][0] == 0 and sp[-1][1] == round(dur * 30) and all(a[1] == b[0] for a, b in zip(sp, sp[1:]))
        assert 2 <= n <= remote.MAX_PARTS
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    assert not remote.wanted(600)


def test_mouth_keeps_rhubarb_timing_without_flicker(tmp_path):
    # owner 2026-11-26 ("mamming, the mouth moves almost opposite"): no shape under two frames, shut only in pauses
    import wave, numpy as np
    from golide_engine.edit.render import smooth
    sr = 16000
    x = np.concatenate([np.sin(np.arange(sr) * 0.05) * 0.5, np.zeros(sr // 2), np.sin(np.arange(sr) * 0.05) * 0.5])
    wav = tmp_path / "v.wav"
    with wave.open(str(wav), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((x * 32767).astype("<i2").tobytes())
    cues = [{"start": i * 0.04, "value": "BCDXBC"[i % 6]} for i in range(60)]
    out = smooth(cues, wav)
    gaps = [b["start"] - a["start"] for a, b in zip(out, out[1:])]
    assert min(gaps) >= 0.06
    assert any(c["value"] == "X" and 0.95 <= c["start"] <= 1.1 for c in out)      # the half-second pause shuts it
    assert not any(c["value"] == "X" and 0.1 < c["start"] < 0.9 for c in out)      # never shut while he sounds


def test_studio_storyboard_puts_pages_on_the_big_screen_with_shots_and_acts(tmp_path):
    # owner 2026-11-26 ("classic, the full studio"): a room sentence's page plays on the big screen, cut to its shot
    from types import SimpleNamespace as L
    from PIL import Image
    from golide_engine.edit.editor import stage_room, instructions
    assert "THE STUDIO" in instructions("long", studio=True) and "THE STUDIO" not in instructions("long")
    img = tmp_path / "page.png"; Image.new("RGB", (1440, 2400), "white").save(img)
    lines = [L(start=0.0, end=3.0), L(start=3.0, end=6.0)]
    scenes = [{"type": "browser_shot", "start": 0.0, "duration": 3.0,
               "data": {"image": img, "page_width": 1440, "highlights": [{"rect": [100, 900, 400, 120]}]}},
              {"type": "host", "start": 0.35, "duration": 2.6, "data": {"place": "corner"}},
              {"type": "metaphor", "start": 3.0, "duration": 3.0, "data": {"kind": "scales"}}]
    plan = [{"first_line": 0, "last_line": 0, "stage": "room", "shot": "screen", "goli": "point_screen"},
            {"first_line": 1, "last_line": 1, "stage": "full", "shot": "main", "goli": "none"}]
    out = stage_room(scenes, plan, lines, [], [])
    assert [s["type"] for s in out] == ["host", "metaphor"]
    room = out[0]["data"]
    assert room["place"] == "studio" and room["shot"] == "screen" and room["act"] == "point_screen"
    assert Image.open(room["screen"]).size == (1280, 720)
    from golide_engine.edit.compose import Composer
    c = Composer("long", outfit="royal")
    P = {"camera": [{"at": 0, "shot": "main"}], "moves": [], "props": []}
    c._live_storyboard(P, 10.0, 4.0, {"shot": "close", "act": "lid_close"})
    assert P["camera"][-1] == {"at": 10.0, "shot": "close", "dur": 0.01} and P["props"][-1]["tilt"] == 102


def test_thumbnail_wears_the_videos_kit_and_the_kit_rotates(tmp_path):
    # owner 2026-11-26: "the engine has to do its work": the next kit after the last upload's, the same on the thumbnail
    import json
    from golide_engine.edit.pipeline import outfit_today
    from golide_engine.goli3d import kits
    recs = tmp_path / "records"; recs.mkdir()
    (recs / "a.json").write_text(json.dumps({"recorded_at": "2026-11-25T20:42", "generation_parameters": {"kit": "royal"}}))
    folder = tmp_path / "edit"
    kit = kits.choose(folder, recs)
    assert kit == kits.next_kit("royal") != "royal"
    assert outfit_today(folder) == kit                     # the thumbnail reads the video's own kit
