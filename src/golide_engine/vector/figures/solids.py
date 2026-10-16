"""3D shapes: cube, cuboid, cylinder, cone, sphere and square pyramid, with volume and surface area."""

from __future__ import annotations

import math

from .core import DIM, GOLD, WHITE, Canvas, FigureError, fmt, new_canvas, num

# Oblique projection: depth runs up and to the right at half scale.
DEPTH = (0.5 * math.cos(math.radians(35)), 0.5 * math.sin(math.radians(35)))


def _p(x: float, y: float, z: float) -> tuple[float, float]:
    return x + z * DEPTH[0] * 2, y + z * DEPTH[1] * 2


def _box(c: Canvas, l: float, h: float, w: float) -> None:
    v = {(i, j, k): _p(i * l, j * h, k * w) for i in (0, 1) for j in (0, 1) for k in (0, 1)}
    hidden = {((0, 0, 0), (0, 0, 1)), ((0, 0, 1), (1, 0, 1)), ((0, 0, 1), (0, 1, 1))}
    for a in v:
        for b in v:
            if a < b and sum(x != y for x, y in zip(a, b)) == 1:
                (c.dashed if (a, b) in hidden else c.seg)(v[a], v[b], DIM if (a, b) in hidden else WHITE,
                                                         0.8 if (a, b) in hidden else 1.2)
    c.label(l / 2, 0, f"{fmt(l)}", WHITE, small=True, anchor="mt", dy=c.line * 5)
    c.label(0, h / 2, f"{fmt(h)}", WHITE, small=True, anchor="rm", dx=-c.line * 5)
    end = _p(l, 0, w)
    c.label((l + end[0]) / 2, end[1] / 2, f"{fmt(w)}", WHITE, small=True, anchor="lt", dx=c.line * 5)


def _ellipse(cx, cy, rx, ry, a0=0, a1=360):
    steps = 72
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * k / steps)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * k / steps))) for k in range(steps + 1)]


def solid(size, params, items) -> Canvas:
    shape = params.get("shape", items[0] if items else "cube").strip().lower()
    unit = params.get("unit", "cm")
    if shape in ("cube", "cuboid", "box"):
        a = num(params, "a", 0) or num(params, "length", 0)
        l = a if shape == "cube" else num(params, "length", a or 1)
        h = a if shape == "cube" else num(params, "height", a or 1)
        w = a if shape == "cube" else num(params, "width", a or 1)
        if min(l, h, w) <= 0:
            raise FigureError("box sides must be positive")
        end = _p(l, h, w)
        c = new_canvas(size, (-0.6 * l, -0.5 * h, end[0] + 1.9 * l, end[1] + 0.3 * h))
        _box(c, l, h, w)
        volume, area = l * h * w, 2 * (l * h + l * w + h * w)
        side = (end[0] + 0.3 * l, end[1] / 2)
    elif shape in ("cylinder", "cone"):
        r, h = num(params, "radius"), num(params, "height")
        if r <= 0 or h <= 0:
            raise FigureError("radius and height must be positive")
        ry = r * 0.32
        c = new_canvas(size, (-r * 1.4, -ry - 0.3 * h, r * 3.6, h + 0.4 * h))
        c.poly(_ellipse(0, 0, r, ry, 180, 360), WHITE, 1.2)          # front of the base
        back = _ellipse(0, 0, r, ry, 0, 180)
        for k in range(0, len(back) - 1, 2):
            c.seg(back[k], back[k + 1], DIM, 0.8)                     # hidden back of the base
        if shape == "cylinder":
            c.seg((-r, 0), (-r, h), WHITE, 1.2)
            c.seg((r, 0), (r, h), WHITE, 1.2)
            c.poly(_ellipse(0, h, r, ry), WHITE, 1.2)
            volume, area = math.pi * r * r * h, 2 * math.pi * r * (r + h)
        else:
            c.seg((-r, 0), (0, h), WHITE, 1.2)
            c.seg((r, 0), (0, h), WHITE, 1.2)
            volume, area = math.pi * r * r * h / 3, math.pi * r * (r + math.hypot(r, h))
        c.dashed((0, 0), (r, 0), DIM, 0.8)
        c.label(r / 2, 0, f"r = {fmt(r)}", WHITE, small=True, anchor="mb", dy=-c.line * 3)
        c.dashed((0, 0), (0, h), DIM, 0.8)
        c.label(0, h / 2, f"h = {fmt(h)}", WHITE, small=True, anchor="lm", dx=c.line * 5)
        side = (r * 1.15, h / 2)
    elif shape == "sphere":
        r = num(params, "radius")
        if r <= 0:
            raise FigureError("radius must be positive")
        c = new_canvas(size, (-r * 1.4, -r * 1.4, r * 3.6, r * 1.4))
        c.circle((0, 0), r, WHITE, 1.3)
        c.poly(_ellipse(0, 0, r, r * 0.3, 180, 360), WHITE, 1.0)
        back = _ellipse(0, 0, r, r * 0.3, 0, 180)
        for k in range(0, len(back) - 1, 2):
            c.seg(back[k], back[k + 1], DIM, 0.8)
        c.dashed((0, 0), (r, 0), DIM, 0.8)
        c.label(r / 2, 0, f"r = {fmt(r)}", WHITE, small=True, anchor="mb", dy=-c.line * 3)
        volume, area = 4 / 3 * math.pi * r ** 3, 4 * math.pi * r * r
        side = (r * 1.15, 0)
    elif shape == "pyramid":
        a, h = num(params, "a"), num(params, "height")
        if a <= 0 or h <= 0:
            raise FigureError("base side and height must be positive")
        base = {(i, k): _p(i * a, 0, k * a) for i in (0, 1) for k in (0, 1)}
        apex = _p(a / 2, h, a / 2)
        end = _p(a, 0, a)
        c = new_canvas(size, (-0.6 * a, -0.5 * h, end[0] + 2.0 * a, apex[1] + 0.3 * h))
        c.seg(base[(0, 0)], base[(1, 0)], WHITE, 1.2)
        c.seg(base[(1, 0)], base[(1, 1)], WHITE, 1.2)
        c.dashed(base[(0, 0)], base[(0, 1)], DIM, 0.8)
        c.dashed(base[(0, 1)], base[(1, 1)], DIM, 0.8)
        for key in base:
            (c.dashed if key == (0, 1) else c.seg)(base[key], apex, DIM if key == (0, 1) else WHITE,
                                                   0.8 if key == (0, 1) else 1.2)
        c.dashed(_p(a / 2, 0, a / 2), apex, DIM, 0.8)
        c.label(a / 2, 0, f"{fmt(a)}", WHITE, small=True, anchor="mt", dy=c.line * 5)
        c.label(apex[0], (apex[1] + base[(0, 0)][1]) / 2, f"h = {fmt(h)}", WHITE, small=True, anchor="lm",
                dx=c.line * 6)
        slant = math.hypot(a / 2, h)
        volume, area = a * a * h / 3, a * a + 2 * a * slant
        side = (end[0] + 0.2 * a, apex[1] / 2)
    else:
        raise FigureError("shape is cube, cuboid, cylinder, cone, sphere or pyramid")
    c.label(*side, f"volume {fmt(volume, 2)} {unit}³", GOLD, small=True, anchor="lb", dx=c.line * 6)
    c.label(*side, f"surface {fmt(area, 2)} {unit}²", WHITE, small=True, anchor="lt", dx=c.line * 6, dy=c.line * 3)
    return c
