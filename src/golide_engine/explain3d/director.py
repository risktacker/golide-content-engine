"""Stage: read the script and the voice timing, pick the moments 3D explains best, and
compile them into shot lists. Motion lands on spoken words, never on guessed seconds."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .blueprint import slug
from .catalog import load

MIN_SHOT, MAX_SHOT = 4.0, 12.0
EXPLODE_SECONDS = 2.4
PLAN_SCHEMA = {
    "type": "object",
    "properties": {"shots": {"type": "array", "items": {"type": "object", "properties": {
        "first_line": {"type": "integer"}, "last_line": {"type": "integer"},
        "subject": {"type": "string"}, "world": {"type": "string"}, "move": {"type": "string"},
        "beats": {"type": "array", "items": {"type": "object", "properties": {
            "action": {"type": "string"},
            "part_hint": {"type": "string"},
            "label": {"type": "string"},
            "cue_word": {"type": "string"},
        }, "required": ["action", "part_hint", "label", "cue_word"], "additionalProperties": False}},
    }, "required": ["first_line", "last_line", "subject", "world", "move", "beats"],
        "additionalProperties": False}}},
    "required": ["shots"], "additionalProperties": False,
}
# Each move is a set of camera numbers, so the director names intent, not maths.
MOVES = {
    "orbit_slow": {"yaw": 30, "pitch": (20, 16), "zoom": (1.0, 1.0)},
    "orbit_wide": {"yaw": 65, "pitch": (14, 24), "zoom": (1.15, 1.05)},
    "push_in": {"yaw": 16, "pitch": (18, 14), "zoom": (1.3, 0.85)},
    "pull_out": {"yaw": 18, "pitch": (12, 20), "zoom": (0.85, 1.25)},
}
# Worlds that need a set camera height or a tilted horizon, whatever the move.
WORLD_FRAMING = {
    "space": {"world": {"name": "space", "altitude": 110, "lon": 195, "lat": 8, "sun_dir": [0.62, -0.5, 0.6]},
              "light": {"rig": "sun_space", "sun": 5.5, "earthshine": 0.8},
              "camera": {"pitch": (31, 26), "aim_offset": [0, 0, -2.5], "roll": -9}},
    "studio": {"world": {"name": "studio"}, "light": {"rig": "studio_soft"}, "camera": {}},
}


def instructions(format_name: str, max_shots: int, max_seconds: float, catalog: dict | None = None) -> str:
    catalog = catalog or load()
    worlds = "\n".join(f"- {k}: {v}" for k, v in catalog["worlds"].items())
    return f"""You direct the 3D moments of an explainer video. Most of the video stays illustrated. You pick
the few lines where seeing the real thing in 3D explains it best: how a machine is built, what is inside
it, how its parts work together. Skip lines about opinions, people or money.

Pick up to {max_shots} shots, {max_seconds:.0f} seconds in total, each {MIN_SHOT:.0f}-{MAX_SHOT:.0f} seconds, using
the times given beside each line. Shots never overlap. first_line and last_line are line numbers.
subject names one real thing exactly, like "Hubble Space Telescope" or "V8 engine piston".

WORLDS
{worlds}
CAMERA MOVES: {', '.join(catalog['moves'])}. Vary them.

beats are what happens inside the shot, each landing on one word the narrator says in that shot.
action is explode (the object opens up), glow (a part lights up), signal (a signal leaves a part) or label
(a part gets named). part_hint names the part in plain words. label is the short on-screen name, or empty.
cue_word is copied exactly from the spoken line. Use 1-4 beats per shot.
If no line suits 3D, return no shots. A video with no 3D is fine."""


def rows(lines: list[str], times: list[tuple[float, float]]) -> str:
    return "\n".join(f"{i}: [{times[i][0]:.1f}-{times[i][1]:.1f}s] {text}" for i, text in enumerate(lines))


def _norm(word: str) -> str:
    return re.sub(r"[^a-z0-9]", "", word.lower())


def cue_time(word: str, words: list[dict[str, Any]], start: float, end: float) -> float | None:
    """When the cue word is actually said inside the shot."""
    target = _norm(word)
    for w in words:
        at = float(w["start"])
        if start <= at < end and _norm(str(w.get("word", w.get("text", "")))) == target:
            return at
    return None


def match_part(hint: str, parts: list[dict[str, Any]]) -> str | None:
    """Link the director's plain words to a blueprint part by shared words."""
    want = {_norm(w) for w in re.split(r"[\s_-]+", hint) if _norm(w)}
    best, score = None, 0
    for part in parts:
        have = {_norm(w) for w in re.split(r"[\s_-]+", f"{part['id']} {part.get('label', '')}") if _norm(w)}
        overlap = len(want & have)
        if overlap > score:
            best, score = part["id"], overlap
    return best


