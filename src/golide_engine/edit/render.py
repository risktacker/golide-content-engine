"""Renderer (production plan step 5): edit list -> finished MP4.

1. Goli's mouth: Rhubarb Lip Sync (MIT) reads the owner's recording and times a mouth shape to every sound.
2. Pictures: the composer writes a HyperFrames composition; `npx hyperframes render` films it in headless
   Chrome (silent).
3. Sound: the owner's voice (loudness-normalised), the scene sounds the composer cued, and the day's music
   track with the gentle dip under the voice, mixed with FFmpeg exactly as the current engine does.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

import numpy as np

HYPERFRAMES = "hyperframes@0.9.32"
RHUBARB_VERSION = "1.14.0"


def _browser() -> str:
    """Chrome for filming: the headless shell Playwright installs (HyperFrames' fast capture path),
    else Playwright's full Chromium."""
    if os.environ.get("HYPERFRAMES_BROWSER_PATH"):
        return os.environ["HYPERFRAMES_BROWSER_PATH"]
    import glob

    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or "", str(Path.home() / ".cache/ms-playwright"), "/opt/pw-browsers"]
    for root in filter(None, roots):
        shells = sorted(glob.glob(f"{root}/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"))
        if shells:
            return shells[-1]
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        return p.chromium.executable_path


def _rhubarb() -> str | None:
    for candidate in (os.environ.get("RHUBARB_PATH"), shutil.which("rhubarb"),
                      str(Path.home() / f".cache/golide-rhubarb/Rhubarb-Lip-Sync-{RHUBARB_VERSION}-Linux/rhubarb")):
        if candidate and Path(candidate).exists():
            return candidate
    return None


def lipsync(narration: Path, out: Path) -> list[dict[str, Any]]:
    """Mouth cues [{start, value}] for the recording. Cached in `out`."""
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))
    wav = out.with_suffix(".wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(narration), "-ac", "1", "-ar", "16000", str(wav)],
                   check=True)
    tool = _rhubarb()
    cues: list[dict[str, Any]]
    if tool:
        raw = out.with_suffix(".rhubarb.json")
        subprocess.run([tool, "-f", "json", "-q", "--extendedShapes", "GHX", "-o", str(raw), str(wav)], check=True)
        cues = [{"start": float(c["start"]), "value": c["value"]} for c in json.loads(raw.read_text())["mouthCues"]]
    else:
        # Rhubarb missing on this machine: open the mouth with the loudness of the voice instead.
        print("::warning title=Lip sync::Rhubarb not found, mouth follows loudness")
        cues = _loudness_cues(wav)
    cues = gate(cues, wav)
    wav.unlink(missing_ok=True)
    out.write_text(json.dumps(cues) + "\n", encoding="utf-8")
    return cues


def _envelope(wav: Path, step: float) -> tuple[np.ndarray, float]:
    with wave.open(str(wav)) as w:
        rate = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
    hop = max(1, int(rate * step))
    rms = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, max(1, len(x) - hop), hop)])
    return rms, float(np.percentile(rms, 95)) or 1.0


def gate(cues: list[dict[str, Any]], wav: Path, step: float = 1 / 30) -> list[dict[str, Any]]:
    """2026-11-11 (owner): the mouth must be shut when nothing is said and moving when something is.
    Frame by frame, silence closes the mouth (X) and sound never shows a closed rest mouth."""
    if not cues:
        return cues
    rms, top = _envelope(wav, step)
    quiet = top * 0.09
    out, k, last = [], 0, None
    for f, level in enumerate(rms):
        t = f * step
        while k + 1 < len(cues) and cues[k + 1]["start"] <= t:
            k += 1
        shape = cues[k]["value"] if cues[k]["start"] <= t else "X"
        if level < quiet:
            shape = "X"
        elif shape == "X":
            shape = "B" if level < top * 0.35 else "C"
        if shape != last:
            out.append({"start": round(t, 3), "value": shape})
            last = shape
    return out


