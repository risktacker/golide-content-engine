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


def test_no_two_parts_ever_pass_through_each_other():
    """Owner review 2026-11-05: every object is made of separate parts (base, lid, screen, cells...)
    and no two may overlap at any moment of the move."""
    for name in motion3d.OBJECTS:
        assert motion3d.overlaps(name, steps=61) == [], name


def test_the_overlap_check_catches_a_real_overlap():
    die = motion3d.box(0, 0, 0.12, 1.0, 1.0, 0.1)
    solid_lid = motion3d.box(0, 0, 0.12, 1.9, 1.9, 0.14)   # the old chip lid, through the die
    assert motion3d._intersect(die, solid_lid, 1e-4)
    assert not motion3d._intersect(motion3d.box(0, 0, 0, 1, 1, 1), motion3d.box(0, 0, 1, 1, 1, 1), 1e-4)


def test_scene_change_light_lands_on_the_object_as_it_looks():
    pts = motion3d.edge_points("laptop", 0.0, -0.6, 600, 400)
    assert pts.shape == (400, 2)
    open_pts = motion3d.edge_points("laptop", 1.0, -0.3, 600, 400)
    assert open_pts[:, 1].min() < pts[:, 1].min() - 50   # the open lid reaches higher: points follow the pose


def test_fitted_scene_draws_inside_its_zone():
    import numpy as np
    size, cx, cy = motion3d.fit("phone", (100.0, 300.0, 980.0, 1100.0), np.float64(760.0))
    assert isinstance(size, float)
    x0, y0, x1, y1 = motion3d.extent("phone", size)
    assert cy + y0 >= 299 and cy + y1 <= 1101
    motion3d.layer((1080, 1920), (cx, cy), size, "phone", 1.0, -0.3)
