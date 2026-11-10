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
