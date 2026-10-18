"""Fast hook pacing and spoken-number cards (owner direction 2026-10-18)."""

import unittest

from golide_engine.vector.number_cards import Card, _tok, find_cards, parse
from golide_engine.vector.pacing import pace_scenes, reveal_seconds, scene_range


def _p(text):
    return parse([p for w in text.split() for p in _tok(w)])


class NumberTests(unittest.TestCase):
    def test_spoken_and_written_numbers(self):
        self.assertEqual(_p("two point seven g")[0], "2.7 G")
        self.assertEqual(_p("two hundred and fifty kilograms")[0], "250 KG")
        self.assertEqual(_p("fifty-thousand-dollar deposit")[0], "$50,000")
        self.assertEqual(_p("552 billion dollars")[0], "$552 BILLION")
        self.assertEqual(_p("sixty miles an hour")[0], "60 MPH")
        self.assertEqual(_p("twenty twenty-eight")[0], "2028")
        self.assertEqual(_p("twenty-seven metres")[0], "27 METRES")
        self.assertEqual(_p("80% of people")[0], "80%")

    def test_small_bare_numbers_are_not_cards(self):
        self.assertIsNone(_p("three questions"))
        self.assertIsNone(_p("ten jets"))

    def test_cards_are_spaced_and_timed(self):
        class W:
            def __init__(self, text, start):
                self.text, self.start, self.end = text, start, start + 0.3

        class L:
            def __init__(self, words):
                self.words = words
        words = [W(w, i * 0.35) for i, w in enumerate("it holds six hundred litres and two hundred kilograms".split())]
        cards = find_cards([L(words)])
        self.assertEqual(cards[0].text, "600 LITRES")
        self.assertEqual(len(cards), 1)  # the second number is too close to the first
        self.assertTrue(isinstance(cards[0], Card) and 1.5 <= cards[0].end - cards[0].start <= 2.7)


class PacingTests(unittest.TestCase):
    def test_hook_scenes_split_into_shots(self):
        times = [(i * 3.0, i * 3.0 + 2.9) for i in range(8)]
        scenes = [{"id": "scene-01", "first_line": 0, "last_line": 5}, {"id": "scene-02", "first_line": 6, "last_line": 7}]
        paced = pace_scenes(scenes, times, "short")
        self.assertEqual(len([s for s in paced if s["first_line"] < 6]), 6)
        self.assertEqual(paced[1]["picture_of"], "scene-01")
        self.assertEqual(paced[1]["shot"], 1)

    def test_body_allows_longer_scenes(self):
        times = [(70 + i * 3.0, 70 + i * 3.0 + 2.9) for i in range(4)]
        paced = pace_scenes([{"id": "s", "first_line": 0, "last_line": 3}], times, "long")
        self.assertEqual(len(paced), 1)

    def test_scene_count_grows_with_length(self):
        self.assertGreater(scene_range("long", 360)[1], 18)
        self.assertGreaterEqual(scene_range("short", 75)[0], 12)

    def test_pen_follows_the_voice(self):
        self.assertLess(reveal_seconds(3.0, 12, True), reveal_seconds(3.0, 5, True))
        self.assertLessEqual(reveal_seconds(3.0, 9, True), 2.4)
        self.assertLess(reveal_seconds(12.0, 30, False), 7.5)


class ShotTests(unittest.TestCase):
    def test_shot_frames_part_of_the_picture(self):
        import numpy as np

        from golide_engine.vector.illustrate import Drawing, Stroke, shot_of

        strokes = [Stroke(np.array([[0, 0], [100, 100]], float), False, 2),
                   Stroke(np.array([[70, 70], [90, 90]], float), True, 2)]
        d = Drawing(strokes, 100, 100, (0, 0, 100, 100))
        shot = shot_of(d, 1)
        self.assertTrue(shot.clip)
        self.assertLess(shot.bbox[2] - shot.bbox[0], 100)
        self.assertEqual(d.bbox, (0, 0, 100, 100))  # the original picture is untouched


if __name__ == "__main__":
    unittest.main()
