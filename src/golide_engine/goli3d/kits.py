"""Goli's closet (owner 2026-11-25: "he isn't changing, even on thumbnails, including glasses").

One kit per weekday: the hoodie colour (edit/mascot.py WEEK) and a glasses style from the 3D model's five. The same
kit dresses him in the day's video (goli3d/video sprites) and on its thumbnail (goli3d/full/kits/<outfit>/).
"""
from __future__ import annotations

KITS = {
    "royal": "round_gold",        # Monday
    "ember": "aviator",           # Tuesday
    "emerald": "browline",        # Wednesday
    "midnight": "square_black",   # Thursday
    "violet": "round_silver",     # Friday
    "sky": "aviator",             # Saturday
    "crimson": "browline",        # Sunday
}


def glasses(outfit: str) -> str:
    return KITS.get(outfit, "round_gold")


def today() -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from ..edit.mascot import outfit_for
    return outfit_for(datetime.now(ZoneInfo("Africa/Lusaka")).date())
