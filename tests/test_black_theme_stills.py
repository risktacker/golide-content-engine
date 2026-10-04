from pathlib import Path

from golide_engine.engine.social_image import SocialImageProfile
from golide_engine.engine.typeset import compose_post, tokenize


def test_prompt_is_black_theme_and_forbids_text():
    prompt = SocialImageProfile("config/social-image-profile.json").build_prompt(
        concept="A glass jar holding one small key.", glow_color="cyan"
    )
    assert "Pure black" in prompt
    assert "Exactly one element" in prompt
    assert "bottom third" in prompt
    assert "ABSOLUTELY NO text" in prompt
    assert "cyan" in prompt


def test_emphasis_phrase_is_marked():
    tokens = tokenize("Most people never notice who holds the key", "holds the key")
    assert [t.text for t in tokens if t.emphasis] == ["holds", "the", "key"]


def test_compose_outputs_platform_sizes(tmp_path: Path):
    from PIL import Image

    master = tmp_path / "m.png"
    Image.new("RGB", (1024, 1536), (11, 11, 14)).save(master)
    for size in ((1080, 1350), (1080, 1080)):
        out = tmp_path / f"{size[1]}.jpg"
        compose_post(master, "Your words build the first minute", "first minute", out, size)
        with Image.open(out) as image:
            assert image.size == size
