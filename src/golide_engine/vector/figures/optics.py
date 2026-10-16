"""Optics figures: thin-lens ray diagrams, reflection, refraction (Snell's law) and a prism."""

from __future__ import annotations

import math

from .core import DIM, GOLD, WHITE, Canvas, FigureError, fmt, new_canvas, num

# Visible colours from red to violet, with a crown-glass index for each.
RAINBOW = [((235, 64, 52), 1.513, "red"), ((245, 140, 40), 1.517, ""), ((245, 215, 60), 1.519, ""),
           ((80, 200, 90), 1.522, ""), ((60, 170, 230), 1.526, ""), ((80, 90, 225), 1.529, ""),
           ((155, 85, 215), 1.532, "violet")]


def lens(size, params, items) -> Canvas:
    """Object, lens, the two principal rays and the image they meet at (1/f = 1/u + 1/v)."""
    kind = params.get("type", "convex").lower()
    f = abs(num(params, "focal"))
    if kind.startswith("conc") or kind.startswith("diverg"):
        f = -f
    u, h = num(params, "object"), num(params, "height", 2.0)
    if u <= 0 or f == 0:
        raise FigureError("object distance and focal length must be set")
    if abs(u - f) < 1e-6:
        raise FigureError("object at the focal point makes no image")
    v = 1 / (1 / f - 1 / u)           # image distance (negative: same side, virtual)
    hi = -h * v / u                    # image height (negative: upside down)
    left = max(u, -v if v < 0 else 0, abs(f)) * 1.15
    tall = max(h, abs(hi)) * 1.5
    right = max(abs(f) * 2, v if v > 0 else abs(f) * 1.5) * 1.15
    # Ray diagrams are drawn taller than true scale (as in textbooks); straight
    # lines stay straight, so every crossing and the image stay exact.
    c = new_canvas(size, (-left, -tall, right, tall), stretch=True)
    c.seg((-left, 0), (right, 0), DIM, 0.7)                      # principal axis
    lh = tall * 0.85
    c.seg((0, -lh), (0, lh), WHITE, 1.3)
    tip = lh * 0.08
    for sgn in (1, -1):                                              # lens symbol
        y = sgn * lh
        if f > 0:
            c.pxline([c.p(-tip, y - sgn * tip), c.p(0, y), c.p(tip, y - sgn * tip)], WHITE, 1.1)
        else:
            c.pxline([c.p(-tip, y + sgn * tip), c.p(0, y), c.p(tip, y + sgn * tip)], WHITE, 1.1)
    for x in (f, -f):
        c.dot(x, 0, WHITE)
    c.label(abs(f), 0, "F", DIM, small=True, anchor="mt", dy=c.line * 5)
    c.label(-abs(f), 0, "F", DIM, small=True, anchor="mt", dy=c.line * 5)
    c.arrow((-u, 0), (-u, h), WHITE, 1.3)                            # object
    c.label(-u, h, "object", WHITE, small=True, anchor="mb", dy=-c.line * 5)
    image = (v, hi)

    def until_edge(y0: float, slope: float) -> float:
        """How far right a ray from (0, y0) may run before it leaves the frame."""
        if abs(slope) < 1e-9:
            return right
        limit = (tall if slope > 0 else -tall) * 0.95
        return max(0.0, min(right, (limit - y0) / slope))

    # Ray 1: parallel to the axis, then through (or away from) the focal point.
    c.seg((-u, h), (0, h), WHITE, 1.0)
    x1 = until_edge(h, -h / f)
    c.seg((0, h), (x1, h - h / f * x1), WHITE, 1.0)
    # Ray 2: straight through the centre of the lens.
    x2 = until_edge(0.0, -h / u)
    c.seg((-u, h), (x2, -h / u * x2), WHITE, 1.0)
    if v < 0:  # virtual image: traced back, the rays seem to come from it
        c.dashed((0, h), image, DIM, 0.8)
        c.dashed((0, 0), image, DIM, 0.8)
    c.arrow((v, 0), image, GOLD, 1.6)
    real = "real, upside down" if v > 0 else "virtual, upright"
    # Labels sit below the axis, clear of the rays: under an inverted image, or
    # low down for an upright (virtual) one.
    y = hi if hi < 0 else -tall * 0.55
    c.label(v, y, f"image {fmt(abs(v))} from the lens", GOLD, small=True, anchor="mt", dy=c.line * 6)
    c.label(v, y, f"{real}, ×{fmt(abs(hi / h))}", GOLD, small=True, anchor="mt", dy=c.line * 22)
    c.label(0, lh, f"f = {fmt(f)}", WHITE, small=True, anchor="mb", dy=-c.line * 5)
    return c


