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


def available() -> bool:
    return meta("talk") is not None


def pose_name(pose: str) -> str:
    return pose if meta(pose) else "talk"


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
    outfit = outfit if outfit in m["body"] else "royal"

    def img(f: Path, xy, id_="", show=True) -> str:
        w, h = _size(f)
        idattr = f' id="{id_}"' if id_ else ""
        return (f'<img{idattr} src="{asset(f)}" style="position:absolute;left:{(xy[0] - x0) * k:.1f}px;'
                f'top:{(xy[1] - y0) * k:.1f}px;width:{w * k:.1f}px;height:{h * k:.1f}px;opacity:{1 if show else 0}">')

    d = SPRITES / p
    html = img(d / f"body-{outfit}.webp", m["body"][outfit])
    for s in SHAPES:
        html += img(d / f"mouth-{s}.webp", m["patches"][s], f"{uid}-m{s}", show=(s == "X"))
    html += img(d / "blink.webp", m["patches"]["blink"], f"{uid}-lid", show=False)
    return html
