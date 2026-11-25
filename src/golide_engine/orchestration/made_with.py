"""What the engine really used for a video (owner 2026-11-25: "these buttons have to correspond with the backend").

Shown on the video's card in Studio next to what he chose, so a button that did nothing is seen the same day:
the video type, the styles that actually appear, the platforms it really went to, Goli's kit and what the doctor
fixed. Read only from the finished production's own files."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

NAMES = {"recipe_clip": "styles", "puppet_clip": "puppets", "object3d": "3D objects", "metaphor": "metaphors",
         "photo": "photos", "browser_shot": "pages", "source": "pages", "walkthrough": "steps on pages",
         "steps": "steps on pages", "terminal": "real runs", "logo_tiles": "logos", "stat_counter": "numbers",
         "quote_card": "quotes", "prompt_card": "prompts", "chapter_card": "chapter cards"}


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def made_with(spec: dict[str, Any], work: Path, platforms, reels: Any = None, long_social: Any = None) -> dict[str, Any]:
    edit = _read(work / "edit" / "edit-list.json")
    blocks: Counter = Counter()
    recipes: Counter = Counter()
    for sc in edit.get("scenes") or []:
        name = NAMES.get(sc.get("type"))
        if name:
            blocks[name] += 1
        if sc.get("type") == "recipe_clip":
            recipes[str((sc.get("data") or {}).get("recipe") or "")] += 1
    doctor = _read(work / "edit" / "doctor.json")
    fixed = [f["kind"] for r in (doctor.get("rounds") or [])[:-1] for f in r.get("found") or []]
    return {
        "style": str(spec.get("video_style") or "goli"),
        "chosen_looks": spec.get("looks"),
        "blocks": dict(blocks.most_common()),
        "recipes": {k: v for k, v in recipes.items() if k},
        "platforms": sorted(platforms or []),
        "kit": _read(work / "edit" / "kit.json").get("kit"),
        "doctor_fixed": dict(Counter(fixed)),
        "plan_misses": len(edit.get("plan_misses") or []),
    }
