"""2026-11-17 (owner): Stickman Shorts run the cartoon-short-kit with its own packages (stickman/short.py)."""
import numpy as np

from golide_engine.stickman import short


def test_timing_is_the_kits_phrases_format_split_at_punctuation():
    words = [{"word": w, "start": i * 0.4, "end": i * 0.4 + 0.3} for i, w in enumerate("A man waited, for years. Then".split())]
    t = short.phrases(words, 3.0)
    assert t["phrases"]["frames30"] == 90 and [p["text"] for p in t["phrases"]["phrases"]] == ["A man waited,", "for years.", "Then"]
    assert t["words"][0] == {"w": "A", "s": 0.0, "e": 0.3}


def test_only_the_story_parts_of_main_js_are_replaced():
    main = (short.KIT / "engine" / "main.js").read_text(encoding="utf-8")
    out = short.splice(main, "const DECK = 0; /* WORLD */", "function worldState(S, f) { waterU.t.value = f / 30; }")
    assert "/* WORLD */" in out and "temple" not in out.split(short.WORLD_B)[0].split(short.WORLD_A)[1]
    assert "worldProps(W_, f);" in out and "helmetState" not in out
    for kept in ("// ---------- ink / normal-depth contract ----------", "function drawActors(", "window.renderFrame",
                 "const dofScene", "function applyLight"):
        assert kept in out


def test_audio_py_keeps_the_synths_and_writes_stems_only():
    code = short.audio_py({"music_end": 12.5, "cues_py": "place(sfx, whoosh(0.6), F(18), 0.5)"}, 600)
    assert "DUR = 600 / 30" in code and "MUSIC_END = 12.50" in code and "def sting():" in code
    assert 'write("music.wav", music); write("sfx.wav", sfx)' in code and "load_voice()\n" not in code.split("F = lambda")[1]
    compile(code, "audio.py", "exec")


def test_music_sits_at_half_the_voice_level(tmp_path):
    import wave
    sr = 48000
    t = np.arange(sr * 4) / sr
    def write(name, x):
        with wave.open(str(tmp_path / name), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((x * 32767).astype(np.int16).tobytes())
    write("voice.wav", 0.4 * np.sin(2 * np.pi * 150 * t) * (np.sin(2 * np.pi * 2 * t) > 0))
    write("music.wav", 0.9 * np.sin(2 * np.pi * 220 * t))
    write("sfx.wav", np.where((t > 1) & (t < 1.2), 0.9, 0.0) * np.sin(2 * np.pi * 900 * t))
    levels = short.mix(tmp_path, tmp_path / "voice.wav")
    assert abs(levels["music_db_vs_voice"] + 6.02) < 0.3 and levels["sfx_db_vs_voice"] <= -6.0
    assert (tmp_path / "mix_raw.wav").exists()


def test_the_writer_gets_the_skill_and_the_kit_code():
    rules = short.instructions()
    assert "## Rules" in rules and "4.6 Look check" in rules
    for piece in ("window.renderFrame", "export const camFromKeys", "export class Pen", "export const romanFront"):
        assert piece in rules
    assert "nobody's mouth talks" in rules


def test_fix_rounds_apply_exact_edits_only():
    parts = {"story_js": "const x = MATH.sin(1);", "world_js": "a", "world_state_js": "b", "cast_js": "", "cues_py": ""}
    fixed = short.apply_edits(parts, [{"part": "story_js", "old": "MATH.sin", "new": "Math.sin"}])
    assert fixed["story_js"] == "const x = Math.sin(1);" and parts["story_js"].startswith("const x = MATH")
    import pytest
    with pytest.raises(ValueError):
        short.apply_edits(parts, [{"part": "world_js", "old": "zzz", "new": "y"}])
    assert "MATH.sin" in short.fix_request(parts, "ReferenceError: MATH is not defined")


def test_look_check_catches_black_frames_and_repeated_pictures(tmp_path, monkeypatch):
    """2026-11-18 (owner): no black blocks, no picture repeated across the Short."""
    from PIL import Image, ImageDraw
    from golide_engine.stickman import short

    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "story.js").write_text(
        "const SHOTS = [" + ",".join(f"{{a: {a}, b: {a + 60}}}" for a in (0, 60, 120, 180, 240)) + "];")

    def scene(f):
        im = Image.new("L", (216, 384), 200)
        d = ImageDraw.Draw(im)
        if f in (30, 90, 150):                                  # three shots, the same picture
            d.rectangle((40, 100, 170, 300), fill=60)
        elif f == 210:                                          # mostly black
            d.rectangle((0, 0, 216, 330), fill=3)
        else:
            d.ellipse(((f * 7) % 150, 40, (f * 7) % 150 + 60, 100 + f % 200), fill=20)
            d.rectangle((0, f % 300, 216, f % 300 + 40), fill=255)
        return im

    def fake_frames(project, picks, outdir, resume=True):
        outdir.mkdir(parents=True, exist_ok=True)
        for f in picks:
            scene(f).convert("RGB").save(outdir / f"f{f:04d}.jpg")
        return []

    monkeypatch.setattr(short, "frames", fake_frames)
    monkeypatch.setattr(short.subprocess, "run", lambda *a, **k: None)
    _, problems = short.look_check(tmp_path)
    assert "frame 210 is" in problems and "black" in problems
    assert "frames 30, 90, 150 show nearly the same picture" in problems
    assert "frame 270" not in problems
