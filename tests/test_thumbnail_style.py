"""Thumbnails in the static-post look (owner direction 2026-10-18 and 2026-10-20)."""
from pathlib import Path

import numpy as np
from PIL import Image

from golide_engine.orchestration.production import youtube_thumbnail_prompt
from golide_engine.vector.thumb_text import stamp_thumbnail, thumbnail_words
from golide_engine.vector.thumbnail_style import thumbnail_colors, thumbnail_prompt


import unittest


class ThumbnailStyleTests(unittest.TestCase):
    def test_prompt_is_one_subject_one_glow_with_premium_light(self):
        prompt = thumbnail_prompt("OpenCode keys", "a house key on a ring whose teeth glow", ["rose", "teal"])
        assert "ONE hero subject" in prompt and "teeth glow" in prompt
        assert "Exactly ONE key element of it glows bright soft rose red" in prompt
        assert "gradient halo" in prompt and "rim light" in prompt
        assert "left 42 percent" in prompt and "right 55 percent" in prompt
        assert "No faces" in prompt and "NO text, letters" in prompt

    def test_default_subject_is_a_metaphor(self):
        assert "visual metaphor" in youtube_thumbnail_prompt("Meta's AI shops for you")

    def test_glow_colour_follows_meaning_not_always_blue(self):
        colors = thumbnail_colors({"scene": "scene-02"}, [{"id": "scene-01", "accent": "teal"},
                                                          {"id": "scene-02", "accent": "rose"},
                                                          {"id": "scene-03", "accent": "teal"}])
        assert colors[0] == "rose" and "teal" in colors
        assert "warm soft gold" in thumbnail_prompt("t", "a scale", ["gold"])

    def test_one_to_three_words_with_a_punch(self):
        self.assertEqual([("WHO", False), ("GETS", False), ("IT?", True)], thumbnail_words("Who gets it?", "it?"))
        self.assertEqual(3, len(thumbnail_words("one two three four five", "")))
        self.assertTrue(thumbnail_words("Keys leaked", "")[-1][1])

    def test_words_sit_left_and_never_in_the_duration_corner(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        p = Path(tmp.name) / "t.png"
        Image.new("RGB", (1536, 1024), (10, 10, 12)).save(p)
        stamp_thumbnail(p, "Who gets it?", "it?", [(240, 138, 128)])
        img = np.asarray(Image.open(p).convert("RGB")).astype(int)
        bright = np.argwhere(img.max(axis=2) > 120)
        assert len(bright) and bright[:, 1].max() < 1536 * 0.46          # left side only
        assert not ((bright[:, 0] > 1024 * 0.82) & (bright[:, 1] > 1536 * 0.7)).any()
        rose = (np.abs(img - np.array((240, 138, 128))).sum(axis=2) < 60).sum()
        assert rose > 2000                                                # punch in the glow colour
