"""Maths figures: vectors, right triangles, functions (tangent, area), the unit circle."""

from __future__ import annotations

import math

from .core import DIM, GOLD, WHITE, Canvas, FigureError, axes, expr, fmt, new_canvas, pair, num, yes

def vectors(size, params, items) -> Canvas:
    a = pair(params, "a")
    b = pair(params, "b") if "b" in params else None
    total = (a[0] + b[0], a[1] + b[1]) if b else a
    show_sum = b is not None and (yes(params, "sum") or "sum" not in params)
    xs = [0, a[0]] + ([b[0], total[0]] if b else [])
    ys = [0, a[1]] + ([b[1], total[1]] if b else [])
    pad = 0.8
    x0, x1 = min(xs) - pad, max(xs) + pad
    y0, y1 = min(ys) - pad, max(ys) + pad
    c = new_canvas(size, (x0, y0, x1, y1))
    axes(c, x0, x1, y0, y1)
    names = [n.strip() for n in params.get("names", "a,b").split(",")] + ["b"]
    c.arrow((0, 0), a, WHITE, 1.2)
    c.side_label((0, 0), a, names[0], WHITE, away=1.0)
    if b:
        start = a if show_sum else (0, 0)
        end = (start[0] + b[0], start[1] + b[1])
        c.arrow(start, end, WHITE, 1.2)
        c.side_label(start, end, names[1], WHITE, away=1.0)
    if show_sum:
        c.arrow((0, 0), total, GOLD, 1.5)
        c.side_label((0, 0), total, f"{names[0]} + {names[1]}", GOLD, small=True, away=-1.4)
        c.label(total[0], total[1], f"({fmt(total[0])}, {fmt(total[1])})", GOLD, small=True,
                anchor="lb", dx=c.line * 6, dy=-c.line * 4)
        if yes(params, "length"):
            c.label(total[0], total[1], f"length {fmt(round(math.hypot(*total), 2))}", GOLD, small=True,
                    anchor="lt", dx=c.line * 6, dy=c.line * 4)
    elif not b:
        c.label(a[0], a[1], f"({fmt(a[0])}, {fmt(a[1])})", GOLD, small=True, anchor="lb",
                dx=c.line * 6, dy=-c.line * 4)
    return c


def right_triangle(size, params, items) -> Canvas:
    a, b = num(params, "a"), num(params, "b")
    if a <= 0 or b <= 0:
        raise FigureError("triangle sides must be positive")
    hyp = math.hypot(a, b)
    c = new_canvas(size, (-0.15 * a, -0.25 * b, a * 1.15, b * 1.12))
    A, B, C = (0, 0), (a, 0), (a, b)
    c.seg(A, B, WHITE, 1.2)
    c.seg(B, C, WHITE, 1.2)
    c.seg(C, A, GOLD, 1.5)
    box = min(a, b) * 0.12
    c.poly([(a - box, 0), (a - box, box), (a, box)], WHITE, 0.9)
    letters = yes(params, "letters")
    c.label(a / 2, 0, "a" if letters else fmt(a), WHITE, dy=c.line * 14)
    c.label(a, b / 2, "b" if letters else fmt(b), WHITE, dx=c.line * 14)
    c.label(a / 2, b / 2, "c" if letters else fmt(hyp), GOLD, dx=-c.line * 14, dy=-c.line * 10)
    if yes(params, "angle"):
        deg = math.degrees(math.atan2(b, a))
        r = min(a, b) * 0.28
        c.arc(A, r, 0, deg, WHITE, 0.9)
        c.label(r * 1.25 * math.cos(math.radians(deg / 2)), r * 1.25 * math.sin(math.radians(deg / 2)),
                f"{fmt(round(deg, 1))}°", WHITE, small=True, anchor="lm", dx=c.line * 3)
    if yes(params, "formula"):
        c.label(a * 0.5, -0.18 * b, "a² + b² = c²", GOLD, small=True)
    return c


