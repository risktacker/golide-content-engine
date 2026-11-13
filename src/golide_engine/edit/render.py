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


# 2026-11-13 (owner, point 8): a real low hit on big landings (was a pop), a riser into reveals, a shimmer when
# something turns gold or opens, typing under typed text
SFX_MAP = {"whoosh": "whoosh", "click": "tick", "pop": "pop", "impact": "hit", "riser": "rise", "shimmer": "shimmer",
           "typing": "typing"}


# 2026-11-13 (owner: "too much of stupid pops. Whoosh good"): 64 sounds in a 38 s Short. Pops and ticks are out; a
# whoosh carries the cut; an impact (with its riser) only on a big number; the rest only where something is really
# happening (keys typing, a glass object). Each kind keeps its own spacing and no two sounds land within 0.6 s.
SOUND_GAP = {"whoosh": 0.9, "impact": 4.0, "riser": 4.0, "shimmer": 6.0, "typing": 3.0}
SOUND_MIN_APART = 0.6


def sound_plan(cues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The cues that are actually played."""
    kept: list[dict[str, Any]] = []
    last: dict[str, float] = {}
    for c in sorted(cues, key=lambda c: c["t"]):
        kind = c.get("kind")
        if kind not in SOUND_GAP or c["t"] < 0 or c["t"] - last.get(kind, -99) < SOUND_GAP[kind]:
            continue
        pair = kind == "impact" and kept and kept[-1]["kind"] == "riser"     # a riser leads into its hit
        if kept and c["t"] - kept[-1]["t"] < SOUND_MIN_APART and not pair:
            continue
        last[kind] = c["t"]
        kept.append(c)
    # a riser with no hit after it is a build-up to nothing
    return [c for i, c in enumerate(kept) if c["kind"] != "riser"
            or any(d["kind"] == "impact" and 0 < d["t"] - c["t"] <= 2.5 for d in kept[i + 1:])]


def quiet_expr(windows: list[list[float]], floor: float = 0.12) -> str:
    """2026-11-13 (owner, point 8): the music drops almost out under a serious line and comes back after it. A
    volume expression: 1 normally, `floor` inside each window, with a 0.6 s fade down and a 0.9 s fade back."""
    if not windows:
        return "1"
    parts = [f"(1-{1 - floor:.2f}*clip(min((t-{a - 0.6:.2f})/0.6,({b + 0.9:.2f}-t)/0.9),0,1))" for a, b in windows]
    expr = parts[0]
    for part in parts[1:]:
        expr = f"min({expr},{part})"
    return expr.replace(",", "\\,")


def render_sfx(cues: list[dict[str, Any]], duration: float, out: Path) -> Path:
    from ..vector.sfx import ACTION_LEVELS, ACTION_SOUNDS, LEVELS, RATE, SOUNDS
    sounds, levels = {**ACTION_SOUNDS, **SOUNDS}, {**ACTION_LEVELS, **LEVELS}

    track = np.zeros(int(RATE * (duration + 2)), dtype=np.float64)
    for c in sound_plan(cues):
        kind = SFX_MAP.get(c["kind"])
        if not kind:
            continue
        sound = sounds[kind]()
        sound = sound / (np.max(np.abs(sound)) or 1.0) * levels[kind]
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
    from .compose import Composer

    fmt = edit["format"]
    duration = float(edit["duration"])
    comp = folder / "composition"
    if comp.exists():
        shutil.rmtree(comp)
    # 2026-11-12 (owner): nothing may overlap: build, measure every box at many moments, fix, repeat
    from .compose import SIZES
    from .layout import resolve, save_report

    def build(e):
        if comp.exists():
            shutil.rmtree(comp)
        Composer(fmt, outfit=outfit).build(e, comp)

    resolve(edit, build, comp, SIZES[fmt])
    save_report(edit, folder / "layout-report.json")
    for note in edit.get("notes", []):
        if note.startswith("overlap left"):
            print(f"::warning title=Layout::{note}")
    silent = folder / "pictures.mp4"
    env = dict(os.environ, HYPERFRAMES_BROWSER_PATH=_browser())
    subprocess.run(["npx", "-y", HYPERFRAMES, "render", str(comp), "-o", str(silent), "--fps", "30",
                    "--quality", "high", "--workers", workers, "--quiet"], check=True, env=env)
    mix(edit, folder, narration, silent, output, track)
    return output


VOICE_CHAIN = ("highpass=f=80,equalizer=f=280:t=q:w=1.2:g=-2.5,equalizer=f=3800:t=q:w=1.4:g=2.5,"
               "deesser=i=0.35,acompressor=threshold=0.1:ratio=2.5:attack=8:release=120:makeup=1.6")


def mix(edit: dict[str, Any], folder: Path, narration: Path, pictures: Path, output: Path,
        track: dict | None = None, copy_video: bool = False) -> Path:
    """Sound under the pictures: the voice, the scene sounds, the music; then the H.264 encode (or, with
    copy_video, the already-encoded pictures of a finished video kept as they are)."""
    from ..vector.ambient import LEVEL_DB, LEVELS_DB
    from ..vector.render import AUDIO_MIX, TRACK_DUCK

    fmt = edit["format"]
    duration = float(edit["duration"])
    comp = folder / "composition"
    sfx = render_sfx(json.loads((comp / "sfx.json").read_text()), duration, folder / "sfx.wav")
    level = LEVELS_DB.get(fmt, LEVEL_DB)
    from ..vector.music_bed import pick, render as render_track
    # 2026-11-12 (owner): never the generated ambient bed (it plays as noise): always a real track
    track = track or pick(fmt, None, str(edit.get("title", "")))
    if not track:
        raise RuntimeError("no music track found in config/background-music.json")
    bed = render_track(track, duration, folder / "bed.wav", level)
    mixdown = AUDIO_MIX.get(fmt, AUDIO_MIX["short"])
    # 2026-11-11 (owner): the voice sat too low: it leads now (-14 LUFS) and the music sits further under it.
    # 2026-11-12: the limiter sits at -2 dBFS (as the illustration mix does): at -1 dBFS the AAC encode
    # pushed the true peak to -0.42 dBTP and QA (max -1 dBTP) refused the first long Goli video.
    # 2026-11-13 (owner, from Isaac's AI-voice method): the voice is cleaned like a recorded one before it is
    # levelled: rumble cut, a little mud taken out, presence lifted, esses tamed, gently compressed
    audio = ("[1:a]" + VOICE_CHAIN + ",loudnorm=I=-14:TP=-1.5:LRA=14,aresample=48000,asplit=2[v][key];"
             f"[2:a]aresample=48000,volume={mixdown['sfx']}[s];"
             # 2026-11-12 (owner): the music was too loud in the first long Goli video: 8 dB lower
             f"[3:a]aresample=48000,volume=0.4,volume='{quiet_expr(edit.get('quiet') or [])}':eval=frame[b0];"
             f"[b0][key]sidechaincompress={TRACK_DUCK}[b];"
             # limited at 4x the sample rate so the peaks between samples are caught too (true peak)
             "[v][s][b]amix=inputs=3:duration=first:normalize=0,aresample=192000,"
             "alimiter=limit=0.79:level=0:attack=2:release=60,aresample=48000,volume={trim}dB[a]")
    output.parent.mkdir(parents=True, exist_ok=True)
    target = output.with_name(output.stem + ".mixing.mp4") if copy_video else output
    video = (["-c:v", "copy"] if copy_video else
             # 2026-11-11 (owner): an 85 MB Short is too big: standard H.264 near YouTube's own rate
             ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-maxrate", "12M", "-bufsize", "24M",
              "-pix_fmt", "yuv420p"])
    from ..quality.audio import measure_loudness

    trim = 0.0
    for _ in range(3):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(pictures), "-i", str(narration), "-i", str(sfx),
                        "-i", str(bed), "-filter_complex", audio.replace("{trim}", f"{trim:.2f}"), "-map", "0:v",
                        "-map", "[a]", *video, "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{duration:.3f}",
                        "-movflags", "+faststart", str(target)], check=True)
        # 2026-11-12: measured after the encode, as QA measures it; brought under -1.5 dBTP if it is over
        peak = measure_loudness(target)["true_peak_dbtp"]
        if peak <= -1.3:
            break
        trim -= peak + 1.6
        print(json.dumps({"status": "mix_peak", "true_peak": peak, "trim_db": round(trim, 2)}))
        if not copy_video:          # the pictures are encoded once; a second pass only redoes the sound
            pictures, video = target, ["-c:v", "copy"]
            target = output.with_name(output.stem + ".mixing.mp4")
            copy_video = True
    if copy_video:
        target.replace(output)
    # the opening frame doubles as the Short's thumbnail card (as the vector renderer's cover did)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1.2", "-i", str(output), "-frames:v", "1",
                    str(output.with_name(output.stem + "-cover.jpg"))], check=True)
    for f in (sfx, bed):
        f.unlink(missing_ok=True)
    return output
