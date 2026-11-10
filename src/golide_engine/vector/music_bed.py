"""Real background music under the voice (owner 2026-11-10).

One track per video, rotating through the format's list in config/background-music.json. It sits
at the same low level the synthesised bed used, fades in over the first seconds and out at the end,
and repeats with a long crossfade when the video is longer than the track. No track listed: the
synthesised bed is used as before.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "config" / "background-music.json"
CROSSFADE = 6.0


def settings() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def pick(fmt: str, n: int | None) -> dict | None:
    tracks = [t for t in settings().get(fmt, []) if (ROOT / t["file"]).exists()]
    if not tracks:
        return None
    return dict(tracks[(n or 0) % len(tracks)], path=str(ROOT / tracks[(n or 0) % len(tracks)]["file"]))


def _length(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _loudness(path: str) -> float:
    import re
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True)
    found = re.findall(r"I:\s+(-?[0-9.]+) LUFS", out.stderr)
    return float(found[-1]) if found else -16.0


def render(track: dict, duration: float, output: Path, level_db: float) -> Path:
    """The track as a bed of ``duration`` seconds at about ``level_db`` LUFS, faded in and out."""
    s = settings()
    fade_in, fade_out = float(s.get("fade_in_seconds", 4.0)), float(s.get("fade_out_seconds", 4.0))
    length = _length(track["path"])
    copies = 1
    while length * copies - CROSSFADE * (copies - 1) < duration + 0.5:
        copies += 1
    inputs: list[str] = []
    for _ in range(copies):
        inputs += ["-i", track["path"]]
    chain, last = [], "[0:a]"
    for k in range(1, copies):
        chain.append(f"{last}[{k}:a]acrossfade=d={CROSSFADE}:c1=tri:c2=tri[x{k}]")
        last = f"[x{k}]"
    level = level_db + float(track.get("level_offset_db", 0.0))
    gain = level - _loudness(track["path"])          # a plain gain: the track keeps its own dynamics
    chain.append(f"{last}aresample=48000,volume={gain:.2f}dB,atrim=0:{duration + 0.5:.3f},"
                 f"afade=t=in:st=0:d={fade_in},afade=t=out:st={max(0.0, duration - fade_out):.3f}:d={fade_out}[m]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(chain),
                    "-map", "[m]", "-ac", "2", "-ar", "48000", str(output)], check=True)
    return output


def credit(track: dict | None) -> str:
    """The description line naming the music."""
    if not track:
        return ""
    return track.get("attribution") or (f"{track['title']} by {track['artist']}" if track.get("artist") not in ("", "unknown") else "")
