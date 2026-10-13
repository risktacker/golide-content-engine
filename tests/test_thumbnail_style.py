"""2026-10-13: thumbnails are IG-cover style art with 2-4 big words, no people."""
from pathlib import Path

from PIL import Image

from golide_engine.orchestration.production import youtube_thumbnail_prompt
from golide_engine.vector.thumb_text import stamp_thumbnail, thumbnail_words


def test_prompt_is_one_hero_object_without_people():
    prompt = youtube_thumbnail_prompt("Meta's AI shops for you")
    assert "ONE hero object" in prompt
    assert "No people, no faces" in prompt
    assert "paper-cut" in prompt


def test_two_to_four_words_and_contrast():
    words, gold = thumbnail_words("Meta's AI shops for you. Amazon said no.", "Amazon said no")
    assert words == ["AMAZON", "SAID", "NO"] and gold == {"NO"}
    words, gold = thumbnail_words("Your phone is watching you", "watching")
    assert 2 <= len(words) <= 4 and "WATCHING" in gold


def test_stamp_keeps_size(tmp_path):
    p = tmp_path / "t.png"
    Image.new("RGB", (1280, 720), (10, 10, 12)).save(p)
    stamp_thumbnail(p, "Nvidia just passed Apple", "passed Apple")
    assert Image.open(p).size == (1280, 720)