def reflection(size, params, items) -> Canvas:
    """A ray on a flat mirror: the angle in equals the angle out."""
    deg = num(params, "angle")
    if not 0 < deg < 90:
        raise FigureError("angle to the normal must be between 0 and 90")
    th = math.radians(deg)
    c = new_canvas(size, (-2.2, -0.6, 2.2, 2.3))
    c.seg((-2, 0), (2, 0), WHITE, 1.4)
    for k in range(10):
        x = -1.9 + k * 0.42
        c.seg((x, 0), (x - 0.14, -0.16), DIM, 0.6)
    c.dashed((0, 0), (0, 2.0), DIM, 0.8)
    c.label(0, 2.0, "normal", DIM, small=True, anchor="mb", dy=-c.line * 4)
    length = 2.0
    start = (-length * math.sin(th), length * math.cos(th))
    c.arrow(start, (0, 0), WHITE, 1.3)
    c.arc((0, 0), 0.6, 90, 90 + deg, WHITE, 0.8)
    c.label(-0.75 * math.sin(th / 2), 0.75 * math.cos(th / 2), f"{fmt(deg)}°", WHITE, small=True)
    c.arrow((0, 0), (length * math.sin(th), length * math.cos(th)), GOLD, 1.6)
    c.arc((0, 0), 0.6, 90 - deg, 90, GOLD, 0.8)
    c.label(0.75 * math.sin(th / 2), 0.75 * math.cos(th / 2), f"{fmt(deg)}°", GOLD, small=True)
    return c


def refraction(size, params, items) -> Canvas:
    """Snell's law at a boundary: n₁ sin θ₁ = n₂ sin θ₂ (or total internal reflection)."""
    n1, n2, deg = num(params, "n1", 1.0), num(params, "n2", 1.5), num(params, "angle")
    if n1 <= 0 or n2 <= 0 or not 0 <= deg < 90:
        raise FigureError("indices must be positive and the angle between 0 and 90")
    th1 = math.radians(deg)
    c = new_canvas(size, (-2.3, -2.3, 2.3, 2.3))
    c.seg((-2.2, 0), (2.2, 0), WHITE, 1.2)
    c.dashed((0, -2.0), (0, 2.0), DIM, 0.8)
    c.label(-2.1, 0.15, f"n = {fmt(n1)}", DIM, small=True, anchor="lb")
    c.label(-2.1, -0.15, f"n = {fmt(n2)}", DIM, small=True, anchor="lt")
    length = 2.0
    c.arrow((-length * math.sin(th1), length * math.cos(th1)), (0, 0), WHITE, 1.3)
    c.arc((0, 0), 0.55, 90, 90 + deg, WHITE, 0.8)
    c.label(-0.72 * math.sin(th1 / 2), 0.72 * math.cos(th1 / 2), f"{fmt(deg, 1)}°", WHITE, small=True)
    s = n1 * math.sin(th1) / n2
    if s > 1:  # total internal reflection
        c.arrow((0, 0), (length * math.sin(th1), length * math.cos(th1)), GOLD, 1.6)
        critical = math.degrees(math.asin(n2 / n1))
        c.label(1.1, 1.9, "total internal reflection", GOLD, small=True)
        c.label(1.1, 1.6, f"critical angle {fmt(critical, 1)}°", GOLD, small=True)
        return c
    th2 = math.asin(s)
    c.arrow((0, 0), (length * math.sin(th2), -length * math.cos(th2)), GOLD, 1.6)
    c.arc((0, 0), 0.55, -90, -90 + math.degrees(th2), GOLD, 0.8)
    c.label(0.75 * math.sin(th2 / 2), -0.75 * math.cos(th2 / 2), f"{fmt(math.degrees(th2), 1)}°", GOLD, small=True)
    c.dashed((0, 0), (length * math.sin(th1) * 0.8, -length * math.cos(th1) * 0.8), DIM, 0.6)
    return c


