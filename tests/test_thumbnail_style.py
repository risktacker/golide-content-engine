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


def test_static_post_look_in_several_colours():
    from golide_engine.vector.thumbnail_style import thumbnail_colors, thumbnail_prompt

    prompt = thumbnail_prompt("Tesla Roadster", "a car on a ramp", ["rose", "teal"])
    assert "deep-space background" in prompt and "soft rose red" in prompt and "electric teal" in prompt
    colors = thumbnail_colors({"scene": "scene-02"}, [{"id": "scene-01", "accent": "teal"},
                                                      {"id": "scene-02", "accent": "rose"},
                                                      {"id": "scene-03", "accent": "teal"}])
    assert colors[0] == "rose" and "teal" in colors


def test_punch_words_take_the_palette(tmp_path):
    p = tmp_path / "t.png"
    Image.new("RGB", (1280, 720), (10, 10, 12)).save(p)
    stamp_thumbnail(p, "Tesla jets beat grip", "jets grip", [(240, 138, 128), (127, 224, 210)])
    assert Image.open(p).size == (1280, 720)
