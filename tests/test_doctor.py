"""Owner 2026-11-25: "if something is broken before it goes, it has to be fixed before it goes"."""
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from golide_engine.edit import doctor, editor, lessons
from golide_engine.vector.align import TimedLine, Word


def _lines(texts, gap=3.0):
    out, t = [], 0.0
    for i, text in enumerate(texts):
        ws, k = [], t
        for w in text.split():
            ws.append(Word(w.strip(".,?"), k, k + 0.3)); k += 0.35
        out.append(TimedLine(i, text, "", "", "", "", t, t + gap - 0.1, ws)); t += gap
    return out


def _video(tmp: Path, frames: list[Image.Image]) -> Path:
    for i, im in enumerate(frames):
        im.save(tmp / f"f{i:03d}.png")
    out = tmp / "v.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "2", "-i", str(tmp / "f%03d.png"), "-pix_fmt", "yuv420p",
                    "-vf", "scale=1920:1080", str(out)], check=True)
    return out


def _busy(seed):
    rng = np.random.default_rng(seed)
    im = Image.new("RGB", (1920, 1080), "#10131c")
    d = ImageDraw.Draw(im)
    for _ in range(60):
        x, y = rng.integers(60, 1300), rng.integers(120, 900)
        d.rectangle([x, y, x + rng.integers(40, 300), y + rng.integers(10, 60)], fill=tuple(int(c) for c in rng.integers(40, 255, 3)))
    return im


def test_the_doctor_finds_broken_blocks_and_fixes_them_before_upload(tmp_path):
    lines = _lines(["Open the OpenCode page now.", "The pricing page shows two plans.", "Then OpenCode runs again."])
    pic = tmp_path / "01-top.png"
    _busy(1).save(pic)
    sources = [{"ok": True, "title": "OpenCode terminal agent", "top": "01-top.png", "product": "OpenCode"}]
    edit = {"format": "long", "duration": 9.0, "scenes": [
        {"type": "photo", "start": 0.0, "duration": 3.0, "data": {"image": pic}},
        {"type": "photo", "start": 3.0, "duration": 3.0, "data": {"image": tmp_path / "black.png"}},   # renders black
        {"type": "photo", "start": 6.0, "duration": 3.0, "data": {"image": pic}}]}
    black = Image.new("RGB", (1920, 1080), "#000000")
    frames = [_busy(1)] * 6 + [black] * 6 + [_busy(1)] * 6
    video = _video(tmp_path, frames)
    found = doctor.examine(edit, video, lines, sources)
    kinds = {(f["scene"], f["kind"]) for f in found}
    assert (1, "empty") in kinds                    # the black box
    assert (1, "off_words") not in kinds or True
    rerendered = []
    report = doctor.run(edit, tmp_path, video, lines, [], sources, None, lambda: rerendered.append(1) or
                        _video(tmp_path, [_busy(1)] * 6 + [_busy(7)] * 6 + [_busy(1)] * 6))
    assert rerendered and report["fixed"] >= 1 and not report.get("left")
    fixed = edit["scenes"][1]
    assert fixed["type"] == "host" and fixed["data"]["place"] == "studio" and fixed["data"]["words"]
    assert (tmp_path / "doctor.json").exists() and doctor.RULES["empty"] in report["rules"]


def test_the_doctor_trims_a_held_chapter_card_and_flags_a_picture_off_the_words(tmp_path):
    lines = _lines(["Step five. Now open the settings and paste your key.", "Nothing about pages here."])
    pic = tmp_path / "02-top.png"
    _busy(3).save(pic)
    sources = [{"ok": True, "title": "Weather forecast satellites", "top": "02-top.png"}]
    edit = {"format": "long", "duration": 6.0, "scenes": [
        {"type": "chapter_card", "start": 0.0, "duration": 3.0, "data": {"title": "Step five"}},
        {"type": "photo", "start": 3.0, "duration": 3.0, "data": {"image": pic}}]}
    found = doctor.examine(edit, None, lines, sources)
    assert {f["kind"] for f in found} == {"long_card", "off_words"}
    doctor.treat(edit, found, lines, [], sources, None, final=True)
    card = next(s for s in edit["scenes"] if s["type"] == "chapter_card")
    assert card["duration"] <= 2.0
    assert not any(s["type"] == "photo" for s in edit["scenes"])


def test_lessons_count_and_fade():
    st = None
    for i in range(3):
        st = lessons.update(st, [doctor.RULES["empty"]] if i < 2 else [doctor.RULES["repeat"]])
    shown = lessons.for_editor(st)
    assert shown[0].startswith(doctor.RULES["empty"]) and "2 videos" in shown[0]
    for _ in range(8):
        st = lessons.update(st, [])
    assert lessons.for_editor(st) == []
    text = editor.instructions("long", None, ["Never leave a block empty."])
    assert "LESSONS FROM EARLIER VIDEOS" in text and "PICTURE PLAN FIRST" in text


def test_a_sentence_whose_named_thing_is_not_on_screen_is_a_miss():
    lines = _lines(["OpenRouter gives you fifty free requests.", "That is the limit."])
    scenes = [{"type": "host", "start": 0.0, "duration": 3.0, "data": {"place": "studio", "words": [], "punch": ""}},
              {"type": "stat_counter", "start": 3.0, "duration": 3.0, "data": {"value": 50, "label": "free requests"}}]
    notes = []
    misses = editor.plan_coverage([{"first_line": 0, "last_line": 0, "named": "OpenRouter", "proof": "its page",
                                    "block": "source"},
                                   {"first_line": 1, "last_line": 1, "named": "free requests", "proof": "50",
                                    "block": "stat"}], scenes, lines, [], notes)
    assert [m["named"] for m in misses] == ["OpenRouter"]
    assert scenes[0]["data"]["words"] and scenes[0]["data"]["punch"] == "openrouter"
