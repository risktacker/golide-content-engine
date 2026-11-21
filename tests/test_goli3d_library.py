from pathlib import Path

from golide_engine.goli3d import library


def test_old_faces_map_to_3d_reactions():
    assert library.expression("sure") == "smug"
    assert library.expression("shock") == "astonished"
    assert library.expression("nonsense") == "neutral"


def test_path_falls_back_to_nearest_reaction_then_talk(tmp_path, monkeypatch):
    for f in ("talk/neutral.png", "talk/excited.png", "shock/astonished.png"):
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / f).write_bytes(b"png")
    monkeypatch.setattr(library, "LIBRARY", tmp_path)
    assert library.path("shock", "shock") == tmp_path / "shock/astonished.png"
    assert library.path("shock", "scared") == tmp_path / "shock/astonished.png"      # nearest reaction
    assert library.path("wave", "happy") == tmp_path / "talk/excited.png"            # pose not drawn -> talk
    assert library.path("point", "angry") == tmp_path / "talk/neutral.png"
