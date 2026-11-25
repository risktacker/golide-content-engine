import json

from PIL import Image

from golide_engine.edit import studio


def test_3d_plates_replace_the_flat_set_and_keep_the_live_parts(tmp_path, monkeypatch):
    for fmt in ("short", "lower"):
        d = tmp_path / fmt
        d.mkdir()
        Image.new("RGBA", (40, 30)).save(d / "back.webp")
        Image.new("RGBA", (20, 10)).save(d / "front.webp")
        (d / "meta.json").write_text(json.dumps({"mug_top": [300, 1500], "edge": [0, 1600, 1080, 1600],
                                                 "back_at": [0, 1250 if fmt == "lower" else 0], "front_at": [5, 1400]}))
    monkeypatch.setattr(studio, "PLATES", tmp_path)
    used = []
    asset = lambda p: used.append(p.name) or p.name  # noqa: E731
    back = studio.back("s1", "short", asset)
    front = studio.front("s1", "short", asset)
    assert "back.webp" in back and 'id="s1-line"' not in back and 'id="s1-bar6"' not in back and 'LIVE' in back   # owner 2026-11-25: no chart on the TV
    assert "front.webp" in front and 'id="s1-steam"' in front and 'id="s1-edge"' in front
    assert "back.webp" in studio.lower_back("s2", asset)
    assert "front.webp" in used and "back.webp" in used
    assert "st-slat" not in back                                  # no flat SVG wall when the 3D set is there


def test_missing_plates_stop_the_run_instead_of_a_fallback(tmp_path, monkeypatch):
    import pytest
    monkeypatch.setattr(studio, "PLATES", tmp_path)
    with pytest.raises(FileNotFoundError):
        studio.back("s1", "short", lambda p: p.name)


def test_every_3d_picture_the_videos_need_is_in_the_repo():
    """Owner 2026-11-21: no fallbacks, so every picture must be there before anything renders."""
    from golide_engine.edit.editor import INTRO_POSES, OUTRO_POSES, POSES
    from golide_engine.goli3d import video
    for fn in (video.meta, video.frame, video._size):
        fn.cache_clear()
    assert video.missing_files() == []
    asked = set(POSES) | {p for v in (*INTRO_POSES.values(), *OUTRO_POSES.values()) for p, _ in v} | {"point_both_up"}
    assert asked <= set(video.POSES)
    for fmt in ("short", "long", "lower"):
        m = studio.need(fmt)
        assert {"mug_top", "edge", "back_at", "front_at"} <= set(m)
