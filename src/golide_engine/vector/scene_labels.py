"""Clean labels printed on a picture (owner direction 2026-10-20).

"BONDS" on a jar reads well only when it is sharp and sits on the jar. The image
model cannot write reliably (misspelt, warped letters that trace into scribbles),
so it draws an empty label panel and the word is typeset here: sharp, in the
scene's colour, on the glowing part, sized to fit it, and placed clear of every
line (the same placement the exact figures use). It appears once the pen has
drawn the picture.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont

MAX_CHARS = 18
FIT = 0.78          # share of the glowing part's width the word may fill
SIZE = (0.045, 0.085)  # word height as a share of the drawing's longest side: min, max
SHOW_AFTER = 0.92   # share of the pen's work after which the label fades in


def clean(text: str) -> str:
    return " ".join(str(text or "").upper().split())[:MAX_CHARS].strip()


def _surface(img: Image.Image):
    import cairo

    rgba = np.asarray(img, np.float32) / 255.0
    alpha = rgba[..., 3:4]
    bgra = np.concatenate([rgba[..., 2:3] * alpha, rgba[..., 1:2] * alpha, rgba[..., 0:1] * alpha, alpha], axis=2)
    data = bytearray((bgra * 255).astype(np.uint8).tobytes())
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, img.width, img.height, img.width * 4), data


def attach_label(drawing, text: str, rgb: tuple[int, int, int]) -> bool:
    """Add ``text`` to ``drawing.labels`` on its glowing part. False when there is nothing to print."""
    from ..theme import load_theme
    from .figures.placement import occupancy, place
    from .illustrate import accent_box

    word = clean(text)
    if not word or not drawing.strokes:
        return False
    x0, y0, x1, y1 = drawing.bbox
    longest = max(x1 - x0, y1 - y0, 1.0)
    target = accent_box(drawing) or drawing.bbox
    tx0, ty0, tx1, ty1 = target
    font_path = str(load_theme().font("bold"))
    probe = ImageDraw.Draw(Image.new("L", (4, 4)))
    size = int(longest * SIZE[1])
    while size > longest * SIZE[0]:
        font = ImageFont.truetype(font_path, size)
        bx0, by0, bx1, by1 = probe.textbbox((0, 0), word, font=font)
        if bx1 - bx0 <= max(tx1 - tx0, longest * 0.25) * FIT:
            break
        size -= 2
    font = ImageFont.truetype(font_path, max(10, size))
    bx0, by0, bx1, by1 = probe.textbbox((0, 0), word, font=font)
    w, h = bx1 - bx0, by1 - by0
    pad = max(3, int(h * 0.25))
    # Centre the word on the glowing part, then move it to the nearest spot clear of every line.
    cx, cy = (tx0 + tx1) / 2, (ty0 + ty1) / 2
    box = (cx - w / 2 - pad, cy - h / 2 - pad, cx + w / 2 + pad, cy + h / 2 + pad)
    size_px = (int(drawing.width), int(drawing.height))
    strokes = [{"points": s.points.tolist(), "width": s.width} for s in drawing.strokes]
    line = float(np.median([s.width for s in drawing.strokes]))
    mask = occupancy(size_px, strokes, 1.0, line)
    for _surface_item, lx, ly, _after, _keep in drawing.labels:  # labels already there stay clear too
        mask[int(ly) // 4:int(ly + 40) // 4, int(lx) // 4:int(lx + 120) // 4] = True
    dx, dy = place(mask, box, size_px, step=max(2.0, h * 0.3))
    crop = Image.new("RGBA", (int(w + pad * 2), int(h + pad * 2)), (0, 0, 0, 0))
    ImageDraw.Draw(crop).text((pad - bx0, pad - by0), word, font=font, fill=tuple(rgb) + (255,))
    surface, data = _surface(crop)
    lx, ly = box[0] + dx, box[1] + dy
    drawing.labels.append((surface, lx, ly, SHOW_AFTER, data))
    # The label is part of the picture: push-ins, zooms and the fit to the drawing area
    # keep it whole, exactly like the drawing's own lines (2026-10-20: "FUND" was cut).
    bx0, by0, bx1, by1 = drawing.bbox
    drawing.bbox = (min(bx0, lx), min(by0, ly), max(bx1, lx + crop.width), max(by1, ly + crop.height))
    return True
