"""Relativity figures: the light clock (time dilation) and the Lorentz factor curve."""

from __future__ import annotations

import math

from .core import DIM, GOLD, WHITE, Canvas, FigureError, fmt, graph, new_canvas, num


def _gamma(params) -> tuple[float, float]:
    v = num(params, "speed")
    if v > 1.5:  # given in % of c
        v /= 100
    if not 0 < v < 1:
        raise FigureError("speed is a fraction of light speed between 0 and 1 (or a percentage)")
    return v, 1 / math.sqrt(1 - v * v)


def light_clock(size, params, items) -> Canvas:
    """One tick of a light clock at rest and the same clock moving at v: the path is γ times longer."""
    v, g = _gamma(params)
    L = 1.6
    shift = v * g * L          # how far the moving clock travels in half a tick
    c = new_canvas(size, (-1.3, -1.2, 2.4 + 2 * shift + 0.6, L + 1.0))
    # At rest: light goes straight up and back.
    for y in (0, L):
        c.seg((-0.4, y), (0.4, y), WHITE, 1.4)
    c.arrow((-0.08, 0.05), (-0.08, L - 0.05), GOLD, 1.3)
    c.arrow((0.08, L - 0.05), (0.08, 0.05), GOLD, 1.3)
    c.label(0, -0.25, "at rest: 1 tick", WHITE, small=True, anchor="mt")
    # Moving: the mirrors move right, so the same light runs a longer, slanted path.
    x0 = 2.0
    for k, x in enumerate((x0, x0 + shift, x0 + 2 * shift)):
        alpha = WHITE if k == 1 else DIM
        c.seg((x - 0.4, 0), (x + 0.4, 0), alpha, 1.2)
        c.seg((x - 0.4, L), (x + 0.4, L), alpha, 1.2)
    c.arrow((x0, 0.05), (x0 + shift, L - 0.05), GOLD, 1.5)
    c.arrow((x0 + shift, L - 0.05), (x0 + 2 * shift, 0.05), GOLD, 1.5)
    c.arrow((x0 - 0.2, -0.45), (x0 + 2 * shift + 0.2, -0.45), DIM, 0.8)
    c.label(x0 + shift, -0.5, f"moving at {fmt(v * 100, 1)}% of light speed", WHITE, small=True, anchor="mt",
            dy=c.line * 3)
    c.label(x0 + shift, L + 0.15, f"1 tick takes {fmt(g)}× longer", GOLD, small=True, anchor="mb")
    return c


def lorentz(size, params, items) -> Canvas:
    """γ = 1 / √(1 − v²/c²) against speed, with the given speed marked."""
    v, g = _gamma(params)
    top = max(4.0, min(10.0, g * 1.3))
    c = new_canvas(size, (-0.1, -0.6, 1.08, top * 1.1), stretch=True)
    graph(c, 0, 1.05, 0, top, "share of light speed", "time stretch")
    pts = []
    for i in range(300):
        s = 0.995 * i / 299
        gs = 1 / math.sqrt(1 - s * s)
        if gs > top:
            break
        pts.append((s, gs))
    c.poly(pts, WHITE, 1.3)
    c.dashed((1.0, 0), (1.0, top), DIM, 0.7)
    c.dashed((v, 0), (v, g), GOLD, 0.8)
    c.dashed((0, g), (v, g), GOLD, 0.8)
    c.dot(v, g, GOLD, 4.0)
    c.label(0.06, top * 0.82, f"at {fmt(v * 100, 1)}% of light speed,", GOLD, small=True, anchor="lm")
    c.label(0.06, top * 0.82, f"time runs {fmt(g)}× slower", GOLD, small=True, anchor="lm", dy=c.line * 16)
    return c
