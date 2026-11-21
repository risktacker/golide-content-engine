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
    assert "back.webp" in back and 'id="s1-line"' in back and 'id="s1-bar6"' in back   # the TV's chart stays live
    assert "front.webp" in front and 'id="s1-steam"' in front and 'id="s1-edge"' in front
    assert "back.webp" in studio.lower_back("s2", asset)
    assert "front.webp" in used and "back.webp" in used
    assert "st-slat" not in back                                  # no flat SVG wall when the 3D set is there


def test_flat_set_stays_when_no_plates(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, "PLATES", tmp_path)
    assert "st-slat" in studio.back("s1", "short", lambda p: p.name)
