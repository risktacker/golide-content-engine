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
