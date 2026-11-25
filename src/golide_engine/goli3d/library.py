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
POSES = ("talk", "point_left", "point", "point_up", "thumbs_up", "shock", "point_both_up", "wave", "shrug", "think",
         "explain", "facepalm")


def expression(name: str | None) -> str:
    name = (name or "neutral").strip().lower()
    name = OLD_FACES.get(name, name)
    return name if name in EXPRESSIONS else "neutral"


def path(pose: str = "talk", expr: str | None = None, outfit: str | None = None) -> Path:
    """The library file for this pose and reaction. Owner 2026-11-21: no stand-ins; a gap is an error.
    Owner 2026-11-25: in the day's kit (hoodie and glasses, goli3d/kits.py) once that kit is rendered."""
    e = expression(expr)
    if pose not in POSES:
        raise ValueError(f"Goli has no 3D pose {pose!r}; poses: {', '.join(POSES)}")
    if outfit is None:
        from .kits import today
        outfit = today()
    kit = LIBRARY / "kits" / outfit / pose / f"{e}.png"
    if kit.exists():
        return kit
    f = LIBRARY / pose / f"{e}.png"
    if not f.exists():
        raise FileNotFoundError(f"Goli 3D library is missing {pose}/{e}.png; run goli3d-library.yml kind=library")
    return f


def missing_files() -> list[str]:
    return [f"{p}/{e}.png" for p in POSES for e in EXPRESSIONS if not (LIBRARY / p / f"{e}.png").exists()]


def available() -> dict[str, list[str]]:
    return {d.name: sorted(f.stem for f in d.glob("*.png")) for d in sorted(LIBRARY.glob("*")) if d.is_dir()}
