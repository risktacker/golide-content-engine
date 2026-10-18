"""Label placement for exact figures: no text ever touches a line or another text
(owner direction 2026-10-18: "There should never be a collision of objects and
texts or texts and texts. Let there be order").

Builders ask for a label near a point. Once every stroke is known, each label in
turn is moved to the nearest free spot around where it was asked for: free of
every drawn line (with a margin) and of every label already placed, and inside
the canvas. Moving labels after the drawing is complete is what makes this
work for every figure kind without each builder having to plan its own space.
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

GRID = 4            # occupancy is kept at 1/GRID of the canvas resolution
MARGIN = 0.9        # gap kept around text, in line widths
RINGS = 40          # how far a label may travel, in steps


def occupancy(size: tuple[int, int], strokes: list[dict], scale: float, line: float) -> np.ndarray:
    """A boolean mask of everything the pen draws (at 1/GRID resolution)."""
    w, h = size[0] // GRID + 1, size[1] // GRID + 1
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    for stroke in strokes:
        pts = [(x * scale / GRID, y * scale / GRID) for x, y in stroke["points"]]
        width = max(1, round((stroke["width"] * scale + line * MARGIN * 2) / GRID))
        if len(pts) >= 2:
            draw.line(pts, fill=255, width=width, joint="curve")
    return np.asarray(mask) > 0


def _cells(box: tuple[float, float, float, float], shape) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    return (max(0, int(x0 // GRID)), max(0, int(y0 // GRID)),
            min(shape[1], int(math.ceil(x1 / GRID)) + 1), min(shape[0], int(math.ceil(y1 / GRID)) + 1))


def place(mask: np.ndarray, box: tuple[float, float, float, float], size: tuple[int, int],
          step: float) -> tuple[float, float]:
    """The (dx, dy) that moves ``box`` to the nearest free, in-canvas spot, and marks it taken."""
    w, h = size
    bw, bh = box[2] - box[0], box[3] - box[1]
    best, best_hit = (0.0, 0.0), None
    for ring in range(RINGS + 1):
        n = 1 if ring == 0 else 8 + ring * 4
        for k in range(n):
            angle = math.tau * k / n
            dx, dy = ring * step * math.cos(angle), ring * step * 0.8 * math.sin(angle)
            x0, y0 = box[0] + dx, box[1] + dy
            if x0 < 0 or y0 < 0 or x0 + bw > w or y0 + bh > h:
                continue
            c0, r0, c1, r1 = _cells((x0, y0, x0 + bw, y0 + bh), mask.shape)
            hit = int(mask[r0:r1, c0:c1].sum())
            if hit == 0:
                best, best_hit = (dx, dy), 0
                break
            if best_hit is None or hit < best_hit:
                best, best_hit = (dx, dy), hit
        if best_hit == 0:
            break
    x0, y0 = box[0] + best[0], box[1] + best[1]
    c0, r0, c1, r1 = _cells((x0, y0, x0 + bw, y0 + bh), mask.shape)
    mask[r0:r1, c0:c1] = True      # later labels keep clear of this one
    return best
