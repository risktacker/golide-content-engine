"""Mechanics figures: projectiles, beams, forces, motion graphs, Newton's second law, inclines."""

from __future__ import annotations

import math
import re

from .core import DIM, GOLD, WHITE, Canvas, FigureError, fmt, graph, new_canvas, num

def projectile(size, params, items) -> Canvas:
    v, deg = num(params, "speed"), num(params, "angle", 45)
    g = num(params, "g", 9.8)
    if v <= 0 or not 0 < deg < 90 or g <= 0:
        raise FigureError("projectile needs speed > 0 and 0 < angle < 90")
    rad = math.radians(deg)
    flight = 2 * v * math.sin(rad) / g
    reach = v * math.cos(rad) * flight
    peak = (v * math.sin(rad)) ** 2 / (2 * g)
    c = new_canvas(size, (-0.08 * reach, -0.18 * max(peak, reach * 0.3), reach * 1.08, peak * 1.3 + 0.1 * reach))
    c.seg((-0.04 * reach, 0), (reach * 1.04, 0), WHITE, 1.0)
    pts = []
    for i in range(121):
        t = flight * i / 120
        pts.append((v * math.cos(rad) * t, v * math.sin(rad) * t - g * t * t / 2))
    c.poly(pts, GOLD, 1.5)
    launch = reach * 0.16
    c.arrow((0, 0), (launch * math.cos(rad), launch * math.sin(rad)), WHITE, 1.2)
    c.arc((0, 0), launch * 0.45, 0, deg, WHITE, 0.8)
    c.label(launch * 0.55 * math.cos(rad / 2), launch * 0.55 * math.sin(rad / 2), f"{fmt(deg)}°", WHITE,
            small=True, anchor="lm", dx=c.line * 3)
    c.seg((reach / 2, 0), (reach / 2, peak), DIM, 0.6)
    c.label(reach / 2, peak, f"peak {fmt(round(peak, 1))} m", WHITE, small=True, dy=-c.line * 12)
    c.label(reach, 0, f"{fmt(round(reach, 1))} m", GOLD, small=True, dy=c.line * 14)
    c.label(launch * math.cos(rad), launch * math.sin(rad), f"{fmt(v)} m/s", WHITE, small=True,
            anchor="rb", dx=-c.line * 4, dy=-c.line * 4)
    return c


def beam(size, params, items) -> Canvas:
    length = num(params, "length", 6)
    load = num(params, "load", 10)
    at = num(params, "at", length / 2)
    if not 0 <= at <= length or length <= 0:
        raise FigureError("load position must be on the beam")
    r_right = load * at / length
    r_left = load - r_right
    unit = params.get("unit", "kN")
    c = new_canvas(size, (-0.12 * length, -0.42 * length, length * 1.12, 0.42 * length))
    t = length * 0.03
    c.poly([(0, 0), (length, 0), (length, t), (0, t), (0, 0)], WHITE, 1.2)
    s = length * 0.05
    c.poly([(0, 0), (-s, -1.6 * s), (s, -1.6 * s), (0, 0)], WHITE, 1.0)          # pin
    c.poly([(length, 0), (length - s, -1.4 * s), (length + s, -1.4 * s), (length, 0)], WHITE, 1.0)
    for k in (-0.6, 0, 0.6):                                                     # roller wheels
        cx, cy = c.p(length + k * s, -1.75 * s)
        r = s * 0.28 * c.scale
        c.pxcircle(cx, cy, r, WHITE)
    top = length * 0.3
    c.arrow((at, t + top), (at, t + length * 0.01), GOLD, 1.5)
    c.label(at, t + top, f"{fmt(load)} {unit}", GOLD, small=True, dy=-c.line * 10)
    for x, value in ((0, r_left), (length, r_right)):
        c.arrow((x, -length * 0.32), (x, -1.9 * s), WHITE, 1.1)
        c.label(x, -length * 0.32, f"{fmt(round(value, 2))} {unit}", WHITE, small=True, dy=c.line * 10)
    c.seg((0, -length * 0.08), (at, -length * 0.08), DIM, 0.5)
    c.label(at / 2, -length * 0.08, f"{fmt(at)} m", DIM, small=True, dy=c.line * 8)
    c.label(length * 0.8 if at < length * 0.6 else length * 0.2, t, f"{fmt(length)} m", DIM, small=True,
            dy=-c.line * 9)
    return c


