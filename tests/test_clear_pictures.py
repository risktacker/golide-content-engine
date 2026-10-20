"""Pictures stay clear at a glance (owner direction 2026-10-20)."""

import numpy as np

from golide_engine.vector.illustrate import (CLUTTER_STROKES, MAX_STROKES, Drawing, Stroke, declutter,
                                             illustration_prompt, scene_plan_instructions, shot_of)


def _line(x0, y0, x1, y1, gold=False):
    return Stroke(np.array([[x0, y0], [x1, y1]], np.float64), gold, 2.0)


import unittest


class ClearPictureTests(unittest.TestCase):
    def test_clean_drawing_is_untouched(self):
        clean = [_line(0, i * 10, 800, i * 10) for i in range(40)]
        assert declutter(clean) is clean

    def test_texture_is_removed_but_shape_and_glow_stay(self):
        shape = [_line(0, 0, 800, 0), _line(0, 0, 0, 800), _line(800, 0, 800, 800), _line(0, 800, 800, 800)]
        glow = [_line(300, 300, 310, 305, gold=True)]                      # small but glowing: kept
        texture = [_line(100 + i % 30 * 20, 100 + i // 30 * 20, 108 + i % 30 * 20, 104 + i // 30 * 20)
                   for i in range(400)]                                     # 400 tiny cracks
        out = declutter(shape + glow + texture)
        assert len(shape + glow + texture) > CLUTTER_STROKES
        kept = {id(s) for s in out}
        assert all(id(s) in kept for s in shape) and id(glow[0]) in kept
        assert len(out) <= MAX_STROKES and not any(id(s) in kept for s in texture)

    def test_shots_never_zoom_into_fragments(self):
        d = Drawing([_line(0, 0, 1000, 1000)], 1000, 1000, (0.0, 0.0, 1000.0, 1000.0), None, None)
        for shot in range(1, 5):
            x0, y0, x1, y1 = shot_of(d, shot).bbox
            assert x1 - x0 >= 1000 * 0.68 and y1 - y0 >= 1000 * 0.68

    def test_rules_ask_for_definition_not_bans(self):
        rules = scene_plan_instructions("long")
        assert "DEFINED, NEVER VAGUE" in rules and "a network: a few clear nodes" in rules
        assert "clearly built network or constellation" in rules and "LABELS" in rules and "DIAGRAMS" in rules
        prompt = illustration_prompt("a jar of coins", "the label panel on the jar", "long", label="BONDS")
        assert "texture mark" not in prompt and "No textures" in prompt and "empty label panel" in prompt
        assert "BONDS" not in prompt                      # the word is typeset by us, never drawn by the model
        assert "empty label panel" not in illustration_prompt("a jar", "the lid", "long")

    def test_label_is_printed_on_the_glowing_part_clear_of_lines(self):
        from golide_engine.vector.scene_labels import attach_label

        jar = [_line(200, 200, 200, 800), _line(200, 800, 600, 800), _line(600, 800, 600, 200)]
        panel = [_line(280, 420, 520, 420, gold=True), _line(520, 420, 520, 580, gold=True),
                 _line(520, 580, 280, 580, gold=True), _line(280, 580, 280, 420, gold=True)]
        d = Drawing(jar + panel, 900, 900, (200.0, 200.0, 600.0, 800.0), None, None)
        assert attach_label(d, "bonds", (233, 196, 106))
        surface, x, y, after, _ = d.labels[0]
        assert 280 <= x and x + surface.get_width() <= 520 and 420 <= y and y + surface.get_height() <= 580
        assert after > 0.8 and not attach_label(d, "  ", (1, 2, 3))
