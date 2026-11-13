"""2026-11-13 (owner, point 5): no tiny text, no near-empty frames: a scene is measured and enlarged."""
import shutil

from golide_engine.edit.compose import SIZES, Composer
from golide_engine.edit.layout import legibility


def test_a_small_sparse_scene_is_enlarged_but_never_into_goli(tmp_path):
    scenes = [{"type": "checklist", "start": 0, "duration": 3, "in": "wipe", "data": {
                  "heading": "Before you switch", "items": ["An account", "A task"], "at": [0.4, 1.0], "goli_zone": True}},
              {"type": "host", "start": 0, "duration": 3, "data": {"place": "side", "cues": [],
                                                                  "poses": [{"pose": "point", "at": 0}]}}]
    edit = {"format": "long", "duration": 3, "scenes": scenes}
    comp = tmp_path / "c"

    def build(e):
        if comp.exists():
            shutil.rmtree(comp)
        Composer("long").build(e, comp)
    notes = legibility(edit, build, comp, SIZES["long"])
    boost = scenes[0]["data"].get("boost")
    assert boost and 1.2 < boost <= 1.6 and notes
    build(edit)
    assert f"scale({0.84 * boost:.3f})" in (comp / "index.html").read_text()
