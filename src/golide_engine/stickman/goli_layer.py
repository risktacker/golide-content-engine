"""Goli beside a Stickman video (owner 2026-11-17): for the owner's channel only, switched on per video.

The Stickman video is finished first, exactly as its kit makes it (picture, music, sound). This layer then puts it
in a framed panel and stands Goli beside it as the explainer: the same Goli as the edit engine (edit/mascot.py, the
"side" place, facing the content), his mouth on the owner's voice (Rhubarb cues, moved by any chapter-card pauses),
and his reactions on the story's own events: a number lands -> he points at it, a shock line -> shock, a list or a
versus -> he explains, a question -> he thinks, the payoff -> both hands up. The sound is the Stickman video's own,
untouched; only the picture is re-rendered.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HOLD = 2.2          # a pose stays at least this long, so he never twitches between poses

# the kit's emotions and shot kinds -> Goli's poses (edit/mascot.py POSES)
EMOTION = {"shocked": "shock", "angry": "shock", "worried": "think", "nervous": "think", "thinking": "think",
           "sad": "shrug", "tired": "shrug", "embarrassed": "shrug", "happy": "thumbs_up", "excited": "thumbs_up",
           "smile": "thumbs_up", "confident": "thumbs_up", "smug": "point", "greedy": "point"}
KIND = {"counter": "point", "chart": "point", "table": "point", "map": "point", "icon": "point", "list": "explain",
        "versus": "explain", "crowd": "explain", "title": "think", "skyline": "talk", "walk": "talk",
        "wide": "talk", "closeup": "talk"}


def _settle(events: list[tuple[float, str]], duration: float) -> list[dict[str, Any]]:
    """Time-ordered poses, at least HOLD apart, never the same twice in a row; between reactions he talks."""
    out: list[dict[str, Any]] = [{"pose": "talk", "at": 0.0}]
    for t, pose in sorted(events):
        if t < 0.3 or t > duration - 0.6 or pose == out[-1]["pose"] or t - out[-1]["at"] < HOLD:
            continue
        out.append({"pose": pose, "at": round(t, 3)})
    final: list[dict[str, Any]] = []
    for i, p in enumerate(out):
        final.append(p)
        nxt = out[i + 1]["at"] if i + 1 < len(out) else duration
        if p["pose"] != "talk" and nxt - p["at"] > HOLD * 2.6:      # back to talking when the next event is far
            final.append({"pose": "talk", "at": round(p["at"] + HOLD * 1.6, 3)})
    return final


def reactions_long(project: Path, duration: float) -> list[dict[str, Any]]:
    """Goli's poses from a ReachMora story, on the output clock (the kit's own Timeline and cue words)."""
    from . import longform

    sys.path.insert(0, str(longform.KIT))
    try:
        from engine.timeline import Timeline
    finally:
        sys.path.remove(str(longform.KIT))
    story = json.loads((project / "story.json").read_text(encoding="utf-8"))
    timing = json.loads((project / "timing.json").read_text(encoding="utf-8"))
    tl = Timeline(story, timing)
    events: list[tuple[float, str]] = []
    for shot in tl.shots:
        sp = shot["spec"]
        kind = sp.get("kind", "wide")
        cue = None
        for key in ("value", "chart", "stamp", "polaroid"):
            if isinstance(sp.get(key), dict) and sp[key].get("at") is not None:
                cue = sp[key]["at"]
                break
        if cue is None and sp.get("labels"):
            cue = (sp["labels"][0] or {}).get("at")
        t = tl.cue(shot, cue, default=0.3) if not shot.get("silent") else shot["t0"] + 0.2
        pose = KIND.get(kind, "talk")
        if sp.get("emotion") in EMOTION and kind == "closeup":
            pose = EMOTION[sp["emotion"]]
        if sp.get("stamp"):
            pose = "shock"
        if sp.get("polaroid"):
            pose = "point_both_up"
        events.append((t, pose))
    return _settle(events, duration)


def reactions_short(project: Path, duration: float) -> list[dict[str, Any]]:
    """Goli's poses for a cartoon-kit Short: a reaction at each new shot (point, explain, think in turn), shock on
    the twist (where the music stops), both hands up for the payoff in the last shot."""
    story = (project / "web" / "story.js").read_text(encoding="utf-8")
    spans = [(int(a), int(b)) for a, b in re.findall(r"\ba:\s*(\d+)\s*,\s*b:\s*(\d+)", story)]
    audio = (project / "audio.py").read_text(encoding="utf-8") if (project / "audio.py").exists() else ""
    twist = re.search(r"MUSIC_END = ([\d.]+)", audio)
    cycle = ("point", "explain", "think")
    events = [(a / 30 + 0.3, cycle[k % 3]) for k, (a, _) in enumerate(spans[1:-1])]
    if twist:
        events.append((float(twist.group(1)), "shock"))
    if spans:
        events.append((spans[-1][0] / 30 + 0.4, "point_both_up"))
    return _settle(events, duration)


def _duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def edit_list(fmt: str, video: Path, duration: float, poses: list[dict[str, Any]], cues: list[dict[str, Any]],
              outfit: str) -> dict[str, Any]:
    return {"format": fmt, "duration": duration, "notes": [], "captions": [], "look": "glass",
            "scenes": [
                {"type": "stage_video", "start": 0.0, "duration": duration, "in": "cut", "data": {"video": str(video)}},
                {"type": "host", "start": 0.0, "duration": duration, "in": "cut",
                 "data": {"place": "beside", "poses": poses, "cues": cues, "outfit": outfit}},
            ]}


def add(fmt: str, video: Path, narration: Path, folder: Path, output: Path, outfit: str,
        poses: list[dict[str, Any]], pauses: list[tuple[float, float]] | None = None) -> Path:
    """Render the panel with Goli beside it and put the Stickman video's own sound under it."""
    from ..edit.compose import Composer
    from ..edit.render import HYPERFRAMES, _browser, lipsync

    folder.mkdir(parents=True, exist_ok=True)
    duration = _duration(video)
    cues_path = folder / "goli-cues.json"
    if not cues_path.exists():
        lipsync(narration, cues_path)
    cues = json.loads(cues_path.read_text(encoding="utf-8"))
    if pauses:          # the voice sits later in the video after each silent chapter card
        shift = lambda t: t + sum(d for v, d in pauses if v <= t + 1e-9)
        cues = [dict(c, start=shift(float(c["start"])), end=shift(float(c.get("end", c["start"])))) for c in cues]
    comp = folder / "goli-composition"
    if comp.exists():
        shutil.rmtree(comp)
    Composer(fmt, outfit=outfit).build(edit_list(fmt, video, duration, poses, cues, outfit), comp)
    pictures = folder / "goli-pictures.mp4"
    env = dict(os.environ, HYPERFRAMES_BROWSER_PATH=_browser())
    subprocess.run(["npx", "-y", HYPERFRAMES, "render", str(comp), "-o", str(pictures), "--fps", "30",
                    "--quality", "high", "--workers", "auto", "--quiet"], check=True, env=env)
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pictures), "-i", str(video), "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(output)], check=True)
    return output
