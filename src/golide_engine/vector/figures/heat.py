"""Thermodynamics figures: pressure-volume diagrams with the work done, and a heat engine."""

from __future__ import annotations

import math

from .core import DIM, GOLD, WHITE, Canvas, FigureError, fmt, graph, new_canvas, num


def pv(size, params, items) -> Canvas:
    """A gas process on a p-V diagram; the work is the area under the curve (kPa × L = J)."""
    process = params.get("process", "isothermal").lower()
    p1, v1 = num(params, "p1"), num(params, "v1")
    gamma = num(params, "gamma", 1.4)
    if p1 <= 0 or v1 <= 0:
        raise FigureError("pressure and volume must be positive")
    if process.startswith("isoch"):
        p2 = num(params, "p2")
        v2 = v1
        curve = [(v1, p1 + (p2 - p1) * i / 50) for i in range(51)]
        work = 0.0
    else:
        v2 = num(params, "v2")
        if v2 <= 0 or v2 == v1:
            raise FigureError("v2 must be positive and differ from v1")
        if process.startswith("isob"):
            pressure = lambda v: p1  # noqa: E731
            work = p1 * (v2 - v1)
        elif process.startswith("adia"):
            pressure = lambda v: p1 * (v1 / v) ** gamma  # noqa: E731
            work = (p1 * v1 - pressure(v2) * v2) / (gamma - 1)
        elif process.startswith("isoth"):
            pressure = lambda v: p1 * v1 / v  # noqa: E731
            work = p1 * v1 * math.log(v2 / v1)
        else:
            raise FigureError("process is isothermal, isobaric, isochoric or adiabatic")
        curve = [(v1 + (v2 - v1) * i / 80, pressure(v1 + (v2 - v1) * i / 80)) for i in range(81)]
        p2 = curve[-1][1]
    vmax = max(v1, v2) * 1.25
    pmax = max(p1, p2) * 1.3
    c = new_canvas(size, (-0.12 * vmax, -0.16 * pmax, vmax * 1.05, pmax * 1.1), stretch=True)
    graph(c, 0, vmax, 0, pmax, "V (L)", "p (kPa)")
    if work:
        for k in range(1, 12):
            v, p = curve[int(k * (len(curve) - 1) / 12)]
            c.seg((v, 0), (v, p), DIM, 0.45)
    c.poly(curve, GOLD, 1.6)
    for (v, p), name in ((curve[0], "A"), (curve[-1], "B")):
        c.dot(v, p, WHITE)
        c.label(v, p, name, WHITE, small=True, anchor="lb", dx=c.line * 4, dy=-c.line * 3)
    mid = curve[len(curve) // 2]
    label = f"work = {fmt(work, 1)} J" if work else "no volume change, no work"
    c.label(mid[0], mid[1] / 2 if work else pmax, label, GOLD, small=True)
    c.label(vmax * 0.98, pmax * 1.02, process, DIM, small=True, anchor="rb")
    return c


def heat_engine(size, params, items) -> Canvas:
    """Hot to cold through an engine; the best possible (Carnot) efficiency is 1 − T_cold / T_hot."""
    hot, cold = num(params, "hot"), num(params, "cold")
    heat = num(params, "heat", 1000.0)
    if not 0 < cold < hot:
        raise FigureError("temperatures are in kelvin with cold < hot")
    eff = 1 - cold / hot
    work = eff * heat
    waste = heat - work
    c = new_canvas(size, (-2.4, -2.6, 3.2, 2.6))
    c.poly([(-1.6, 1.4), (1.6, 1.4), (1.6, 2.3), (-1.6, 2.3), (-1.6, 1.4)], WHITE, 1.2)
    c.label(0, 1.85, f"hot {fmt(hot)} K", WHITE, small=True)
    c.poly([(-1.6, -2.3), (1.6, -2.3), (1.6, -1.4), (-1.6, -1.4), (-1.6, -2.3)], WHITE, 1.2)
    c.label(0, -1.85, f"cold {fmt(cold)} K", WHITE, small=True)
    c.circle((0, 0), 0.7, WHITE, 1.3)
    c.label(0, 0, "engine", WHITE, small=True)
    c.arrow((0, 1.4), (0, 0.72), WHITE, 1.3)
    c.label(0, 1.06, f"{fmt(heat)} J in", WHITE, small=True, anchor="lm", dx=c.line * 6)
    c.arrow((0, -0.72), (0, -1.4), WHITE, 1.1)
    c.label(0, -1.06, f"{fmt(waste)} J out", WHITE, small=True, anchor="lm", dx=c.line * 6)
    c.arrow((0.72, 0), (2.2, 0), GOLD, 1.6)
    c.label(2.2, 0, f"work {fmt(work)} J", GOLD, small=True, anchor="lm", dx=c.line * 4)
    c.label(1.45, -0.5, f"max efficiency {fmt(eff * 100, 1)}%", GOLD, small=True, anchor="lt")
    return c
