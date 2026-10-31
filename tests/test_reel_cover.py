"""Owner direction 2026-10-31: every long upload emails a 1080x1920 reel cover."""

from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from golide_engine.operations import reel_cover
from golide_engine.vector.short_cover import LAYOUTS


def test_layouts_rotate_across_consecutive_long_videos():
    ids = [f"golide-long-2026-{d}" for d in ("10-31", "11-03", "11-05", "11-07")]
    got = [reel_cover.layout_for(i) for i in ids]
    assert sorted(got) == sorted(LAYOUTS)


def test_email_carries_the_cover(tmp_path):
    path = tmp_path / "c.jpg"
    Image.new("RGB", (1080, 1920), (20, 40, 60)).save(path)
    msg = reel_cover.build_reel_cover_email(title="T", youtube_video_id="abc", image_path=path, words="Touch Mac")
    files = [p.get_filename() for p in msg.iter_attachments()]
    assert files == ["c.jpg"]
    assert "1080 x 1920" in msg.get_body(("plain",)).get_content()
    assert "youtu.be/abc" in msg.get_body(("plain",)).get_content()


def test_make_reel_cover_plans_draws_and_sends(tmp_path, monkeypatch):
    plan = {"id": "golide-long-2026-10-31", "object": "MacBook Pro", "drawing": "a laptop", "gold": "screen",
            "people": False, "words": "Touch Arrives", "sub": "Apple", "accent": "gold",
            "bg_top": "#16304a", "bg_bottom": "#3a1830", "layout": "words-top"}
    text = SimpleNamespace(generate_json=lambda *a, **k: SimpleNamespace(value=plan))
    providers = SimpleNamespace(text=lambda live: text, config={"assets": {"support_model": "m", "support_quality": "low"}})
    seen = {}
    monkeypatch.setattr(reel_cover, "draw_cover", lambda cover, work, line_art, ref: seen.setdefault("cover", cover)
                        and Image.new("RGB", (1080, 1920)))
    monkeypatch.setattr(reel_cover, "_send", lambda msg: seen.setdefault("sent", msg) is not None)
    out = reel_cover.make_reel_cover(production_id="golide-long-2026-10-31", title="Mac", story="s",
                                     youtube_video_id="v", source_url="", providers=providers, out_dir=tmp_path)
    assert out["status"] == "sent"
    assert seen["cover"]["layout"] == reel_cover.layout_for("golide-long-2026-10-31")
    assert Image.open(out["path"]).size == (1080, 1920)
