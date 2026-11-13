"""2026-11-13 (owner, point 6): a scene comes in the way it relates to the one before it."""
from types import SimpleNamespace

from golide_engine.edit import editor


def _sc(scene_type, start, **data):
    return {"type": scene_type, "start": start, "duration": 2.0, "in": "rise", "data": data}


def test_transition_follows_meaning():
    lines = [SimpleNamespace(text="So what does it cost?", start=0, end=3.9),
             SimpleNamespace(text="Here is the answer.", start=4, end=5.9),
             SimpleNamespace(text="But that is not the whole story.", start=10, end=11.9)]
    scenes = [_sc("browser_shot", 0, url="a"), _sc("browser_shot", 2, url="a"), _sc("metaphor", 4, kind="funnel"),
              _sc("terminal", 6), _sc("stat_counter", 8), _sc("kinetic_title", 10), _sc("chapter_card", 12),
              {"type": "host", "start": 0, "duration": 14, "data": {}}]
    editor._transitions(scenes, lines)
    got = [s["in"] for s in scenes if s["type"] != "host"]
    # 2026-11-13 (owner: smooth): a strong one at most once in three cuts, so the zoom and the flash flow instead
    assert got[:3] == ["rise", "match", "iris"] and got[-1] == "wipe"
    assert "whip" in got and "zoom" not in got[3:4]
    strong = [g in editor.STRONG for g in got]
    assert all(sum(strong[i:i + 3]) <= 1 for i in range(len(strong)))


def test_never_three_alike_in_a_row():
    scenes = [_sc("kinetic_title", i * 2) for i in range(6)]
    editor._transitions(scenes, [])
    got = [s["in"] for s in scenes[1:]]
    assert all(not (a == b == c) for a, b, c in zip(got, got[1:], got[2:]))
