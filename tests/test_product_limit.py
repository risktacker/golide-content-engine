"""Owner direction 2026-10-31: the product photo is a reveal, not 85% of the video."""

from golide_engine.vector.illustrate import scene_plan_instructions
from golide_engine.vector.pacing import limit_products, pace_scenes, scene_range


def _scenes(n, product=True):
    return [{"id": f"s{i}", "first_line": i, "last_line": i, "product": product} for i in range(n)]


TIMES = [(i * 5.0 + 60, i * 5.0 + 64) for i in range(40)]   # after the hook, 4 s lines


def test_long_video_keeps_three_products_never_in_a_row():
    out = limit_products(_scenes(12), TIMES, "long")
    flags = [s["product"] for s in out]
    assert sum(flags) == 3
    assert not any(a and b for a, b in zip(flags, flags[1:]))


def test_short_keeps_one():
    assert sum(s["product"] for s in limit_products(_scenes(6), TIMES, "short")) == 1


def test_a_long_product_scene_becomes_line_art_so_it_is_never_repeated():
    scene = {"id": "p", "first_line": 0, "last_line": 5, "product": True}   # 29 s
    out = limit_products([scene], TIMES, "long")
    assert out[0]["product"] is False
    shots = pace_scenes([{"id": "q", "first_line": 0, "last_line": 1, "product": True}], TIMES, "long")
    assert len(shots) == 1   # a kept product photo is one block


def test_long_videos_get_more_faster_pictures_and_the_rule():
    low, high = scene_range("long", 510)
    assert high == 48 and low < high
    rules = scene_plan_instructions("long", 510)
    assert "ILLUSTRATE WHAT IS SAID" in rules and "at most 3" in rules
