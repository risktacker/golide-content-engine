"""Goli's closet (owner 2026-11-25: "each uploaded video he wears something else. That's the rotation.").

Seven kits, each a hoodie colour (edit/mascot.py WEEK) and a glasses style from the 3D model's five; every upload takes
the next kit after the last one used, so no two videos in a row (and none of the last six) look the same. The kit is
chosen once per production (edit/kit.json), kept in the production record ("kit") for the next pick, and dresses him
in the video (goli3d/video sprites) and on its thumbnail (goli3d/full/kits/<outfit>/).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROTATION = [("royal", "round_gold"), ("ember", "aviator"), ("emerald", "browline"), ("midnight", "square_black"),
            ("violet", "round_silver"), ("sky", "aviator"), ("crimson", "browline")]
KITS = dict(ROTATION)


def glasses(outfit: str) -> str:
    return KITS.get(outfit, "round_gold")


def next_kit(last: str | None) -> str:
    """The kit after `last` in the rotation (the first one when there is none)."""
    names = [o for o, _ in ROTATION]
    return names[(names.index(last) + 1) % len(names)] if last in names else names[0]


def current() -> str:
    """The kit of the production being made (set by choose); the first kit outside a production."""
    k = os.environ.get("GOLIDE_KIT", "")
    return k if k in KITS else ROTATION[0][0]


def choose(folder: Path, records: Path) -> str:
    """This production's kit, chosen once: the next after the last upload's (production records, newest first)."""
    f = folder / "kit.json"
    if f.exists():
        kit = json.loads(f.read_text(encoding="utf-8")).get("kit")
    else:
        used = []
        for path in records.glob("*.json"):
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            params = rec.get("generation_parameters") or {}
            if isinstance(params, dict) and params.get("kit") in KITS:
                used.append((str(rec.get("recorded_at", "")), params["kit"]))
        used.sort(reverse=True)
        kit = next_kit(used[0][1] if used else None)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"kit": kit}) + "\n", encoding="utf-8")
    os.environ["GOLIDE_KIT"] = kit
    return kit


def today() -> str:          # kept for older callers: the production's kit
    return current()
