"""Goli's talking sprites for the videos (assets/goli3d/video/<pose>/, rendered by tools/goli3d_video.py).

Per pose: the body in each weekday outfit with the mouth at rest, nine Rhubarb mouth patches and a blink patch,
all from one camera, so they stack exactly. `layer()` returns the HTML for one pose with ids the composer already
animates: {uid}-m<shape> (one mouth shown at a time) and {uid}-lid (the blink).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SPRITES = ROOT / "assets" / "goli3d" / "video"
SHAPES = "ABCDEFGHX"


@lru_cache(maxsize=None)
def meta(pose: str) -> dict | None:
    f = SPRITES / pose / "meta.json"
    return json.loads(f.read_text()) if f.exists() else None


# what the videos can ask for: every pose the editor, the intros/outros and the Stickman + Goli layer use,
# in every weekday outfit (tools/goli3d_video.py draws exactly these)
POSES = ("talk", "explain", "point", "point_up", "point_left", "shock", "think", "thumbs_up", "shrug", "point_both_up", "wave")
OUTFITS = ("royal", "ember", "emerald", "midnight", "violet", "sky", "crimson")


def missing_files() -> list[str]:
    out = []
    for p in POSES:
        d = SPRITES / p
        need = ["meta.json", "blink.webp"] + [f"body-{o}.webp" for o in OUTFITS] + [f"mouth-{s}.webp" for s in SHAPES]
        out += [f"{p}/{f}" for f in need if not (d / f).exists()]
    return out


def require() -> None:
    """Stop before any rendering if a sprite is missing (owner 2026-11-21: no fallbacks; nothing may fail late)."""
    missing = missing_files()
    if missing:
        raise FileNotFoundError(f"Goli 3D sprites missing ({len(missing)}): {missing[:5]}; run goli3d-library.yml kind=video")


def pose_name(pose: str) -> str:
    if pose not in POSES:
        raise ValueError(f"Goli has no 3D pose {pose!r}; poses: {', '.join(POSES)}")
    return pose


@lru_cache(maxsize=None)
def frame() -> tuple[float, float, float, float]:
    """One box around every pose (raised arms, pointing arms, feet), so poses swap without a jump."""
    boxes = [m["bbox"] for p in sorted(SPRITES.glob("*/meta.json")) if (m := meta(p.parent.name))]
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def aspect() -> float:
    x0, y0, x1, y1 = frame()
    return (x1 - x0) / (y1 - y0)


def waist(size: float) -> float:
    """Pixels from the top of the frame to his waist, at this height."""
    x0, y0, x1, y1 = frame()
    return (meta("talk")["waist"] - y0) * size / (y1 - y0)


@lru_cache(maxsize=None)
def _size(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size


def layer(pose: str, uid: str, outfit: str, size: float, asset) -> str:
    """The HTML for one pose: body, mouth patches (rest shown), blink patch (hidden). `asset` registers a file."""
    p = pose_name(pose)
    m = meta(p)
    x0, y0, _, y1 = frame()
    k = size / (y1 - y0)
    if outfit not in m["body"]:
        raise ValueError(f"Goli has no 3D outfit {outfit!r}; outfits: {', '.join(OUTFITS)}")

    def img(f: Path, xy, id_="", show=True) -> str:
        w, h = _size(f)
        idattr = f' id="{id_}"' if id_ else ""
        return (f'<img{idattr} src="{asset(f)}" style="position:absolute;left:{(xy[0] - x0) * k:.1f}px;'
                f'top:{(xy[1] - y0) * k:.1f}px;width:{w * k:.1f}px;height:{h * k:.1f}px;opacity:{1 if show else 0}">')

    d = SPRITES / p
    html = img(d / f"body-{outfit}.webp", m["body"][outfit])
    for s in SHAPES:
        html += img(d / f"mouth-{s}.webp", m["patches"][s], f"{uid}-m{s}", show=(s == "X"))
    from .kits import glasses
    g = glasses(outfit)
    if (d / f"blink-{g}.webp").exists():       # owner 2026-11-25: the day's glasses, and a half lid for a smooth blink
        html += img(d / f"half-{g}.webp", m["patches"][f"half-{g}"], f"{uid}-half", show=False)
        html += img(d / f"blink-{g}.webp", m["patches"][f"blink-{g}"], f"{uid}-lid", show=False)
    else:
        html += img(d / "blink.webp", m["patches"]["blink"], f"{uid}-lid", show=False)
    return html