def _variation(seed: str) -> tuple[float, float, float]:
    """Each shot gets its own angle, so no two videos open the same way."""
    h = hashlib.sha256(seed.encode()).digest()
    return h[0] % 360, (h[1] % 21) - 10, -1.0 if h[2] % 2 else 1.0


def compile_shot(plan: dict[str, Any], blueprint: dict[str, Any], blueprint_name: str, blueprint_dir: str,
                 start: float, end: float, words: list[dict[str, Any]], vertical: bool = False,
                 fps: int = 24) -> dict[str, Any]:
    """One director shot plus the blueprint and real voice timing makes one render-ready shot."""
    duration = round(end - start, 3)
    parts = blueprint["parts"]
    framing = WORLD_FRAMING.get(plan["world"], WORLD_FRAMING["studio"])
    move = MOVES.get(plan["move"], MOVES["orbit_slow"])
    yaw, tilt, turn = _variation(f"{plan['subject']}|{start:.2f}")
    pitch = framing["camera"].get("pitch", move["pitch"])
    actions: list[dict[str, Any]] = [{"type": "drift", "deg_per_sec": 0.9}]
    effects: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    opens = False
    timed = []
    for beat in plan.get("beats", []):
        at = cue_time(beat["cue_word"], words, start, end)
        timed.append((at - start if at is not None else duration * 0.3, beat))
    timed.sort(key=lambda row: row[0])
    for index, (at, beat) in enumerate(timed):
        kind = beat["action"]
        next_at = timed[index + 1][0] if index + 1 < len(timed) else duration
        part = match_part(beat.get("part_hint", ""), parts)
        if kind == "explode":
            opens = True
            actions.append({"type": "explode", "start": at, "end": min(duration, at + EXPLODE_SECONDS)})
        elif kind == "glow" and part:
            actions.append({"type": "glow", "part": part, "start": at, "end": max(next_at, at + 1.2)})
        elif kind == "signal" and part:
            effects.append({"type": "signal_beam", "from": part, "start": at, "end": duration, "length": 70, "speed": 16})
        if part and (kind == "label" or beat.get("label")):
            side = 1 if len(labels) % 2 == 0 else -1
            labels.append({"part": part, "text": beat.get("label") or beat.get("part_hint"),
                           "start": at, "end": duration - 0.1, "dx": 0.09 * side, "dy": -0.1 if index % 2 else 0.1})
    camera = {"move": "orbit", "lens": 38, "yaw_from": yaw, "yaw_to": yaw + turn * move["yaw"],
              "pitch_from": pitch[0], "pitch_to": pitch[1], "zoom_from": move["zoom"][0], "zoom_to": move["zoom"][1],
              "fit_exploded": opens, "aim_offset": framing["camera"].get("aim_offset", [0, 0, 0]),
              "roll": framing["camera"].get("roll", 0)}
    return {"duration": duration, "fps": fps, "vertical": vertical, "world": framing["world"], "light": framing["light"],
            "object": {"blueprint": blueprint_name, "blueprint_dir": blueprint_dir, "rotate": [tilt, 0, tilt * 2]},
            "camera": camera, "actions": actions, "effects": effects, "labels": labels,
            "start_time": start, "subject": plan["subject"]}


def accepted(plan: list[dict[str, Any]], times: list[tuple[float, float]], max_shots: int,
             max_seconds: float, catalog: dict | None = None) -> list[dict[str, Any]]:
    """Keep the shots that fit the budget. A bad shot is dropped, so it can never stop a video."""
    catalog = catalog or load()
    kept: list[dict[str, Any]] = []
    used, last_end = 0.0, -1.0
    for shot in sorted(plan, key=lambda s: s["first_line"]):
        first, last = shot["first_line"], shot["last_line"]
        if not (0 <= first <= last < len(times)) or shot["world"] not in catalog["worlds"]:
            continue
        start, end = times[first][0], min(times[last][1], times[first][0] + MAX_SHOT)
        length = end - start
        if length < MIN_SHOT or start < last_end or used + length > max_seconds or len(kept) >= max_shots:
            continue
        used += length
        last_end = end
        kept.append({**shot, "start": start, "end": end, "blueprint_name": slug(shot["subject"])})
    return kept


def save_shots(shots: list[dict[str, Any]], folder) -> list[str]:
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, shot in enumerate(shots):
        path = folder / f"shot-{index:02d}.json"
        path.write_text(json.dumps(shot, indent=2) + "\n", encoding="utf-8")
        paths.append(str(path))
    return paths
