"""Puppet scenes inside Goli videos (owner 2026-11-17): a beat about people (a team, customers, a founder, a crowd)
is shown as one ReachMora shot, drawn by the kit's own engine (vendor/reachmora, unchanged), in a frame in the Goli
video. The storyboard writes the shot in the kit's own story.json format (references/story-format.md), so there
is no extra model call: the scene costs $0 beyond the storyboard the video already pays for.

The shot is checked with the kit's plan check and our collision check (stickman/collide.py). A shot that fails is
not sent back to a writer (that would cost money): the caller shows the free stand-in instead.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from . import longform

# shot kinds a single beat can use (owner 2026-11-17: no text cards; real people are real photos, not puppets)
KINDS = ("wide", "closeup", "walk", "crowd", "table", "versus", "icon", "map", "counter", "chart")
DROP = ("s", "lower_third", "polaroid", "talk", "whip")


def shot_from(doc: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """(cast, shot) from what the storyboard wrote: {"cast": {...}, "shot": {...}}. Raises ValueError when it is
    not a shot this scene can draw."""
    cast = doc.get("cast") or {}
    shot = dict(doc.get("shot") or {})
    if not isinstance(cast, dict) or shot.get("kind", "wide") not in KINDS:
        raise ValueError(f"puppet shot kind {shot.get('kind')!r} is not one of {', '.join(KINDS)}")
    for key in DROP:
        shot.pop(key, None)
    for c in shot.get("chars") or []:
        c.pop("talk", None)                       # nobody's mouth talks: the voice tells it
    shot["labels"] = (shot.get("labels") or [])[:2]
    if shot.get("kind") == "crowd":
        shot.pop("highlight", None)       # its ring can sit on the frame edge (seen 2026-11-17): no cut-off shapes
    used = {c.get("id") for c in shot.get("chars") or []} | {shot.get("who")} | \
        {(shot.get(side) or {}).get("who") for side in ("left", "right")} | {shot.get("highlight")}
    missing = sorted(i for i in used if i and i not in cast)
    if missing:
        raise ValueError(f"puppet shot uses characters not in its cast: {', '.join(missing)}")
    return cast, shot


def prepare(project: Path, text: str, words: list[dict[str, Any]], duration: float, doc: dict[str, Any]) -> None:
    """A one-shot ReachMora project: the beat's words as the script, their timing (seconds from the beat's start),
    a silent voice track of the beat's length (the video's own voice plays over it), and story.json."""
    cast, shot = shot_from(doc)
    project.mkdir(parents=True, exist_ok=True)
    script = longform.script_text(text)
    (project / "script.txt").write_text(script, encoding="utf-8")
    timing = longform.timing(script, [{"word": w["text"], "start": w["t"], "end": w["t"] + 0.25} for w in words], duration)
    (project / "timing.json").write_text(json.dumps(timing, indent=1, ensure_ascii=False), encoding="utf-8")
    n = len(timing["sentences"])
    shot["s"] = [0, n - 1] if n > 1 else [0]
    story = {"title": "scene", "mood": "calm", "cast": cast, "shots": [shot]}
    (project / "story.json").write_text(json.dumps(story, indent=1, ensure_ascii=False), encoding="utf-8")
    voice = project / "voice.wav"
    if not voice.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t",
                        f"{duration:.3f}", str(voice)], check=True)


def problems(project: Path) -> list[str]:
    """The kit's plan warnings plus our collision check, on real frames."""
    try:
        found = longform.warnings(longform.kit("plan", project, timeout=600))
    except RuntimeError as error:
        return [str(error)[-400:]]
    if found:
        return found
    return list(longform.collisions(project)["problems"])


def make(text: str, words: list[dict[str, Any]], duration: float, doc: dict[str, Any], project: Path,
         res: str | None = None) -> dict[str, Any] | None:
    """Prepare, check and render one puppet shot. Returns {video, size} or None (the caller's stand-in shows)."""
    try:
        prepare(project, text, words, duration, doc)
    except (ValueError, RuntimeError) as error:
        print(json.dumps({"status": "puppet_unusable", "why": str(error)[:300]}))
        return None
    found = problems(project)
    print(json.dumps({"status": "puppet_check", "ok": not found, "problems": found[:4]}))
    if found:
        return None
    try:
        longform.kit("render", project, *(["--res", res] if res else []), timeout=1800)
    except RuntimeError as error:
        print(json.dumps({"status": "puppet_render_failed", "why": str(error)[-300:]}))
        return None
    video = project / "work" / "video.mp4"
    if not video.exists():
        return None
    return {"video": str(video), "size": [1280, 720] if res == "720" else [1920, 1080]}
