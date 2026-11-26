"""2026-11-13 (owner): ideas shown as moving pictures, landing on the spoken word."""
from pathlib import Path
from golide_engine.edit import editor, metaphors
from golide_engine.edit.compose import Composer

from test_edit_editor import _lines


def test_every_metaphor_draws_and_moves():
    for kind, fn in metaphors.DRAW.items():
        svg, tweens, cues = fn("m", 1.2, label="Compute is the real cost", items=["Plan", "Act", "Check"],
                               times=[0.3, 0.6, 0.9], left="Speed", right="Accuracy", winner="right", value=82)
        assert svg.startswith("<") and tweens and cues, kind


def test_editor_places_a_metaphor_on_its_word(tmp_path):
    lines = _lines(["It is a trade between speed and accuracy.", "And accuracy wins every time."])
    raw = {"scenes": [{"type": "metaphor", "metaphor": "scales", "first_line": 0, "last_line": 1, "goli_corner": False,
                       "poses": [], "screen_words": None, "punch": "accuracy", "source": None, "phrase": None,
                       "items": [], "shots": [], "quote": None, "label": None, "left": "Speed", "right": "Accuracy",
                       "value": None},
                      {"type": "metaphor", "metaphor": "scales", "first_line": 1, "last_line": 1, "goli_corner": False,
                       "poses": [], "screen_words": "Accuracy wins", "punch": None, "source": None, "phrase": None,
                       "items": [], "shots": [], "quote": None, "label": None, "left": "A", "right": "B", "value": None}]}
    edit = editor.build(raw, lines, 6.0, "long", [], None, [], [])
    metas = [s for s in edit["scenes"] if s["type"] == "metaphor"]
    assert len(metas) == 1                       # never the same metaphor twice in a video
    assert metas[0]["data"]["winner"] == "right" and metas[0]["data"]["at"] > 0.5
    html = Composer("long").build(edit, tmp_path / "o").read_text()
    assert "metaphor3d.js" in html and "Accuracy" in html      # 3D since 2026-11-26


def _s3d(obj, first, last, punch="opens", label="Your rented GPU"):
    return {"type": "object3d", "object3d": obj, "metaphor": None, "first_line": first, "last_line": last,
            "goli_corner": False, "poses": [], "screen_words": None, "punch": punch, "source": None, "phrase": None,
            "items": [], "shots": [], "quote": None, "label": label, "left": None, "right": None, "value": None}


def test_glass_object_with_its_label_and_limits(tmp_path):
    lines = _lines(["The laptop lid opens and the screen lights up.", "The laptop again.",
                    "In the rack one server slides out.", "Inside the chip the die is tiny."])
    raw = {"scenes": [_s3d("laptop", 0, 0), _s3d("laptop", 1, 1), _s3d("server", 2, 2, "slides"), _s3d("chip", 3, 3, "rise")]}
    edit = editor.build(raw, lines, 8.0, "long", [], None, [], [])
    objs = [s for s in edit["scenes"] if s["type"] == "object3d"]
    # laptops with nothing real for their screens give way; never two objects in a row (the chip follows the server)
    assert [o["data"]["object"] for o in objs] == ["server"]
    assert any("no real picture for its screen" in n for n in edit["notes"])
    assert objs[0]["data"]["lead"] == "Your rented GPU"
    html = Composer("long").build(edit, tmp_path / "o")
    text = html.read_text()
    assert "glass3d.js" in text and "importmap" in text and '"lead": "Your rented GPU"' in text
    assert (html.parent / "three" / "g3d" / "glass3d.js").exists()


def test_a_screen_device_shows_the_real_thing_and_never_the_same_way_twice(tmp_path):
    """Owner 2026-11-25: "11 times is not wrong; what is wrong is the same way, same colour, and the screen empty".
    A laptop shows the real picture of what is said on its screen, as often as that fits; each showing gets its own
    look and view; a laptop with nothing real for its screen is not shown. Other objects need their name said."""
    from PIL import Image, ImageDraw
    for i, colour in enumerate(("#1d4ed8", "#16a34a")):
        im = Image.new("RGB", (1440, 900), "white")
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 1440, 90], fill="#111827")
        d.rectangle([80, 200, 700, 760], fill=colour)
        for y in range(220, 740, 40):
            d.rectangle([760, y, 1360, y + 14], fill="#374151")
        im.save(tmp_path / f"0{i}-top.png")
    sources = [{"ok": True, "url": "https://opencode.ai", "title": "OpenCode terminal agent", "top": "00-top.png",
                "product": "OpenCode"},
               {"ok": True, "url": "https://openrouter.ai", "title": "OpenRouter free models", "top": "01-top.png",
                "product": "OpenRouter"}]
    lines = _lines(["Install OpenCode on your machine.", "Saved into Git.", "Then open OpenRouter for free models.",
                    "Words.", "Plug the battery in."])
    raw = {"scenes": [_s3d("laptop", 0, 0), {"type": "studio", "first_line": 1, "last_line": 1},
                      _s3d("laptop", 2, 2), {"type": "studio", "first_line": 3, "last_line": 3}, _s3d("server", 4, 4)]}
    edit = editor.build(raw, lines, 10.0, "long", sources, tmp_path, [], [])
    objs = [s for s in edit["scenes"] if s["type"] == "object3d"]
    assert [Path(o["data"]["screen"]).name for o in objs] == ["00-top.png", "01-top.png"]
    assert objs[0]["data"]["look"] != objs[1]["data"]["look"] and objs[0]["data"]["view"] != objs[1]["data"]["view"]
    assert objs[0]["data"]["keys"] != objs[1]["data"]["keys"]          # smooth, real keys or neon, in turn
    assert any("do not name it" in n for n in edit["notes"])          # a server on a line about a battery
    html = Composer("long").build(edit, tmp_path / "o").read_text()
    assert '"screen": "' in html and "-scr" in html


def test_counters_carry_the_spoken_units():
    assert editor._stat_units(90.92, "", "", "close to hundred billion dollars") == (90.9, "$", "B")
    assert editor._stat_units(229.0, "", "", "229 tools") == (229.0, "", "")
    assert editor._stat_units(4_800_000, "", "", "views") == (4.8, "", "M")


def test_a_chapter_card_never_holds_past_two_seconds():
    lines = _lines(["Every AI coding tool has two parts.", "The body, the app you type into.", "And the brain doing the thinking."])
    raw = {"scenes": [{"type": "chapter", "label": "Two parts", "first_line": 0, "last_line": 2}]}
    edit = editor.build(raw, lines, 9.0, "long", [], None, [], [])
    card = next(s for s in edit["scenes"] if s["type"] == "chapter_card")
    assert card["duration"] <= 2.0
    studio = [s for s in edit["scenes"] if s["type"] == "host" and s["data"].get("place") == "studio"]
    assert studio and abs(studio[0]["start"] - (card["start"] + card["duration"])) < 0.05


def test_a_chapter_card_leaves_once_its_stage_is_named():
    """Owner 2026-11-25: "once you say 'step 5', the moment you start explaining that stage it has to leave"."""
    lines = _lines(["Step five. Now open the settings page and paste the key you copied."])
    raw = {"scenes": [{"type": "chapter", "label": "Step five", "first_line": 0, "last_line": 0}]}
    edit = editor.build(raw, lines, 6.0, "long", [], None, [], [])
    card = next(s for s in edit["scenes"] if s["type"] == "chapter_card")
    assert 1.0 <= card["duration"] < 1.9
