"""Simple 3D (owner direction 2026-11-05): any real device, its move on the spoken word."""
from types import SimpleNamespace

from golide_engine.vector import motion3d
from golide_engine.vector.figures import check_figure


def test_every_object_draws_and_a_car_does_not():
    for name in motion3d.OBJECTS:
        assert check_figure(f"3d: object={name}; on=opens") == ""
    assert "object must be one of" in check_figure("3d: object=car")


def test_the_move_lands_on_the_spoken_word():
    lines = [SimpleNamespace(text="Picture a laptop on your desk.", start=0.0, end=2.0),
             SimpleNamespace(text="You lift the lid and it opens.", start=2.0, end=4.0)]
    at = motion3d.trigger_time(lines, "opens", 9.9)
    assert 3.0 < at < 4.0
    assert motion3d.trigger_time(lines, "", 9.9) == 9.9
    assert motion3d.move_progress(at, at) == 0.0 and motion3d.move_progress(at + motion3d.MOVE_SECONDS, at) == 1.0


def test_the_layer_is_drawn_with_one_gold_part_once_moved():
    img = motion3d.layer((540, 960), (270, 400), 500, "laptop", 1.0, -0.4)
    rgba = img.getdata()
    assert any(a > 0 for *_, a in rgba)