def function(size, params, items) -> Canvas:
    f = expr(params.get("f", "x^2"))
    lo, hi = pair(params, "x") if "x" in params else (-3.0, 3.0)
    if hi <= lo:
        raise FigureError("x range must go low,high")
    n = 240
    xs = [lo + (hi - lo) * i / n for i in range(n + 1)]
    ys = []
    for x in xs:
        try:
            ys.append(f(x))
        except (ValueError, ZeroDivisionError, OverflowError):
            ys.append(float("nan"))
    good = [y for y in ys if math.isfinite(y)]
    if len(good) < n // 2:
        raise FigureError("function is undefined over most of the range")
    y_lo, y_hi = min(good + [0.0]), max(good + [0.0])
    if "y" in params:
        y_lo, y_hi = pair(params, "y")
    span_y = max(1e-6, y_hi - y_lo)
    pad_x, pad_y = (hi - lo) * 0.08, span_y * 0.1
    x0, x1 = min(lo, 0) - pad_x, max(hi, 0) + pad_x
    y0, y1 = y_lo - pad_y, y_hi + pad_y
    c = new_canvas(size, (x0, y0, x1, y1), stretch=True)
    _axes_stretched(c, x0, x1, y0, y1)
    key_gold = not ("tangent" in params or "area" in params)
    run: list[tuple[float, float]] = []
    for x, y in zip(xs, ys):
        if math.isfinite(y) and y0 - span_y <= y <= y1 + span_y:
            run.append((x, min(max(y, y0), y1)))
        elif run:
            c.poly(run, GOLD if key_gold else WHITE, 1.4)
            run = []
    if run:
        c.poly(run, GOLD if key_gold else WHITE, 1.4)
    if "area" in params:
        a0, a1 = pair(params, "area")
        k = 60
        ax = [a0 + (a1 - a0) * i / k for i in range(k + 1)]
        top = [(x, f(x)) for x in ax]
        c.poly([(a0, 0)] + top + [(a1, 0), (a0, 0)], GOLD, 1.2)
        for i in range(1, 12):  # hatching shows the region without a solid fill
            x = a0 + (a1 - a0) * i / 12
            c.seg((x, 0), (x, f(x)), GOLD, 0.5)
        integral = sum((f(ax[i]) + f(ax[i + 1])) / 2 * (ax[i + 1] - ax[i]) for i in range(k))
        mid = (a0 + a1) / 2
        c.label(mid, f(mid) / 2, f"area ≈ {fmt(round(integral, 2))}", GOLD, small=True, dy=-c.line * 2)
    if "tangent" in params:
        t = num(params, "tangent")
        h_ = 1e-4
        slope = (f(t + h_) - f(t - h_)) / (2 * h_)
        yt = f(t)
        half = (hi - lo) * 0.28
        if abs(slope) > 1e-9:  # keep the line inside the graph's height
            half = min(half, abs((y1 - yt) / slope) * 0.95, abs((yt - y0) / slope) * 0.95)
        c.seg((t - half, yt - slope * half), (t + half, yt + slope * half), GOLD, 1.3)
        px, py = c.p(t, yt)
        r = c.line * 3.2
        c.pxcircle(px, py, r, GOLD)
        c.label(t, yt, f"slope = {fmt(round(slope, 2))}", GOLD, small=True,
                anchor="lt" if slope > 0 else "lb", dx=c.line * 8, dy=c.line * (6 if slope > 0 else -6))
    label = params.get("label") or ("y = " + params.get("f", "x^2").replace("**", "^").replace("^2", "²"))
    c.label(hi, f(hi) if math.isfinite(f(hi)) else y1, label, WHITE, small=True, anchor="rb", dy=-c.line * 6)
    return c


def _axes_stretched(c: Canvas, x0, x1, y0, y1) -> None:
    c.arrow((x0, 0), (x1, 0), DIM, 0.8)
    if x0 <= 0 <= x1:
        c.arrow((0, y0), (0, y1), DIM, 0.8)


def unit_circle(size, params, items) -> Canvas:
    deg = num(params, "angle", 30)
    rad = math.radians(deg)
    wave = yes(params, "wave")
    R = 1.0
    shift, wx = 1.75, 0.55  # the wave starts right of the circle; x units per radian
    right = shift + 2 * math.pi * wx + 0.3 if wave else 1.45
    c = new_canvas(size, (-1.45, -1.4, right, 1.4))
    c.arrow((-1.3, 0), (right, 0), DIM, 0.8)
    c.arrow((0, -1.3), (0, 1.3), DIM, 0.8)
    c.arc((0, 0), R, 0, 360, WHITE, 1.1)
    px, py = R * math.cos(rad), R * math.sin(rad)
    c.seg((0, 0), (px, py), WHITE, 1.2)
    c.seg((0, 0), (px, 0), WHITE, 1.0)           # cos
    c.seg((px, 0), (px, py), GOLD, 1.5)          # sin, the key length
    c.arc((0, 0), 0.22, 0, deg, WHITE, 0.9)
    c.label(0.3 * math.cos(rad / 2), 0.3 * math.sin(rad / 2), f"{fmt(deg)}°", WHITE, small=True, anchor="lm",
            dx=c.line * 2)
    c.label(px / 2, 0, f"cos {fmt(math.cos(rad))}", WHITE, small=True, anchor="mt", dy=c.line * 7)
    if wave:
        pts = [(shift + wx * t, R * math.sin(t)) for t in [2 * math.pi * i / 180 for i in range(181)]]
        c.poly(pts, WHITE, 1.1)
        wxp = shift + wx * rad
        c.seg((px, py), (wxp, py), DIM, 0.6)
        c.seg((wxp, 0), (wxp, py), GOLD, 1.5)
        c.label(wxp, py, f"sin {fmt(math.sin(rad))}", GOLD, small=True, anchor="mb", dy=-c.line * 8)
    else:
        c.label(px, py / 2, f"sin {fmt(math.sin(rad))}", GOLD, small=True, anchor="lm", dx=c.line * 6)
    return c
