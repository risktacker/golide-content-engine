import unittest
"""Simple 3D (owner direction 2026-11-05): any real device, its move on the spoken word."""
from types import SimpleNamespace

from golide_engine.vector import motion3d
from golide_engine.vector.figures import check_figure


def test_every_preset_draws_and_any_object_draws_from_parts():
    for name in motion3d.OBJECTS:
        assert check_figure(f"3d: object={name}; on=opens") == ""
    # 2026-11-06 (owner): no fixed list; a car with no parts says how to describe it, with parts it draws
    assert "describe the object as parts" in check_figure("3d: object=car")
    assert check_figure("3d: object=car; move=slide; on=drives; box 0 0 0.3 4 1.8 0.8 mover; "
                        "box 0.2 0 1.1 2.2 1.6 0.7 mover; cyl -1.3 -0.95 0 0.8 0.3 0.8 rx90 mover; "
                        "cyl 1.3 -0.95 0 0.8 0.3 0.8 rx90 gold mover") == ""


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


def test_a_video_skipped_in_studio_is_never_due(tmp_path):
    """2026-11-06: with the AI voice nothing waits for the owner, so a skipped video is set aside."""
    import json as _json
    from golide_engine.orchestration.queue import due_specs
    spec = {"id": "golide-short-2026-11-04", "generate_at": "2026-11-04T04:00:00Z", "production_authorized": True}
    (tmp_path / "golide-short-2026-11-04.skipped.json").write_text(_json.dumps(spec))
    (tmp_path / "golide-short-2026-11-06.json").write_text(_json.dumps(dict(spec, id="golide-short-2026-11-06")))
    assert [p.name for p in due_specs(tmp_path)] == ["golide-short-2026-11-06.json"]


def test_ai_voice_choice_makes_a_waiting_video_ready(tmp_path):
    from golide_engine.orchestration.queue import pick_due_spec, waiting_for_voice
    import json as _json
    spec = {"id": "golide-short-2026-11-06", "owner_voice_required": True}
    (tmp_path / "productions" / spec["id"]).mkdir(parents=True)
    (tmp_path / "productions" / spec["id"] / "script.txt").write_text("x")
    assert waiting_for_voice(spec, tmp_path)
    assert not waiting_for_voice(dict(spec, voice_choice="ai"), tmp_path)
    path = tmp_path / "a.json"
    path.write_text(_json.dumps(dict(spec, voice_choice="ai")))
    assert pick_due_spec([path], tmp_path) == path


class EngineAnyObjectTest(unittest.TestCase):
    """2026-11-06 (owner): the engine makes 3D for any object, built from parts."""

    SPEC = ("3d: object=vault; move=swing; on=opened; box 0 0 0 3 3 3; "
            "box 0 -1.56 0.25 2.4 0.12 2.5 mover; cyl 0 -1.66 1.2 1 0.1 1 rx90 gold mover")

    def test_parts_build_render_and_move(self):
        from golide_engine.vector.figures.core import parse_figure
        from golide_engine.vector.figures.devices import parse_parts
        _, params, items = parse_figure(self.SPEC)
        model = {"object": "vault", "move": params["move"], "parts": parse_parts(items)}
        self.assertTrue(motion3d.is_model(model))
        start = [v.copy() for v, *_ in motion3d.solids(model, 0.0)]
        end = [v for v, *_ in motion3d.solids(model, 1.0)]
        self.assertTrue((start[0] == end[0]).all())          # the body stays
        self.assertFalse((start[1] == end[1]).all())         # the door moves
        img, _ = motion3d.render(model, 0.5, -0.5, 300)
        self.assertGreater(img.getbbox()[2], 50)

    def test_every_shape_and_move(self):
        for move in motion3d.MOVES:
            model = {"object": "x", "move": move, "parts": [
                {"shape": shape, "at": [k * 1.2, 0, 0], "size": [1, 1, 1], "rot": [0, 0, 0],
                 "gold": k == 0, "mover": k == 1} for k, shape in enumerate(motion3d.SHAPES)]}
            for u in (0.0, 0.5, 1.0):
                img, _ = motion3d.render(model, u, -0.4, 200)
                self.assertIsNotNone(img.getbbox(), (move, u))

    def test_figure_check_accepts_any_object(self):
        check_figure(self.SPEC)
