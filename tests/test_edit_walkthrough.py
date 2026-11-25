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
    d.rectangle([0, 0, 2160, 120], fill="#101828")   # a page header and a picture: a real page, not a texture
    d.rectangle([1500, 600, 2100, 1200], fill="#2563eb")
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


def test_walkthrough_without_shots_shows_its_page(tmp_path):
    lines = _lines(["Copy the name and open the playground.", "Then run it."])
    raw = {"scenes": [_scene(type="walkthrough", source=0, items=["Copy the name", "Open the playground"], shots=[9])]}
    edit = editor.build(raw, lines, 6.0, "long", _page(tmp_path), tmp_path, [], [])
    kinds = [s["type"] for s in edit["scenes"]]
    assert "kinetic_title" not in kinds      # 2026-11-18 (owner): other scenes, never text
    # 2026-11-25 (owner: "steps to be shown without skipping, on screenshots"): the steps stay, on the real page:
    # each step found on the page by its own words, else numbered steps beside the page; never plain text steps
    walk = [s for s in edit["scenes"] if s["type"] in ("walkthrough", "steps")]
    assert walk and all(s["type"] == "walkthrough" or s["data"].get("image") for s in walk)


def test_prompt_and_checklist_render(tmp_path):
    lines = _lines(["Ask it to read your sales sheet.", "You need an account, a task and a budget."])
    raw = {"scenes": [_scene(type="prompt", last_line=0, quote="Read my sales sheet and list three risks", label="Claude"),
                      _scene(type="checklist", first_line=1, last_line=1, items=["An account", "A task", "A budget"])]}
    edit = editor.build(raw, lines, 7.0, "long", [], None, [], [])
    kinds = [s["type"] for s in edit["scenes"]]
    assert "prompt_card" in kinds and "checklist" not in kinds     # 2026-11-18: no text cards; a prompt stays
    html = Composer("long").build(edit, tmp_path / "out").read_text()
    assert "Read my sales sheet" not in html.replace("</span><span", "")  # typed letter by letter
    # (the checklist's ticks are gone with the checklist: 2026-11-18, no text cards)


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


def test_one_page_at_most_twice_in_a_row():
    lines = _lines(["One two three four five six.", "Seven eight nine ten eleven twelve.", "More words here now please."])
    shot = lambda a, r: {"type": "browser_shot", "start": a, "duration": 2.0, "data": {
        "url": "https://x.example", "highlights": [{"rect": r}]}}
    notes = []
    out = editor._no_repeats([shot(0, [1, 1, 1, 1]), shot(2, [2, 2, 2, 2]), shot(4, [3, 3, 3, 3]), shot(6, [4, 4, 4, 4])],
                             lines, "long", notes)
    kinds = [s["type"] for s in out]
    assert kinds[:2] == ["browser_shot", "browser_shot"] and kinds[2] == "kinetic_title"


def test_goli_points_at_the_content():
    from golide_engine.edit.compose import Composer
    import tempfile, pathlib
    edit = {"format": "long", "duration": 4.0, "scenes": [
        {"type": "host", "start": 0, "duration": 4.0, "data": {"place": "side", "cues": [], "poses": [
            {"pose": "point_left", "at": 0}]}}]}
    html = Composer("long").build(edit, pathlib.Path(tempfile.mkdtemp()) / "o").read_text()
    assert "scaleX(-1)" in html          # on the right he faces left, toward the content


def test_steps_find_their_own_spots_and_stand_beside_the_real_page(tmp_path):
    """Owner 2026-11-25: steps on real screens. With no shots picked, each step's spot is found by its words; when a
    step has no spot, the numbered steps stand beside the real page, lit one by one, the done ones ticked."""
    page = _page(tmp_path)
    lines = _lines(["Open the playground, then check the pricing.", "That is all."])
    raw = {"scenes": [_scene(type="walkthrough", source=None, items=["Try the playground", "Check output pricing"])]}
    page[0]["title"] = "Claude playground pricing docs"
    edit = editor.build(raw, lines, 6.0, "long", page, tmp_path, [], [])
    walk = next(s for s in edit["scenes"] if s["type"] == "walkthrough")
    assert [st["rect"] for st in walk["data"]["steps"]] == [[480, 200, 150, 28], [1100, 280, 270, 70]]
    raw = {"scenes": [_scene(type="walkthrough", source=0, items=["Sign in first", "Make a new key"])]}
    edit = editor.build(raw, lines, 6.0, "long", page, tmp_path, [], [])
    st = next(s for s in edit["scenes"] if s["type"] == "steps")
    assert st["data"]["image"].name == "01-top.png"
    html = Composer("long").build(edit, tmp_path / "out").read_text()
    assert "Make a new key" in html and "-k0" in html and "platform.claude.com" in html
