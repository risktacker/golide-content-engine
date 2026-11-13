"""2026-11-13 (owner, point 8): real hits and risers, and the music dropping out under serious lines."""
import subprocess
import wave
from types import SimpleNamespace

import numpy as np

from golide_engine.edit import editor
from golide_engine.edit.render import SFX_MAP, quiet_expr, render_sfx


def test_quiet_windows_follow_the_serious_paragraphs():
    voice = ("[excited] This part is the fun one, it really is.\n\n"
             "[serious][slowly] But nobody has checked whether the tests themselves are right.\n\n"
             "[curious] So what happens next?")
    lines = [SimpleNamespace(text="This part is the fun one, it really is.", start=0.0, end=2.5),
             SimpleNamespace(text="But nobody has checked whether", start=2.6, end=4.4),
             SimpleNamespace(text="the tests themselves are right.", start=4.4, end=6.0),
             SimpleNamespace(text="So what happens next?", start=6.1, end=7.5)]
    assert editor.quiet_windows(voice, lines) == [[2.6, 6.0]]


def test_music_really_drops_inside_the_window(tmp_path):
    out = tmp_path / "q.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=f=300:d=7:sample_rate=8000",
                    "-filter_complex", f"[0:a]volume='{quiet_expr([[2.0, 4.0]])}':eval=frame[o]", "-map", "[o]",
                    str(out)], check=True)
    w = wave.open(str(out))
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768
    level = lambda t: np.abs(x[int(t * 8000):int(t * 8000) + 800]).max()
    assert level(3.0) < 0.2 * level(0.5) and level(6.0) > 0.9 * level(0.5)


def test_new_sounds_render(tmp_path):
    assert SFX_MAP["impact"] == "hit"
    out = render_sfx([{"kind": k, "t": 0.5 + i} for i, k in enumerate(("impact", "riser", "shimmer", "typing"))],
                     6.0, tmp_path / "s.wav")
    w = wave.open(str(out))
    assert np.abs(np.frombuffer(w.readframes(w.getnframes()), np.int16)).max() > 1000
