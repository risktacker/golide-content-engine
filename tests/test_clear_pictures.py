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


class LabelStaysInViewTests(unittest.TestCase):
    def test_a_label_outside_the_lines_still_counts_as_the_picture(self):
        from golide_engine.vector.scene_labels import attach_label

        # A narrow glowing door: the word cannot fit on it and lands beside it.
        house = [_line(100, 100, 800, 100), _line(800, 100, 800, 700), _line(100, 700, 800, 700)]
        door = [_line(440, 560, 440, 700, gold=True), _line(470, 560, 470, 700, gold=True)]
        d = Drawing(house + door, 900, 900, (100.0, 100.0, 800.0, 700.0), None, None)
        attach_label(d, "FUND", (127, 224, 210))
        surface, x, y, _after, _ = d.labels[0]
        x0, y0, x1, y1 = d.bbox
        self.assertTrue(x0 <= x and y0 <= y and x + surface.get_width() <= x1 and y + surface.get_height() <= y1)

    def test_a_shot_that_touches_a_label_keeps_it_whole(self):
        from golide_engine.vector.scene_labels import attach_label

        jar = [_line(200, 200, 200, 800), _line(200, 800, 600, 800), _line(600, 800, 600, 200)]
        panel = [_line(280, 420, 520, 420, gold=True), _line(520, 420, 520, 580, gold=True),
                 _line(520, 580, 280, 580, gold=True), _line(280, 580, 280, 420, gold=True)]
        d = Drawing(jar + panel, 900, 900, (200.0, 200.0, 600.0, 800.0), None, None)
        attach_label(d, "BONDS", (233, 196, 106))
        surface, x, y, _after, _ = d.labels[0]
        for shot in range(1, 6):
            x0, y0, x1, y1 = shot_of(d, shot).bbox
            touches = x < x1 and x + surface.get_width() > x0 and y < y1 and y + surface.get_height() > y0
            if touches:
                self.assertTrue(x0 <= x and x + surface.get_width() <= x1 and y0 <= y and y + surface.get_height() <= y1)

    def test_a_zoom_never_slices_an_object(self):
        ground = [_line(0, 900, 1000, 900)]
        tree = [_line(850, 500, 950, 500), _line(950, 500, 950, 600), _line(950, 600, 850, 600),
                _line(850, 600, 850, 500)]
        house = [_line(100, 300, 500, 300), _line(500, 300, 500, 900), _line(100, 300, 100, 900)]
        d = Drawing(ground + tree + house, 1000, 1000, (0.0, 300.0, 1000.0, 900.0), None, None)
        for shot in range(1, 6):
            x0, y0, x1, y1 = shot_of(d, shot).bbox
            cut = 850 < x1 < 950 or 850 < x0 < 950
            if x1 > 850 and x0 < 950:      # the shot reaches the tree
                self.assertFalse(cut, shot)


class UnclearPictureTests(unittest.TestCase):
    """2026-10-21: an all-gold tangle reached a short; the outline must survive and unclear art is redrawn."""

    def test_a_mostly_gold_cluttered_picture_keeps_its_white_outline(self):
        outline = [_line(0, 0, 900, 0), _line(900, 0, 900, 900), _line(900, 900, 0, 900), _line(0, 900, 0, 0)]
        glow = [_line(100 + i % 20 * 30, 100 + i // 20 * 30, 300 + i % 20 * 30, 300 + i // 20 * 30, gold=True)
                for i in range(200)]
        out = declutter(outline + glow)
        kept = {id(s) for s in out}
        self.assertTrue(all(id(s) in kept for s in outline))
        self.assertLessEqual(sum(1 for s in out if s.gold), 60)

    def test_problems_are_named_for_an_all_gold_or_empty_picture(self):
        from golide_engine.vector.illustrate import picture_problems

        gold = Drawing([_line(0, 0, 900, 900, gold=True)] * 6 + [_line(0, 0, 10, 10)], 900, 900,
                       (0.0, 0.0, 900.0, 900.0), None, None)
        self.assertTrue(any("glows" in p for p in picture_problems(gold)))
        empty = Drawing([_line(0, 0, 900, 0)], 900, 900, (0.0, 0.0, 900.0, 0.0), None, None)
        self.assertTrue(any("empty" in p for p in picture_problems(empty)))
        good = Drawing([_line(0, i * 100, 900, i * 100) for i in range(8)] + [_line(400, 400, 500, 450, gold=True)],
                       900, 900, (0.0, 0.0, 900.0, 900.0), None, None)
        self.assertEqual([], picture_problems(good))
