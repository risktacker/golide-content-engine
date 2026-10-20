"""Thumbnails in the static-post look (owner direction 2026-10-18 and 2026-10-20)."""
from pathlib import Path

import numpy as np
from PIL import Image

from golide_engine.orchestration.production import youtube_thumbnail_prompt
from golide_engine.vector.thumb_text import stamp_thumbnail, thumbnail_line
from golide_engine.vector.thumbnail_style import thumbnail_colors, thumbnail_prompt


def test_prompt_is_one_subject_one_glow_with_premium_light():
    prompt = thumbnail_prompt("OpenCode keys", "a house key on a ring whose teeth glow", ["rose", "teal"])
    assert "ONE hero subject" in prompt and "teeth glow" in prompt
    assert "Exactly ONE key element of it glows bright soft rose red" in prompt
    assert "gradient halo" in prompt and "rim light" in prompt
    assert "bottom 28 percent" in prompt
    assert "No faces" in prompt and "NO text, letters" in prompt


def test_default_subject_is_a_metaphor():
    assert "visual metaphor" in youtube_thumbnail_prompt("Meta's AI shops for you")


def test_glow_colour_follows_meaning_not_always_blue():
    colors = thumbnail_colors({"scene": "scene-02"}, [{"id": "scene-01", "accent": "teal"},
                                                      {"id": "scene-02", "accent": "rose"},
                                                      {"id": "scene-03", "accent": "teal"}])
    assert colors[0] == "rose" and "teal" in colors
    assert "warm soft gold" in thumbnail_prompt("t", "a scale", ["gold"])


def test_line_keeps_the_punch_and_stays_short():
    pairs = thumbnail_line("OpenCode says AI keys were exposed.", "AI keys")
    assert [w for w, b in pairs if b] == ["AI", "keys"]
    long = thumbnail_line("one two three four five six seven eight nine ten punch", "punch")
    assert len(long) <= 7 and long[-1] == ("punch", True)
    assert thumbnail_line("Nothing marked here", "")[-1][1] is True


def test_text_sits_in_the_bottom_band_only(tmp_path):
    p = tmp_path / "t.png"
    Image.new("RGB", (1536, 1024), (10, 10, 12)).save(p)
    stamp_thumbnail(p, "Adobe just put AI inside video editing.", "AI inside", [(240, 138, 128)])
    img = np.asarray(Image.open(p).convert("RGB")).astype(int)
    assert img.shape[:2] == (1024, 1536)
    bright = np.argwhere(img.max(axis=2) > 120)
    assert len(bright) and bright[:, 0].min() > 1024 * 0.66        # nothing over the picture
    rose = (np.abs(img - np.array((240, 138, 128))).sum(axis=2) < 60).sum()
    assert rose > 500                                              # punch in the glow colour