def forces(size, params, items) -> Canvas:
    raw = items + [f"{v}" for k, v in params.items() if k.startswith("f")]
    forces: list[tuple[float, float]] = []
    for item in raw:
        m = re.fullmatch(r"\s*([\d.]+)\s*(?:n|kn)?\s*@\s*(-?[\d.]+)\s*°?\s*", item.lower())
        if m:
            forces.append((float(m.group(1)), float(m.group(2))))
    if not forces:
        raise FigureError("forces need items like 20@0; 15@120")
    unit = params.get("unit", "N")
    vecs = [(mag * math.cos(math.radians(a)), mag * math.sin(math.radians(a))) for mag, a in forces]
    rx, ry = sum(v[0] for v in vecs), sum(v[1] for v in vecs)
    reach = max([math.hypot(*v) for v in vecs] + [math.hypot(rx, ry), 1e-6])
    c = new_canvas(size, (-reach * 1.2, -reach * 1.2, reach * 1.2, reach * 1.2))
    box = reach * 0.12
    c.poly([(-box, -box), (box, -box), (box, box), (-box, box), (-box, -box)], WHITE, 1.1)
    for (mag, a), (vx, vy) in zip(forces, vecs):
        ux, uy = vx / mag, vy / mag
        c.arrow((ux * box, uy * box), (vx + ux * box, vy + uy * box), WHITE, 1.2)
        c.label(vx + ux * box * 2.4, vy + uy * box * 2.4, f"{fmt(mag)} {unit}", WHITE, small=True)
    net = math.hypot(rx, ry)
    if net > 1e-6:
        ux, uy = rx / net, ry / net
        c.arrow((ux * box, uy * box), (rx + ux * box, ry + uy * box), GOLD, 1.5)
        c.label(rx + ux * box * 2.6, ry + uy * box * 2.6,
                f"net {fmt(round(net, 1))} {unit} at {fmt(round(math.degrees(math.atan2(ry, rx)), 1))}°", GOLD,
                small=True)
    else:
        c.label(0, -box * 2.5, f"net = 0 {unit}", GOLD, small=True)
    return c


def _points(text: str) -> list[tuple[float, float]]:
    pts = []
    for chunk in re.split(r"\s+|;", text.strip()):
        if not chunk:
            continue
        parts = chunk.strip("()").split(",")
        if len(parts) != 2:
            raise FigureError(f"point {chunk!r} needs t,value")
        pts.append((float(parts[0]), float(parts[1])))
    if len(pts) < 2:
        raise FigureError("a motion graph needs at least two points")
    if any(b[0] <= a[0] for a, b in zip(pts, pts[1:])):
        raise FigureError("time must increase from point to point")
    return pts


def motion(size, params, items) -> Canvas:
    """Velocity-time (or position-time) graph: slopes and the distance are computed."""
    pts = _points(params.get("points", " ".join(items)))
    quantity = params.get("quantity", "velocity").lower()
    velocity = not quantity.startswith("pos")
    t0, t1 = 0.0, pts[-1][0]
    v_lo, v_hi = min(0.0, *(p[1] for p in pts)), max(0.0, *(p[1] for p in pts))
    span_t, span_v = t1 - t0, max(1e-6, v_hi - v_lo)
    c = new_canvas(size, (-0.08 * span_t, v_lo - 0.12 * span_v, t1 * 1.1, v_hi + 0.22 * span_v), stretch=True)
    graph(c, -0.02 * span_t, t1 * 1.08, v_lo - 0.05 * span_v, v_hi + 0.18 * span_v,
          "t (s)", "v (m/s)" if velocity else "x (m)")
    if velocity:  # the distance is the area under the line: hatch it, then compute it
        for (ta, va), (tb, vb) in zip(pts, pts[1:]):
            for k in range(1, 6):
                t = ta + (tb - ta) * k / 6
                c.seg((t, 0), (t, va + (vb - va) * k / 6), DIM, 0.45)
    c.poly(pts, GOLD, 1.5)
    unit = "m/s²" if velocity else "m/s"
    name = "a" if velocity else "v"
    for (ta, va), (tb, vb) in zip(pts, pts[1:]):
        slope = (vb - va) / (tb - ta)
        c.side_label((ta, va), (tb, vb), f"{name} = {fmt(slope)} {unit}", WHITE, small="tiny", away=-2.2)
    if velocity:
        area = sum((tb - ta) * (va + vb) / 2 for (ta, va), (tb, vb) in zip(pts, pts[1:]))
        c.label(t1 / 2, (v_hi + v_lo) * 0.4, f"distance = {fmt(area)} m", GOLD, small=True)
    return c


