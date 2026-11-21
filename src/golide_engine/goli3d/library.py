"""Pick Goli renders from the 3D library (assets/goli3d/full/<pose>/<expression>.png).

The library is rendered once with model.py (Blender) and reused for every thumbnail and video. A caller asks for
a pose and an expression; the old SVG names still work (pose "shock", faces "sure", "skeptic"...).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIBRARY = ROOT / "assets" / "goli3d" / "full"

EXPRESSIONS = ("neutral happy laughing excited angry determined surprised astonished scared disappointed crying shy "
               "trying_hard thinking confused smug sleepy hungry in_love savage").split()
# the old flat Goli's faces -> the 3D reactions
OLD_FACES = {"sure": "smug", "shock": "astonished", "think": "thinking", "skeptic": "confused", "happy": "excited",
             "neutral": "neutral"}
# when a pose was not drawn with that reaction, the nearest one that was
NEAR = {
    "smug": ["determined", "happy", "neutral"], "excited": ["happy", "laughing", "astonished"],
    "happy": ["excited", "smug", "neutral"], "astonished": ["surprised", "scared", "excited"],
    "surprised": ["astonished", "excited"], "scared": ["astonished", "surprised"],
    "angry": ["determined", "trying_hard"], "determined": ["smug", "angry"], "thinking": ["confused", "smug"],
    "confused": ["thinking", "disappointed"], "disappointed": ["confused", "crying"], "crying": ["disappointed"],
    "laughing": ["excited", "happy"], "in_love": ["excited", "happy"], "hungry": ["excited", "happy"],
    "savage": ["determined", "smug"], "trying_hard": ["determined"], "shy": ["happy"], "sleepy": ["neutral"],
    "neutral": ["smug", "happy"],
}


def expression(name: str | None) -> str:
    name = (name or "neutral").strip().lower()
    name = OLD_FACES.get(name, name)
    return name if name in EXPRESSIONS else "neutral"


def path(pose: str = "talk", expr: str | None = None) -> Path:
    """The library file for this pose and reaction (nearest reaction, then the talking pose, if not drawn)."""
    e = expression(expr)
    pose = pose if (LIBRARY / pose).is_dir() else "talk"
    for p in (pose, "talk"):
        for cand in [e] + NEAR.get(e, []) + ["neutral"]:
            f = LIBRARY / p / f"{cand}.png"
            if f.exists():
                return f
    raise FileNotFoundError(f"Goli 3D library is empty at {LIBRARY}")


def available() -> dict[str, list[str]]:
    return {d.name: sorted(f.stem for f in d.glob("*.png")) for d in sorted(LIBRARY.glob("*")) if d.is_dir()}
