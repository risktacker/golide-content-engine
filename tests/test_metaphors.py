"""2026-11-13 (owner): ideas shown as moving pictures, landing on the spoken word."""
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
    assert "svgOrigin" in html and "Accuracy" in html


def _s3d(obj, first, last, punch="opens", label="Your rented GPU"):
    return {"type": "object3d", "object3d": obj, "metaphor": None, "first_line": first, "last_line": last,
            "goli_corner": False, "poses": [], "screen_words": None, "punch": punch, "source": None, "phrase": None,
            "items": [], "shots": [], "quote": None, "label": label, "left": None, "right": None, "value": None}


def test_glass_object_with_its_label_and_limits(tmp_path):
    lines = _lines(["The lid opens and the screen lights up.", "In the rack one server slides out.",
                    "Inside the chip the die is tiny.", "And the battery cells rise out."])
    raw = {"scenes": [_s3d("laptop", 0, 0), _s3d("laptop", 1, 1), _s3d("server", 2, 2, "slides"), _s3d("chip", 3, 3, "rise")]}
    edit = editor.build(raw, lines, 8.0, "long", [], None, [], [])
    objs = [s for s in edit["scenes"] if s["type"] == "object3d"]
    assert len(objs) == 2                                  # at most 2 in a long video, never two in a row
    assert objs[0]["data"]["lead"] == "Your rented GPU"
    html = Composer("long").build(edit, tmp_path / "o")
    text = html.read_text()
    assert "glass3d.js" in text and "importmap" in text and '"lead": "Your rented GPU"' in text
    assert (html.parent / "three" / "g3d" / "glass3d.js").exists()
