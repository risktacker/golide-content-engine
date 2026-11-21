import json

from PIL import Image

from golide_engine.goli3d import video


def _fake(tmp_path, monkeypatch):
    for pose, box in (("talk", [100, 50, 300, 400]), ("shock", [60, 20, 340, 400])):
        d = tmp_path / pose
        d.mkdir()
        meta = {"canvas": [400, 440], "bbox": box, "waist": 250, "head": [120, 40, 280, 200],
                "body": {"royal": [0, 0], "ember": [0, 0]},
                "patches": {s: [180, 170] for s in "ABCDEFGHX"} | {"blink": [150, 100]}}
        (d / "meta.json").write_text(json.dumps(meta))
        for f in ["body-royal", "body-ember", "blink"] + [f"mouth-{s}" for s in "ABCDEFGHX"]:
            Image.new("RGBA", (40, 30)).save(d / f"{f}.webp")
    monkeypatch.setattr(video, "SPRITES", tmp_path)
    for fn in (video.meta, video.frame, video._size):
        fn.cache_clear()


import pytest


@pytest.fixture(autouse=True)
def _clear_caches():
    yield
    for fn in (video.meta, video.frame, video._size):
        fn.cache_clear()


def test_layer_has_every_mouth_and_blink_and_one_frame_for_all_poses(tmp_path, monkeypatch):
    _fake(tmp_path, monkeypatch)
    assert video.frame() == (60, 20, 340, 400)                    # union of the poses: no jump on a pose change
    got = []
    html = video.layer("shock", "s1-host-p0", "ember", 760, lambda f: got.append(f) or f.name)
    assert "body-ember.webp" in html
    with pytest.raises(ValueError):                               # no quiet swaps: an unknown pose is an error
        video.layer("moonwalk", "s1-host-p1", "ember", 760, lambda f: f.name)
    for s in "ABCDEFGHX":
        assert f'id="s1-host-p0-m{s}"' in html
    assert 'id="s1-host-p0-lid"' in html
    assert html.count("opacity:1") == 2                           # the body and the resting mouth
    assert round(video.waist(760)) == round((250 - 20) * 760 / 380)
