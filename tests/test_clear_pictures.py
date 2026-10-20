"""Pictures stay clear at a glance (owner direction 2026-10-20)."""

import numpy as np

from golide_engine.vector.illustrate import (CLUTTER_STROKES, MAX_STROKES, Drawing, Stroke, declutter,
                                             illustration_prompt, scene_plan_instructions, shot_of)


def _line(x0, y0, x1, y1, gold=False):
    return Stroke(np.array([[x0, y0], [x1, y1]], np.float64), gold, 2.0)


def test_clean_drawing_is_untouched():
    clean = [_line(0, i * 10, 800, i * 10) for i in range(40)]
    assert declutter(clean) is clean


def test_texture_is_removed_but_shape_and_glow_stay():
    shape = [_line(0, 0, 800, 0), _line(0, 0, 0, 800), _line(800, 0, 800, 800), _line(0, 800, 800, 800)]
    glow = [_line(300, 300, 310, 305, gold=True)]                      # small but glowing: kept
    texture = [_line(100 + i % 30 * 20, 100 + i // 30 * 20, 108 + i % 30 * 20, 104 + i // 30 * 20)
               for i in range(400)]                                     # 400 tiny cracks
    out = declutter(shape + glow + texture)
    assert len(shape + glow + texture) > CLUTTER_STROKES
    kept = {id(s) for s in out}
    assert all(id(s) in kept for s in shape) and id(glow[0]) in kept
    assert len(out) <= MAX_STROKES and not any(id(s) in kept for s in texture)


def test_shots_never_zoom_into_fragments():
    d = Drawing([_line(0, 0, 1000, 1000)], 1000, 1000, (0.0, 0.0, 1000.0, 1000.0), None, None)
    for shot in range(1, 5):
        x0, y0, x1, y1 = shot_of(d, shot).bbox
        assert x1 - x0 >= 1000 * 0.68 and y1 - y0 >= 1000 * 0.68


def test_rules_ask_for_concrete_blank_objects():
    rules = scene_plan_instructions("long")
    assert "CLEAR AT A GLANCE" in rules and "BLANK" in rules
    assert "constellation of connected dots" not in rules
    prompt = illustration_prompt("a jar of coins", "the coins", "long")
    assert "texture mark" not in prompt and "No textures" in prompt and "blank" in prompt