def _snell(direction, normal, n_in, n_out):
    """Refract a unit direction at a surface with unit normal (pointing against the ray)."""
    dx, dy = direction
    nx, ny = normal
    cos_i = -(dx * nx + dy * ny)
    ratio = n_in / n_out
    k = 1 - ratio * ratio * (1 - cos_i * cos_i)
    if k < 0:
        return None
    t = ratio * cos_i - math.sqrt(k)
    return ratio * dx + t * nx, ratio * dy + t * ny


def _hit(p, d, a, b):
    """Where the ray p + s d crosses segment a-b (s > 0), or None."""
    ex, ey = b[0] - a[0], b[1] - a[1]
    den = d[0] * ey - d[1] * ex
    if abs(den) < 1e-12:
        return None
    s = ((a[0] - p[0]) * ey - (a[1] - p[1]) * ex) / den
    u = ((a[0] - p[0]) * d[1] - (a[1] - p[1]) * d[0]) / den
    if s <= 1e-9 or not 0 <= u <= 1:
        return None
    return p[0] + s * d[0], p[1] + s * d[1]


def prism(size, params, items) -> Canvas:
    """White light split by a glass prism, traced with Snell's law per colour.

    The spread between colours is widened (``spread``, default 8x) so it can be
    seen; the order (red bends least, violet most) is the real one.
    """
    spread = num(params, "spread", 8.0)
    A, B, C = (-1.2, -0.9), (1.2, -0.9), (0.0, 1.18)
    c = new_canvas(size, (-3.2, -1.9, 3.4, 1.9))
    c.poly([A, B, C, A], WHITE, 1.3)
    start = (-3.0, -0.35)
    entry_dir = (math.cos(math.radians(14)), math.sin(math.radians(14)))
    entry = _hit(start, entry_dir, A, C)
    if entry is None:
        raise FigureError("beam misses the prism")
    c.seg(start, entry, WHITE, 1.6)
    c.label(-2.5, -0.35, "white light", WHITE, small=True, anchor="rt", dy=-c.line * 9)

    def unit_normal(a, b, inside):
        ex, ey = b[0] - a[0], b[1] - a[1]
        nx, ny = ey, -ex
        length = math.hypot(nx, ny)
        nx, ny = nx / length, ny / length
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if (inside[0] - mx) * nx + (inside[1] - my) * ny > 0:
            nx, ny = -nx, -ny
        return nx, ny

    centre = ((A[0] + B[0] + C[0]) / 3, (A[1] + B[1] + C[1]) / 3)
    n_left = unit_normal(A, C, centre)
    n_right = unit_normal(C, B, centre)
    mean = sum(n for _, n, _ in RAINBOW) / len(RAINBOW)
    for rgb, index, name in RAINBOW:
        n = mean + (index - mean) * spread
        inside = _snell(entry_dir, n_left, 1.0, n)
        if inside is None:
            continue
        exit_pt = _hit(entry, inside, C, B)
        if exit_pt is None:
            continue
        c.seg(entry, exit_pt, (min(255, rgb[0] // 2 + 120), min(255, rgb[1] // 2 + 120), min(255, rgb[2] // 2 + 120)), 0.6)
        out = _snell(inside, (-n_right[0], -n_right[1]), n, 1.0)
        if out is None:
            continue
        end = (exit_pt[0] + out[0] * 2.2, exit_pt[1] + out[1] * 2.2)
        c.seg(exit_pt, end, rgb, 1.4)
        if name:
            c.label(end[0], end[1], name, rgb, small=True, anchor="lm", dx=c.line * 4)
    c.label(0.1, -1.55, "violet bends most, red least", DIM, small=True)
    return c
