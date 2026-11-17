"""2026-11-17 (owner): people in Goli videos as ReachMora puppet shots, written by the storyboard (no extra call)."""
import json

import pytest

from golide_engine.edit import editor
from golide_engine.stickman import scene
from golide_engine.vector.align import TimedLine, Word

DOC = {"cast": {"ann": {"skin": "brown", "outfit": "hoodie", "color": "#76B900", "hair": "bun"}},
       "shot": {"kind": "wide", "set": "office", "talk": True, "lower_third": {"name": "X"}, "s": [3],
                "chars": [{"id": "ann", "x": 900, "talk": True, "emotion": "happy"}],
                "labels": [{"text": "A"}, {"text": "B"}, {"text": "C"}]}}


def test_a_shot_is_cleaned_to_what_a_beat_may_show():
    cast, shot = scene.shot_from(json.loads(json.dumps(DOC)))
    assert "talk" not in shot and "lower_third" not in shot and "s" not in shot
    assert "talk" not in shot["chars"][0] and len(shot["labels"]) == 2
    with pytest.raises(ValueError):
        scene.shot_from({"cast": {}, "shot": {"kind": "title"}})
    with pytest.raises(ValueError):
        scene.shot_from({"cast": {}, "shot": {"kind": "wide", "chars": [{"id": "ghost"}]}})


def test_a_project_has_the_beats_words_timing_and_one_shot(tmp_path):
    words = [{"text": w, "t": 0.2 + 0.3 * i} for i, w in enumerate("Ten engineers left. Then they started over.".split())]
    scene.prepare(tmp_path, "Ten engineers left. Then they started over.", words, 3.0, DOC)
    story = json.loads((tmp_path / "story.json").read_text())
    assert story["shots"][0]["s"] == [0, 1] and story["cast"]["ann"]["hair"] == "bun"
    timing = json.loads((tmp_path / "timing.json").read_text())
    assert len(timing["sentences"]) == 2 and timing["duration"] == 3.0 and (tmp_path / "voice.wav").exists()


def _lines():
    words = [Word(w, 0.4 * i, 0.4 * i + 0.35) for i, w in enumerate("Most engineers there quit within a year".split())]
    return [TimedLine(0, " ".join(w.text for w in words), "", "", "", "", 0.0, words[-1].end, words)]


def test_the_editor_makes_a_puppet_scene_with_a_metaphor_stand_in():
    s = {k: None for k in editor.SCENE["required"]}
    s.update(type="puppets", first_line=0, last_line=0, goli_corner=False, poses=[], rows=[], items=[], shots=[],
             points=[], brands=[], parts3d=[], puppet=json.dumps(DOC), metaphor="funnel", label="who stays")
    edit = editor.build({"scenes": [s]}, _lines(), 4.0, "long", [], None, [], [])
    sc = next(x for x in edit["scenes"] if x["type"] == "puppet_clip")
    assert sc["data"]["doc"]["cast"]["ann"] and sc["data"]["words"][0]["text"] == "Most"
    assert sc["data"]["fallback"]["kind"] == "funnel"
    off = editor.build({"scenes": [s]}, _lines(), 4.0, "long", [], None, [], [], looks=editor.looks_for({"free": []}))
    assert not any(x["type"] == "puppet_clip" for x in off["scenes"])
