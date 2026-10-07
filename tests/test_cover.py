import os
import unittest
from unittest.mock import patch

from golide_engine.orchestration.production import youtube_thumbnail_prompt
from golide_engine.vector.cover import cover_spec, pick_scene


class Stroke:
    def __init__(self, gold):
        self.gold = gold


class Drawing:
    def __init__(self, total, gold):
        self.total = total
        self.strokes = [Stroke(gold)]


class CoverTests(unittest.TestCase):
    def test_cover_falls_back_to_the_title(self):
        spec = cover_spec({"title": "Meta's New AI Shops for You. Amazon Said No."})
        self.assertTrue(spec["text"].startswith("Meta's New AI"))
        self.assertEqual(cover_spec({"cover": {"text": "Hook", "gold": "Hook"}})["text"], "Hook")

    def test_storyboard_pick_wins_else_the_richest_drawing(self):
        drawings = {"a": Drawing(100, False), "b": Drawing(90, True), "c": Drawing(50, False)}
        self.assertEqual(pick_scene(["a", "b", "c"], drawings, "c"), "c")
        self.assertEqual(pick_scene(["a", "b", "c"], drawings), "b")  # 90 * 1.25 beats 100

    def test_youtube_prompt_uses_the_moment_and_never_text(self):
        prompt = youtube_thumbnail_prompt("Title", "a robot hand reaching for a cart as a shutter slams")
        self.assertIn("shutter slams", prompt)
        self.assertIn("No words, letters", prompt)
        self.assertIn("decisive moment", prompt)