def newton(size, params, items) -> Canvas:
    """F = ma on a block: push, friction, and the acceleration they produce."""
    force, mass = num(params, "force"), num(params, "mass")
    friction = num(params, "friction", 0.0)
    if mass <= 0:
        raise FigureError("mass must be positive")
    net = force - friction
    accel = net / mass
    c = new_canvas(size, (-2.6, -0.9, 2.6, 2.4))
    c.seg((-2.4, 0), (2.4, 0), WHITE, 1.0)
    for k in range(12):  # ground hatching
        x = -2.3 + k * 0.4
        c.seg((x, 0), (x - 0.15, -0.15), DIM, 0.6)
    c.poly([(-0.6, 0), (0.6, 0), (0.6, 1.2), (-0.6, 1.2), (-0.6, 0)], WHITE, 1.2)
    c.label(0, 0.6, f"{fmt(mass)} kg", WHITE)
    biggest = max(abs(force), abs(friction), 1e-6)
    push = 1.5 * abs(force) / biggest
    c.arrow((-0.6 - push, 0.6), (-0.6, 0.6), GOLD, 1.5)
    c.label(-0.6 - push / 2, 0.6, f"F = {fmt(force)} N", GOLD, small=True, anchor="mb", dy=-c.line * 6)
    if friction:
        drag = 1.5 * abs(friction) / biggest
        c.arrow((-0.6, 0.15), (-0.6 - drag, 0.15), WHITE, 1.1)  # friction opposes the push
        c.label(-0.6 - drag / 2, 0.15, f"friction {fmt(friction)} N", WHITE, small=True, anchor="mt",
                dy=c.line * 8)
    c.arrow((-0.5, 1.6), (0.7 if accel >= 0 else -1.7, 1.6), WHITE, 1.1)
    c.label(0.1, 1.6, f"a = {fmt(net)} ÷ {fmt(mass)} = {fmt(accel)} m/s²", WHITE, small=True, anchor="mb",
            dy=-c.line * 6)
    return c


def incline(size, params, items) -> Canvas:
    """A block on a slope: its weight split along and across the slope."""
    deg, mass = num(params, "angle"), num(params, "mass", 1.0)
    g = num(params, "g", 9.8)
    if not 0 < deg < 80:
        raise FigureError("slope angle must be between 0 and 80 degrees")
    th = math.radians(deg)
    base = 4.0
    top = base * math.tan(th)
    c = new_canvas(size, (-0.6, -1.4, base + 0.8, top + 1.2))
    c.poly([(0, 0), (base, 0), (base, top), (0, 0)], WHITE, 1.1)
    c.arc((0, 0), 0.8, 0, deg, WHITE, 0.8)
    c.label(1.0 * math.cos(th / 2), 1.0 * math.sin(th / 2), f"{fmt(deg)}°", WHITE, small=True, anchor="lm")
    ux, uy = math.cos(th), math.sin(th)       # along the slope, up
    nx, ny = -math.sin(th), math.cos(th)      # out of the slope
    s0, side = base / math.cos(th) * 0.55, 0.7
    p0 = (ux * s0, uy * s0)
    corners = [p0, (p0[0] + ux * side, p0[1] + uy * side),
               (p0[0] + ux * side + nx * side, p0[1] + uy * side + ny * side),
               (p0[0] + nx * side, p0[1] + ny * side), p0]
    c.poly(corners, WHITE, 1.2)
    cx, cy = p0[0] + (ux + nx) * side / 2, p0[1] + (uy + ny) * side / 2
    weight = mass * g
    along, across = weight * math.sin(th), weight * math.cos(th)
    k = 1.6 / weight
    c.arrow((cx, cy), (cx, cy - weight * k), WHITE, 1.2)
    c.label(cx, cy - weight * k, f"weight {fmt(weight, 1)} N", WHITE, small=True, anchor="lt", dx=c.line * 3)
    c.arrow((cx, cy), (cx - ux * along * k, cy - uy * along * k), GOLD, 1.5)
    c.label(cx - ux * along * k, cy - uy * along * k, f"down the slope {fmt(along, 1)} N", GOLD, small=True,
            anchor="rm", dx=-c.line * 5)
    c.dashed((cx, cy), (cx - nx * across * k, cy - ny * across * k), WHITE, 1.0)
    c.label(cx - nx * across * k, cy - ny * across * k, f"into the slope {fmt(across, 1)} N", WHITE,
            small=True, anchor="lt", dx=c.line * 4, dy=c.line * 2)
    return c
