from pathlib import Path

from golide_engine.goli3d import library


def test_old_faces_map_to_3d_reactions():
    assert library.expression("sure") == "smug"
    assert library.expression("shock") == "astonished"
    assert library.expression("nonsense") == "neutral"


def test_path_is_exact_or_an_error(tmp_path, monkeypatch):
    import pytest
    (tmp_path / "shock").mkdir()
    (tmp_path / "shock/astonished.png").write_bytes(b"png")
    monkeypatch.setattr(library, "LIBRARY", tmp_path)
    assert library.path("shock", "shock") == tmp_path / "shock/astonished.png"     # old face names still map
    with pytest.raises(FileNotFoundError):
        library.path("shock", "scared")                                            # no stand-in reaction
    with pytest.raises(ValueError):
        library.path("moonwalk", "happy")


def test_thumbnail_reaction_fits_the_title():
    from golide_engine.vector.thumb_engine import reaction_for
    assert reaction_for("The Hidden Cost of China's Polished EVs", "China's Cheap EVs") == ("smug", "point_left")
    assert reaction_for("This Free AI Tool Beats ChatGPT")[0] == "excited"
    assert reaction_for("Why Nvidia Is Worth $5 Trillion")[0] == "astonished"
    assert reaction_for("Plain words") == ("", "")


def test_every_pose_with_every_reaction_is_drawn():
    """Owner 2026-11-21: no stand-ins, so the whole library must be there."""
    assert library.missing_files() == []


def test_render_plan_lists_every_job():
    import subprocess
    import sys
    run = lambda *a: subprocess.run([sys.executable, "tools/goli3d_plan.py", *a], capture_output=True, text=True, check=True).stdout.split()  # noqa: E731
    assert run("library") == list(library.POSES)
    from golide_engine.goli3d import video
    assert sorted(run("video")) == sorted(video.POSES)
    assert run("studio") == ["short", "long", "lower"]