def _loudness_cues(wav: Path, step: float = 1 / 12) -> list[dict[str, Any]]:
    with wave.open(str(wav)) as w:
        rate = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
    hop = int(rate * step)
    rms = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, max(1, len(x) - hop), hop)])
    top = float(np.percentile(rms, 95)) or 1.0
    cues, last = [], None
    for i, r in enumerate(rms):
        v = r / top
        shape = "X" if v < .08 else "B" if v < .3 else "C" if v < .6 else "D"
        if shape != last:
            cues.append({"start": round(i * step, 3), "value": shape})
            last = shape
    return cues


SFX_MAP = {"whoosh": "whoosh", "click": "tick", "pop": "pop", "impact": "pop", "riser": "rise"}


def render_sfx(cues: list[dict[str, Any]], duration: float, out: Path) -> Path:
    from ..vector.sfx import LEVELS, RATE, SOUNDS

    track = np.zeros(int(RATE * (duration + 2)), dtype=np.float64)
    last: dict[str, float] = {}
    for c in sorted(cues, key=lambda c: c["t"]):
        kind = SFX_MAP.get(c["kind"])
        if not kind or c["t"] < 0 or c["t"] - last.get(kind, -9) < 0.45:
            continue                       # sparse: the same sound never machine-guns
        last[kind] = c["t"]
        sound = SOUNDS[kind]()
        sound = sound / (np.max(np.abs(sound)) or 1.0) * LEVELS[kind]
        a = int(c["t"] * RATE)
        b = min(len(track), a + len(sound))
        track[a:b] += sound[: b - a]
    pcm = np.clip(track[: int(RATE * duration)], -1, 1)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((pcm * 32767).astype("<i2").tobytes())
    return out


def render(edit: dict[str, Any], folder: Path, narration: Path, output: Path, outfit: str,
           track: dict | None = None, workers: str = "auto") -> Path:
    from ..vector.ambient import LEVEL_DB, LEVELS_DB, render_ambient
    from ..vector.render import AUDIO_MIX, TRACK_DUCK
    from .compose import Composer

    fmt = edit["format"]
    duration = float(edit["duration"])
    comp = folder / "composition"
    if comp.exists():
        shutil.rmtree(comp)
    Composer(fmt, outfit=outfit).build(edit, comp)
    silent = folder / "pictures.mp4"
    env = dict(os.environ, HYPERFRAMES_BROWSER_PATH=_browser())
    subprocess.run(["npx", "-y", HYPERFRAMES, "render", str(comp), "-o", str(silent), "--fps", "30",
                    "--quality", "high", "--workers", workers, "--quiet"], check=True, env=env)
    sfx = render_sfx(json.loads((comp / "sfx.json").read_text()), duration, folder / "sfx.wav")
    level = LEVELS_DB.get(fmt, LEVEL_DB)
    if track:
        from ..vector.music_bed import render as render_track
        bed = render_track(track, duration, folder / "bed.wav", level)
    else:
        bed = render_ambient(duration, folder / "bed.wav", seed_text=str(edit.get("title", "")), level_db=level)
    mix = AUDIO_MIX.get(fmt, AUDIO_MIX["short"])
    # 2026-11-11 (owner): the voice sat too low: it leads now (-14 LUFS) and the music sits further under it
    audio = ("[1:a]loudnorm=I=-14:TP=-1.2:LRA=14,aresample=48000,asplit=2[v][key];"
             f"[2:a]aresample=48000,volume={mix['sfx']}[s];"
             "[3:a]aresample=48000,volume=0.7[b0];"
             f"[b0][key]sidechaincompress={TRACK_DUCK if track else mix['duck']}[b];"
             "[v][s][b]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.89:level=0:attack=2:release=60[a]")
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(narration), "-i", str(sfx),
                    "-i", str(bed), "-filter_complex", audio, "-map", "0:v", "-map", "[a]",
                    # 2026-11-11 (owner): an 85 MB Short is too big: standard H.264 near YouTube's own rate
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-maxrate", "12M", "-bufsize", "24M",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{duration:.3f}", "-movflags", "+faststart",
                    str(output)], check=True)
    # the opening frame doubles as the Short's thumbnail card (as the vector renderer's cover did)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1.2", "-i", str(output), "-frames:v", "1",
                    str(output.with_name(output.stem + "-cover.jpg"))], check=True)
    for f in (sfx, bed):
        f.unlink(missing_ok=True)
    return output
