"""Owner direction 2026-11-01: thumbnails and covers modelled on the source, with a little brand."""

from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from golide_engine.operations import reel_cover
from golide_engine.vector import thumb_model
from golide_engine.vector.thumb_model import BRAND_GOLD, add_mark, clean_layout, modelled_prompt, place_text

LAYOUT = {"their_text": "BILLS NEVER END", "our_text": "LOSSES NEVER END", "highlight": "never",
          "text_zone": "bottom-left", "text_lines": 2, "text_case": "upper", "text_style": "outline",
          "text_size": "large", "text_color": "#ffffff", "highlight_color": "#5fe0c0", "box_color": "",
          "subject": "MacBook Pro", "action": "a hand touching the screen", "subject_zone": "right",
          "subject_size": "large", "subject_angle": "three-quarter", "background": "scene",
          "bg_colors": ["#ffffff", "#cccccc"], "background_note": "desk", "extras": ["arrow"], "mood": "bold"}


def test_brand_gold_always_wins_and_no_faces_are_asked_for():
    layout = clean_layout(LAYOUT)
    assert layout["highlight_color"] == BRAND_GOLD
    prompt = modelled_prompt("T", "", layout, False)
    assert "no faces" in prompt.lower() and "hand touching the screen" in prompt
    assert "gold" in prompt and "arrow" in prompt
    assert "reference image" not in prompt.lower()   # the source is never handed to the image model


def test_words_and_mark_are_set_on_the_picture():
    layout = clean_layout(LAYOUT)
    blank = Image.new("RGB", (1280, 720), (40, 40, 40))
    out = add_mark(place_text(blank, layout), layout)
    assert out.size == (1280, 720) and out.tobytes() != blank.tobytes()
    assert place_text(blank, dict(layout, text_zone="none")).tobytes() == blank.tobytes()


def test_reel_cover_is_modelled_when_the_source_has_a_thumbnail(tmp_path, monkeypatch):
    src = tmp_path / "src.jpg"
    Image.new("RGB", (480, 360)).save(src)
    providers = SimpleNamespace(text=lambda live: None, config={"assets": {"support_model": "m", "support_quality": "low"}})
    monkeypatch.setattr(reel_cover, "fetch_reference", lambda url, dest: src)
    monkeypatch.setattr(thumb_model, "read_layout", lambda text, path, title: clean_layout(LAYOUT))
    monkeypatch.setattr(thumb_model, "canvas_from_layout", lambda cut, mask, layout: Image.new("RGB", (1080, 1920)))
    monkeypatch.setattr(reel_cover, "drawing_cutout", lambda art, accent: (None, None))
    monkeypatch.setattr("golide_engine.providers.openai_media.OpenAILineArtProvider.create",
                        lambda self, *a, **k: None, raising=False)
    sent = []
    monkeypatch.setattr(reel_cover, "_send", lambda msg: sent.append(msg) or True)
    out = reel_cover.make_reel_cover(production_id="golide-short-2026-11-02", title="Mac", story="s",
                                     youtube_video_id="v", source_url="https://youtu.be/x", providers=providers,
                                     out_dir=tmp_path)
    assert out["layout"] == "modelled" and out["words"] == "LOSSES NEVER END"
    assert "today's short" in sent[0].get_body(("plain",)).get_content()
    assert Path(out["path"]).exists()
