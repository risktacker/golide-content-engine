"""Owner 2026-11-10: real logos on thumbnails, real music faded in and out, a free guide per video,
published real 3D models before CAD."""
import json
import subprocess
from pathlib import Path

from PIL import Image

from golide_engine.vector import logos, music_bed, real_models
from golide_engine.engine.guide import render_pdf, sources

SVG = '<svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M2 2h20v20H2z"/></svg>'


def test_logo_tile_is_the_brand_colour_with_a_white_mark():
    t = logos.tile({"hex": "D97757", "svg": SVG}, 200)
    px = t.getpixel((t.size[0] // 2, t.size[1] // 2))
    assert px[3] == 255 and min(px[:3]) > 200            # the mark, white
    edge = t.getpixel((t.size[0] // 2, int(t.size[1] * 0.22) + 8))
    assert edge[0] > edge[2] + 40                          # the tile, in the brand's own orange


def test_logos_go_on_the_right_and_unknown_brands_are_skipped(monkeypatch):
    monkeypatch.setattr(logos, "catalogue", lambda: {"claude": {"title": "Claude", "hex": "D97757", "svg": SVG}})
    img = Image.new("RGB", (1280, 720), (5, 5, 7))
    assert logos.place(img, ["Claude", "Not A Brand"], 0.45) == ["Claude"]
    left = sum(img.crop((0, 0, 600, 720)).convert("L").getdata())
    right = sum(img.crop((680, 0, 1280, 720)).convert("L").getdata())
    assert right > left * 5


def test_music_bed_fades_in_and_out(tmp_path):
    src = tmp_path / "t.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=12",
                    str(src)], check=True)
    out = music_bed.render({"path": str(src)}, 20.0, tmp_path / "bed.wav", -21.0)
    import wave, numpy as np
    with wave.open(str(out)) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float)
        rate = w.getframerate() * w.getnchannels()
    start, middle, end = (np.abs(a[int(s * rate):int((s + 0.3) * rate)]).mean() for s in (0.05, 10.0, 19.8))
    assert start < middle * 0.2 and end < middle * 0.2   # faded at both ends, full in the middle


def test_the_guide_pdf_lists_its_sources(tmp_path):
    research = {"claims": [{"claim": "x", "source_title": "Agency", "source_url": "https://example.org/a"},
                           {"claim": "y", "source_title": "Agency", "source_url": "https://example.org/a"}]}
    refs = sources(research)
    assert refs == [("Agency", "https://example.org/a")]
    pdf = render_pdf({"headline": "H", "intro": "I", "sections": [{"heading": "S", "points": ["p"]}],
                      "next_steps": ["n"]}, "T", refs, tmp_path / "g.pdf")
    assert pdf.read_bytes()[:4] == b"%PDF"


def test_published_models_need_an_allowed_licence_and_are_credited():
    assert set(real_models.LICENCES) == {"cc0", "by"}       # never share-alike or non-commercial
    line = real_models.credit_line({"credit": {"title": "Car", "author": "Ann", "url": "https://s/x", "licence": "CC BY 4.0"}})
    assert "Ann" in line and "CC BY 4.0" in line


def test_approved_styles_pick_by_story_and_draw_without_the_image_model(tmp_path, monkeypatch):
    from golide_engine.vector import thumb_styles as T

    assert T.choose("Nvidia Lost $400B In One Day", 1, 0) == "dark_drama"
    assert T.choose("Best AI Video Tools", 6, 0) == "platter"
    assert {T.choose("How Chips Are Made", 1, n) for n in range(3)} == {"light_glass", "editorial", "grid_paper"}
    icon = {"title": "Claude", "hex": "D97757", "svg": SVG}
    monkeypatch.setattr(logos, "find", lambda name: icon if name == "Claude" else None)
    fake = lambda spec: Image.new("RGBA", (spec["w"], spec["h"]), (217, 119, 87, 255))
    monkeypatch.setattr(T, "goli", lambda *a, **k: Image.new("RGBA", (300, 600), (40, 90, 200, 255)))
    for n in range(3):
        out = tmp_path / f"t{n}.jpg"
        style = T.make("How Claude Builds Apps", "Claude Builds", "Builds", ["Claude", "Nobody"], n, out, tiles=fake)
        assert style in T.STYLES and Image.open(out).size == (1280, 720)
    # 2026-11-12: Goli hosts every thumbnail; no logo -> the source's real picture, else the big words
    assert T.make("Story", "Big Words", "Words", ["Nobody"], 0, tmp_path / "none.jpg", tiles=fake,
                  with_goli=False) is None
    assert T.make("Story", "Big Words", "Words", ["Nobody"], 0, tmp_path / "w.jpg", tiles=fake) == "words"
    pic = tmp_path / "p.png"
    Image.new("RGB", (900, 600), (90, 120, 170)).save(pic)
    assert T.make("Story", "Big Words", "Words", [], 0, tmp_path / "p.jpg", tiles=fake, photo=pic) == "photo_card"
    assert Image.open(tmp_path / "p.jpg").size == (1280, 720)


def test_alert_shorts_get_the_trailer_music(monkeypatch):
    # after the signature month (owner 2026-11-13) the alert track comes back
    cfg = dict(music_bed.settings(), short_signature={})
    monkeypatch.setattr(music_bed, "settings", lambda: cfg)
    picked = music_bed.pick("short", 0, "Hackers breach a bank")
    assert picked is None or picked["title"] == "Motivational Trailer"


def test_every_short_gets_the_signature_track_this_month():
    for n, story in enumerate(["Hackers breach a bank", "A new phone", "USB colours"]):
        picked = music_bed.pick("short", n, story)
        assert picked is None or picked["title"].startswith("Discipline Finishes")


def test_follow_button_shows_only_while_it_is_said():
    from types import SimpleNamespace as N
    from golide_engine.vector.render import VectorRenderer

    r = VectorRenderer.__new__(VectorRenderer)
    r.follow = {1}
    groups = [N(lines=[N(index=0, start=0, end=5), N(index=1, start=5, end=8), N(index=2, start=8, end=300)])]
    assert r._follow_state(groups, 3) is None
    assert r._follow_state(groups, 6) is not None
    assert r._follow_state(groups, 11) is None and r._follow_state(groups, 200) is None
