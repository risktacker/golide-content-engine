"""What the engine learns from every 3D Short (owner 2026-11-24: "how do we let the engine learn to write such
storyboards?").

The Ricks Clips kits keep a lessons file: after every film the mistakes are written down and the next film reads them.
Here it is automatic and free. After a render, the free repairs (board.repair notes), the sentence coverage
(board.coverage) and the director's report (assets/shorts3d/scene.js: stations stepped or dropped, shots kept with
problems, people walking through things) are turned into GENERAL rules, never a topic, a thing id or a place, and
counted in R2 (shorts3d-lessons/lessons.json). The next storyboard call reads the most frequent and most recent ones
(board.instructions(lessons)). A lesson that stops happening fades: it drops out after LAPSE films without a repeat.
"""
from __future__ import annotations

import json
import re
from typing import Any

KEY = "shorts3d-lessons/lessons.json"
SHOW = 12          # lessons Sol reads
LAPSE = 8          # films without a repeat before a lesson is retired

# measured mistake -> the general rule Sol reads (pattern over the note, report line or coverage entry)
RULES: list[tuple[str, str, str]] = [
    ("station-inside", r"camera is inside",
     "A camera station stood inside a thing. Before writing cam, check it is outside every thing's footprint (its spot "
     "plus half its size) by at least 1 m, and above the ground."),
    ("station-hidden", r"is hidden behind|blocked",
     "A station's subject was hidden behind a thing. The straight line from cam to aim must cross nothing taller than "
     "the aim point; put the near-lens prop to one side of that line, not on it."),
    ("station-out", r"out of the shot",
     "A station's aim missed its subject. Aim at the subject's own spot and height (a face about 1.3 m, hands about "
     "0.9 m, a thing at half its height), and frame the ids the aim is on."),
    ("cut-by-camera", r"cut by the camera",
     "The camera stood so close that a person was cut by the lens. Keep a station at least 1.2 m from any person."),
    ("face-hidden", r"the face of|back to the camera",
     "A face shot did not show the face. For a face, stand the camera in front of where the person faces (their "
     "turn), 1.5 to 2.5 m away, at face height, mm 50 to 85."),
    ("too-small", r"too small",
     "The subject was too small in its picture. A wide picture still needs its subject at least a tenth of the frame "
     "height: a big place is shown from closer or with the subject near the lens."),
    ("staging", r"passes through",
     "People walked or stood through things. Walk targets (to) go around things, never across them, and people stand "
     "at least 0.6 m from a thing's edge."),
    ("cropped", r"cropped at the frame edge",
     "A person or label was cut by the frame edge. Keep what a picture is about inside its middle: aim between the "
     "framed ids, and for several people use a wider lens or step the camera back."),
    ("under-captions", r"under the captions|heads of .* overlap",
     "Heads sat under the captions or on top of each other. The lower third of the phone picture holds the captions: "
     "aim a little below the faces so heads sit in the upper two thirds, and stand people so their heads do not line up "
     "from the camera."),
    ("walk-nowhere", r"had nowhere to go",
     "A walk, run or sneak had no to spot and no target. Every one needs to [x, z] or a target id."),
    ("hands-empty", r"had nothing to",
     "A throw, kick, give, hold, use or put-down had nothing in the hands. Every one needs with = the thing's id, and "
     "a pick-up of that thing on an earlier word."),
    ("ride-nothing", r"nothing to ride",
     "A ride had no thing to ride. ride needs target = the vehicle or animal's id."),
    ("unknown-frame", r"framed nothing known",
     "A landing framed ids that were never defined. frame lists only ids from things and cast."),
    ("no-spot", r"had no spot",
     "A thing had no spot. Every thing needs at [x, z] inside the world's size."),
    ("move-nowhere", r"move at word .* had nowhere",
     "A thing's move had no to and no path. Every move needs to [x, z] or a path of spots."),
    ("too-close-shots", r"under .*s, merged|under the minimum",
     "Two landings were under 1 second apart and were merged. Keep landings at least 1.2 s apart."),
    ("sentence-short", r"^sentence-short",
     "A sentence got fewer pictures than it needed. Every sentence gets the number of pictures it is given, each a "
     "plan row and a landing on that sentence's words, the chain of action shown link by link."),
    ("plan-unbuilt", r"^plan-unbuilt",
     "Plan rows had no landing. Every plan row is built as a landing on its landing word."),
]


def observe(notes: list[str], report: dict | None, cover: list[dict], board: dict | None = None) -> list[str]:
    """The lesson keys this film shows (each counted once per film)."""
    lines = list(notes)
    rep = report or {}
    for s in rep.get("shots") or []:
        lines += [str(q) for q in (s.get("found") or [])] if s.get("station_dropped") or s.get("kept_with") else []
        lines += [str(q) for q in (s.get("station_dropped") or [])]
        if s.get("station_moved"):
            lines.append("camera is inside a thing (stepped out)")
    lines += [str(q) for q in rep.get("staging") or []]
    for c in cover:
        if c.get("short"):
            lines.append("sentence-short")
    if board is not None and len(board.get("plan") or []) > len(board.get("shots") or []) + 1:
        lines.append("plan-unbuilt")
    found = []
    for key, pat, _ in RULES:
        if any(re.search(pat, ln, re.I) for ln in lines) and key not in found:
            found.append(key)
    return found


def update(store: dict | None, keys: list[str]) -> dict:
    """Count this film's lessons in the store (a dict saved as JSON)."""
    st = json.loads(json.dumps(store or {"films": 0, "lessons": {}}))
    st["films"] = int(st.get("films", 0)) + 1
    for k in keys:
        e = st["lessons"].setdefault(k, {"count": 0, "last": 0})
        e["count"] += 1
        e["last"] = st["films"]
    for k in list(st["lessons"]):
        if st["films"] - st["lessons"][k]["last"] >= LAPSE:
            del st["lessons"][k]
    return st


def for_sol(store: dict | None) -> list[str]:
    """The rules Sol reads: most frequent first, then most recent; at most SHOW."""
    text = {k: t for k, _, t in RULES}
    ls = (store or {}).get("lessons") or {}
    keys = sorted((k for k in ls if k in text), key=lambda k: (-ls[k]["count"], -ls[k]["last"]))[:SHOW]
    return [f"{text[k]} (seen on {ls[k]['count']} film{'s' if ls[k]['count'] != 1 else ''})" for k in keys]


def load(r2) -> dict | None:
    """The saved lessons, or None (no store, nothing yet)."""
    if r2 is None:
        return None
    try:
        import urllib.request
        with urllib.request.urlopen(r2.resolve(f"r2://{KEY}", expires_seconds=600), timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - no lessons yet
        return None


def save(r2, store: dict) -> None:
    if r2 is not None:
        r2.put_object(KEY, json.dumps(store, indent=1).encode("utf-8"), "application/json")


def learn(r2, notes: list[str], report: dict | None, cover: list[dict], board: dict | None = None) -> dict[str, Any]:
    """After a film: observe, count, save. Never stops a video."""
    keys = observe(notes, report, cover, board)
    st = update(load(r2), keys)
    try:
        save(r2, st)
    except Exception as error:  # noqa: BLE001 - the video goes on; next film learns again
        print(json.dumps({"status": "shorts3d_lessons_not_saved", "error": str(error)[:200]}))
    return {"learned": keys, "films": st["films"]}
