"""Owner 2026-11-12 (modelled on Outskill): steps shown in the real product, typed prompts, checklists, one Goli."""
from pathlib import Path

from golide_engine.edit import editor
from golide_engine.edit.compose import Composer
from PIL import Image

from test_edit_editor import _lines


def _page(tmp_path):
    from PIL import ImageDraw
    im = Image.new("RGB", (2160, 1350), "white")  # captures are 1.5x
    d = ImageDraw.Draw(im)
    for x0 in range(0, 2160, 12):                  # text-like marks everywhere, so no shot is an empty patch
        d.rectangle([x0, 0, x0 + 5, 1350], fill="black")
    im.save(tmp_path / "01-top.png")
    return [{"ok": True, "url": "https://platform.claude.com/docs", "title": "Docs", "top": "01-top.png",
             "blocks": [{"text": "Try in playground", "rect": [480, 200, 150, 28]},
                        {"text": "claude-fable-5-2", "rect": [300, 200, 160, 28]},
                        {"text": "Output pricing $40", "rect": [1100, 280, 270, 70]}]}]


def _scene(**kw):
    base = {"first_line": 0, "last_line": 1, "goli_corner": False, "poses": [], "screen_words": None, "punch": None,
            "source": None, "phrase": None, "items": [], "shots": [], "quote": None, "label": None}
    base.update(kw)
    return base


def test_walkthrough_on_the_real_page(tmp_path):
    lines = _lines(["Copy the model name, then open the playground.", "Then check the price before you run it."])
    raw = {"scenes": [_scene(type="walkthrough", source=0, items=["Copy the model name", "Open the playground", "Check the price"],
                             shots=[1, 0, 2], label="Try it today")]}
    edit = editor.build(raw, lines, 8.0, "long", _page(tmp_path), tmp_path, [], [])
    walk = next(s for s in edit["scenes"] if s["type"] == "walkthrough")
    steps = walk["data"]["steps"]
    assert [s["label"] for s in steps] == ["Copy the model name", "Open the playground", "Check the price"]
    assert steps[0]["rect"] == [300, 200, 160, 28]
    ats = [s["at"] for s in steps]
    assert ats == sorted(ats) and all(b - a >= 0.6 for a, b in zip(ats, ats[1:]))
    html = Composer("long").build(edit, tmp_path / "out").read_text()
    assert "Open the playground" in html and "-sp2" in html and "-cur" in html


def test_walkthrough_without_shots_falls_back_to_steps(tmp_path):
    lines = _lines(["Copy the name and open the playground.", "Then run it."])
    raw = {"scenes": [_scene(type="walkthrough", source=0, items=["Copy the name", "Open the playground"], shots=[9])]}
    edit = editor.build(raw, lines, 6.0, "long", _page(tmp_path), tmp_path, [], [])
    assert any(s["type"] == "steps" for s in edit["scenes"])
    assert any("walkthrough" in n for n in edit["notes"])


def test_prompt_and_checklist_render(tmp_path):
    lines = _lines(["Ask it to read your sales sheet.", "You need an account, a task and a budget."])
    raw = {"scenes": [_scene(type="prompt", last_line=0, quote="Read my sales sheet and list three risks", label="Claude"),
                      _scene(type="checklist", first_line=1, last_line=1, items=["An account", "A task", "A budget"])]}
    edit = editor.build(raw, lines, 7.0, "long", [], None, [], [])
    kinds = [s["type"] for s in edit["scenes"]]
    assert "prompt_card" in kinds and "checklist" in kinds
    html = Composer("long").build(edit, tmp_path / "out").read_text()
    assert "Read my sales sheet" not in html.replace("</span><span", "")  # typed letter by letter
    assert "stagger" in html and "strokeDashoffset" in html


def test_one_goli_per_block():
    scenes = [{"type": "host", "start": 0.0, "duration": 5.0, "data": {"place": "side", "poses": [{"pose": "talk", "at": 0}], "cues": []}},
              {"type": "host", "start": 3.0, "duration": 4.0, "data": {"place": "corner", "poses": [{"pose": "shock", "at": 2.5}], "cues": []}},
              {"type": "host", "start": 6.5, "duration": 0.6, "data": {"place": "corner", "poses": [], "cues": []}},
              {"type": "stat_counter", "start": 0.0, "duration": 7.0, "data": {}}]
    out = editor.one_goli(scenes)
    hosts = sorted((s for s in out if s["type"] == "host"), key=lambda s: s["start"])
    assert len(hosts) == 2
    assert hosts[1]["start"] == 5.0 and hosts[1]["data"]["poses"][0]["at"] == 0.5
    for a, b in zip(hosts, hosts[1:]):
        assert a["start"] + a["duration"] <= b["start"] + 1e-6
