"""2026-11-17 (owner): Goli beside a Stickman video as the explainer (stickman/goli_layer.py)."""
import json

from golide_engine.edit.compose import Composer
from golide_engine.stickman import goli_layer, longform


def test_poses_hold_long_enough_never_repeat_and_return_to_talk():
    poses = goli_layer._settle([(1.0, "point"), (1.5, "shock"), (5.0, "point"), (5.1, "point"), (14.0, "think")], 20.0)
    assert poses[0] == {"pose": "talk", "at": 0.0}
    times = [p["at"] for p in poses]
    assert times == sorted(times) and all(b - a >= goli_layer.HOLD - 1e-9 for a, b in zip(times, times[1:]))
    assert all(a["pose"] != b["pose"] for a, b in zip(poses, poses[1:]))
    assert {"point", "think", "talk"} <= {p["pose"] for p in poses}


def _words(text, gap=0.4):
    return [{"word": w, "start": 0.2 + i * gap, "end": 0.2 + i * gap + 0.3} for i, w in enumerate(text.split())]


def test_reactions_follow_the_story_events_on_the_output_clock(tmp_path):
    script = "It started small. Then it hit five trillion dollars. Nobody saw it coming. That was the point.\n"
    doc = longform.timing(script, _words(script), 8.0)
    (tmp_path / "timing.json").write_text(json.dumps(doc))
    (tmp_path / "story.json").write_text(json.dumps({"shots": [
        {"kind": "wide", "s": [0]},
        {"kind": "counter", "s": [1], "value": {"from": 0, "to": 5, "at": "five"}},
        {"kind": "closeup", "s": [2], "emotion": "shocked"},
        {"kind": "wide", "s": [3], "polaroid": {"at": "point", "caption": "X"}}]}))
    poses = goli_layer.reactions_long(tmp_path, 9.0)
    by = {p["pose"]: p["at"] for p in poses}
    assert "point" in by and abs(by["point"] - doc["sentences"][1]["words"][3]["t"]) < 0.05   # on "five"
    assert "point_both_up" in by or "shock" in by


def test_the_panel_and_goli_are_built_into_one_composition(tmp_path):
    video = tmp_path / "stick.mp4"
    video.write_bytes(b"0")
    edit = goli_layer.edit_list("long", video, 6.0, [{"pose": "talk", "at": 0}, {"pose": "point", "at": 2.5}], [], "royal")
    Composer("long", outfit="royal").build(edit, tmp_path / "comp")
    html = (tmp_path / "comp" / "index.html").read_text(encoding="utf-8")
    assert '<video id="s1-stage' in html or "stage" in html and "<video" in html
    assert 'muted' in html and "s2-host" in html or "host" in html
