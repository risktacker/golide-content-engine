from pathlib import Path

from PIL import Image, ImageDraw

from golide_engine.vector import thumb_engine as E


def mask(box):
    m = Image.new("L", (E.W, E.H), 0)
    ImageDraw.Draw(m).rectangle(box, fill=255)
    return m


def test_layout_check_catches_collisions():
    rec = [("text", mask([100, 100, 400, 200])), ("tile", mask([350, 150, 500, 300])),
           ("face", mask([700, 50, 900, 300])), ("goli", mask([650, 50, 950, 720]))]
    hits = E.check(rec)
    assert any("text" in h and "tile" in h for h in hits)          # words under a logo: caught
    assert not any("face" in h and "goli" in h for h in hits)      # Goli and his own face: fine
    assert E.check([("text", mask([0, 10, 300, 100]))])            # words off the left edge: caught


def test_never_repeats_and_skips_collisions(tmp_path, monkeypatch):
    drawn = []

    def fake(name, bad=False):
        def draw(s):
            drawn.append(name)
            E.T.record("text", mask([100, 100, 400, 200]))
            if bad:
                E.T.record("tile", mask([300, 150, 500, 300]))
            return Image.new("RGBA", (E.W, E.H), (255, 255, 255, 255))
        return draw

    designs = [E.Design("a", "", lambda s: True, fake("a")), E.Design("b", "", lambda s: True, fake("b", bad=True)),
               E.Design("c", "", lambda s: True, fake("c"))]
    monkeypatch.setattr(E, "DESIGNS", designs)
    monkeypatch.setattr(E, "BY_NAME", {d.name: d for d in designs})
    out = tmp_path / "t.jpg"
    used = E.make("Story", "Big Words", "Words", [], out, recent=["a"], log=lambda e: None)
    assert used == "c" and "a" not in drawn                        # last design skipped, the colliding one too
    assert Image.open(out).size == (1280, 720)


def test_video_id():
    assert E.video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=3") == "dQw4w9WgXcQ"
    assert E.video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
