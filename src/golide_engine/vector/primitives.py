"""The fixed visual vocabulary for GOLIDE Black videos.

Every scene in a script picks one of these by name (see
engine.content_rules.VISUAL_CUES). Each draws thin white/grey line art on
black with exactly one family of glowing accents, in a unit square
(-1..1 on both axes). ``gp`` is the group's progress (0..1): consecutive
script lines that share a visual keep building the same drawing instead of
cutting away.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable

import cairo

TAU = math.tau


def ease(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def seg(p: float, a: float, b: float) -> float:
    """Progress of ``p`` within the sub-range a..b, eased."""
    if b <= a:
        return 1.0 if p >= b else 0.0
    return ease((p - a) / (b - a))


@dataclass
class Draw:
    main: cairo.Context
    glow: cairo.Context
    gp: float
    k: int
    n: int
    t: float
    seed: int
    unit_px: float  # pixels per unit at full resolution
    colors: dict[str, tuple[float, float, float]]
    icons: tuple[str, ...] = ()  # topic drawings for this scene (see vector.icons)
    # Continuity between scenes: drawings already on screen are not redrawn.
    # carry maps a drawing name to the position it glides from (x, y, size),
    # or None once it has arrived; hide lists drawings this scene must skip.
    carry: dict | None = None
    hide: frozenset = frozenset()
    visual: str = ""
    span: float = 0.0  # length of the whole scene in seconds
    region: tuple = (-1.0, -1.0, 1.0, 1.0)  # where an illustration may sit (unit coords)
    zoom: float = 1.0  # extra scale used by the fade transition (drift in / out)
    words: int = 0      # spoken words in this scene (the pen keeps the voice's pace)
    hook: bool = False  # inside the opening hook window: quick pictures
    marking: float = 0.0  # 0..1 while a spoken number is on screen (zoom and ring on the accent)

    def px(self, value: float) -> float:
        return value / self.unit_px

    def _apply(self, ctx: cairo.Context, color: str, alpha: float) -> None:
        r, g, b = self.colors[color]
        ctx.set_source_rgba(r, g, b, alpha)

    def stroke(self, path: Callable[[cairo.Context], None], color: str = "line", width: float = 2.2,
               alpha: float = 1.0, hot: bool = False, dash: tuple[float, ...] | None = None) -> None:
        targets = [(self.main, width, alpha)]
        if hot:
            targets.append((self.glow, width * 2.6, min(1.0, alpha * 1.1)))
        for ctx, w, a in targets:
            ctx.save()
            ctx.new_path()
            path(ctx)
            self._apply(ctx, color, a)
            ctx.set_line_width(self.px(w))
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            if dash:
                ctx.set_dash([self.px(v) for v in dash])
            ctx.stroke()
            ctx.restore()

    def fill(self, path: Callable[[cairo.Context], None], color: str = "line", alpha: float = 1.0,
             hot: bool = False) -> None:
        targets = [self.main] + ([self.glow] if hot else [])
        for ctx in targets:
            ctx.save()
            ctx.new_path()
            path(ctx)
            self._apply(ctx, color, alpha)
            ctx.fill()
            ctx.restore()

    def dot(self, x: float, y: float, radius_px: float, color: str = "line", alpha: float = 1.0,
            hot: bool = False) -> None:
        r = self.px(radius_px)
        self.fill(lambda c: c.arc(x, y, r, 0, TAU), color, alpha, hot)
        if hot:
            self.glow.save()
            self._apply(self.glow, color, alpha * 0.8)
            self.glow.arc(x, y, r * 3.2, 0, TAU)
            self.glow.fill()
            self.glow.restore()

    def rng(self, salt: int = 0) -> random.Random:
        return random.Random(self.seed * 7919 + salt)


def _line(x1, y1, x2, y2):
    def path(c):
        c.move_to(x1, y1)
        c.line_to(x2, y2)
    return path


def _partial_polyline(points: list[tuple[float, float]], p: float):
    """Path that draws the first fraction ``p`` of a polyline."""
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    total = sum(lengths) or 1.0
    target = total * min(1.0, max(0.0, p))

    def path(c):
        c.move_to(*points[0])
        walked = 0.0
        for (a, b), length in zip(zip(points, points[1:]), lengths):
            if walked + length >= target:
                f = (target - walked) / length if length else 0
                c.line_to(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
                return
            c.line_to(*b)
            walked += length
    return path


def _point_at(points, p):
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    total = sum(lengths) or 1.0
    target = total * min(1.0, max(0.0, p))
    walked = 0.0
    for (a, b), length in zip(zip(points, points[1:]), lengths):
        if walked + length >= target:
            f = (target - walked) / length if length else 0
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        walked += length
    return points[-1]


def _frame(d: Draw, p: float = 1.0, alpha: float = 0.35) -> None:
    """Thin rounded card around the drawing area."""
    r = 0.08
    x0, y0, x1, y1 = -0.92, -0.92, 0.92, 0.92

    def path(c):
        c.new_sub_path()
        c.arc(x1 - r, y0 + r, r, -TAU / 4, 0)
        c.arc(x1 - r, y1 - r, r, 0, TAU / 4)
        c.arc(x0 + r, y1 - r, r, TAU / 4, TAU / 2)
        c.arc(x0 + r, y0 + r, r, TAU / 2, 3 * TAU / 4)
        c.close_path()
    d.stroke(path, "line_dim", 1.4, alpha=alpha * ease(p * 3))


# --------------------------------------------------------------------- shapes

def dot_field(d: Draw) -> None:
    rng = d.rng(1)
    count = 46
    hot = int(1 + d.gp * 5)
    for i in range(count):
        x, y = rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9)
        phase = rng.uniform(0, TAU)
        x += 0.02 * math.sin(d.t * 0.7 + phase)
        y += 0.02 * math.cos(d.t * 0.6 + phase)
        twinkle = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(d.t * 2.1 + phase))
        appear = seg(d.gp, i / count * 0.5, i / count * 0.5 + 0.2)
        is_hot = i % 9 == 0 and i // 9 < hot
        d.dot(x, y, 4.5 if is_hot else 3.2, "cyan" if is_hot else "line",
              alpha=appear * (1.0 if is_hot else twinkle), hot=is_hot)


def grid(d: Draw) -> None:
    rng = d.rng(2)
    cols, rows = 6, 7
    settle = seg(d.gp, 0.05, 0.6)
    for j in range(rows):
        y = -0.8 + 1.6 * j / (rows - 1)
        d.stroke(_line(-0.8, y, -0.8 + 1.6 * seg(d.gp, 0.4, 0.9), y), "line_dim", 1.0, alpha=0.6)
    for i in range(cols):
        x = -0.8 + 1.6 * i / (cols - 1)
        d.stroke(_line(x, -0.8, x, -0.8 + 1.6 * seg(d.gp, 0.4, 0.9)), "line_dim", 1.0, alpha=0.6)
    for j in range(rows):
        for i in range(cols):
            gx, gy = -0.8 + 1.6 * i / (cols - 1), -0.8 + 1.6 * j / (rows - 1)
            sx, sy = rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9)
            x, y = sx + (gx - sx) * settle, sy + (gy - sy) * settle
            center = (i, j) == (cols // 2, rows // 2)
            d.dot(x, y, 4.6 if center else 3.4, "gold" if center else "line",
                  hot=center and settle > 0.9)


def _levels(d: Draw, ladder: bool) -> None:
    steps = 7 if ladder else 6
    colors = ["red", "red", "gold", "gold", "cyan", "cyan", "white_glow"]
    pts = [(-0.85, 0.75)]
    for s in range(steps):
        x0 = -0.85 + 1.6 * s / steps
        y = 0.75 - 1.4 * (s + 1) / steps
        pts += [(x0, y), (x0 + 1.6 / steps, y)]
    draw = seg(d.gp, 0.0, 0.55)
    d.stroke(_partial_polyline(pts, draw), "line", 2.4)
    d.stroke(_line(-1.0, 0.75, 1.0, 0.75), "line", 1.6, alpha=0.8)
    reached = d.gp * steps
    for s in range(steps):
        x = -0.85 + 1.6 * (s + 0.5) / steps
        y = 0.75 - 1.4 * (s + 1) / steps - 0.12
        visible = seg(draw, s / steps, (s + 1) / steps)
        if ladder:
            color = colors[s % len(colors)]
            lit = reached >= s + 0.5
            d.stroke(lambda c, x=x, y=y: c.arc(x, y, d.px(16), 0, TAU), color, 1.6,
                     alpha=visible, dash=(4, 4), hot=lit)
            d.dot(x, y, 5, color, alpha=visible, hot=lit)
    if not ladder:
        climb = min(steps - 0.01, reached)
        s = int(climb)
        x = -0.85 + 1.6 * (s + (climb - s)) / steps
        y = 0.75 - 1.4 * (s + 1) / steps - d.px(10)
        d.dot(x, y, 7, "gold", alpha=seg(d.gp, 0.1, 0.3), hot=True)


def ladder(d: Draw) -> None:
    _levels(d, ladder=True)


def staircase(d: Draw) -> None:
    _levels(d, ladder=False)


def bar_chart(d: Draw) -> None:
    _frame(d, d.gp)
    bars = 6
    d.stroke(_line(-0.75, 0.7, 0.75, 0.7), "line", 1.6)
    for i in range(bars):
        h = 0.22 + 1.05 * (i + 1) / bars
        grow = seg(d.gp, 0.1 + i * 0.1, 0.35 + i * 0.1)
        x0 = -0.68 + i * 0.24
        top = 0.7 - h * grow
        last = i == bars - 1
        d.stroke(lambda c, x0=x0, top=top: c.rectangle(x0, top, 0.14, 0.7 - top), "gold", 2.0,
                 alpha=0.9, hot=last and grow > 0.95)
        d.fill(lambda c, x0=x0, top=top: c.rectangle(x0, top, 0.14, 0.7 - top), "gold", alpha=0.18)


def line_chart(d: Draw) -> None:
    d.stroke(_line(-0.8, 0.75, -0.8, -0.8), "line", 1.6)
    d.stroke(_line(-0.8, 0.75, 0.85, 0.75), "line", 1.6)
    pts = [(-0.8 + 1.6 * i / 20, 0.7 - 1.35 * (i / 20) ** 1.1 + 0.03 * math.sin(i * 1.7)) for i in range(21)]
    p = seg(d.gp, 0.05, 0.85)
    d.stroke(_partial_polyline(pts, p), "gold", 2.4, hot=True)
    x, y = _point_at(pts, p)
    d.dot(x, y, 6, "gold", alpha=1 if p > 0 else 0, hot=True)


def spike_vs_curve(d: Draw) -> None:
    d.stroke(_line(-0.9, 0.6, 0.9, 0.6), "line_dim", 1.4)
    spike_p = seg(d.gp, 0.0, 0.4)
    spike = [(-0.9 + 0.9 * i / 40, 0.6 - 1.25 * math.exp(-((i - 20) / 3.2) ** 2)) for i in range(41)]
    d.stroke(_partial_polyline(spike, spike_p), "cyan", 2.2, alpha=1 - 0.5 * seg(d.gp, 0.5, 0.8),
             hot=d.gp < 0.5)
    curve_p = seg(d.gp, 0.45, 1.0)
    curve = [(-0.9 + 1.8 * i / 40, 0.6 - 1.3 * (math.exp(2.2 * i / 40) - 1) / (math.exp(2.2) - 1)) for i in range(41)]
    d.stroke(_partial_polyline(curve, curve_p), "gold", 2.6, hot=True)
    if curve_p > 0:
        d.dot(*_point_at(curve, curve_p), 6, "gold", hot=True)


def _gear(d: Draw, cx, cy, r, teeth, angle, color, hot, alpha):
    def path(c):
        for i in range(teeth * 2 + 1):
            a = angle + i * TAU / (teeth * 2)
            rr = r * (1.0 if i % 2 == 0 else 0.84)
            x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
            (c.move_to if i == 0 else c.line_to)(x, y)
        c.close_path()
    d.stroke(path, color, 1.8, alpha=alpha, hot=hot)
    d.stroke(lambda c: c.arc(cx, cy, r * 0.45, 0, TAU), color, 1.2, alpha=alpha * 0.7)
    d.dot(cx, cy, 4, color, alpha=alpha, hot=hot)


def gears(d: Draw) -> None:
    spin = d.t * 0.6
    _gear(d, -0.1, 0.1, 0.48, 14, spin, "gold", True, seg(d.gp, 0, 0.3))
    _gear(d, 0.52, -0.35, 0.3, 10, -spin * 1.5 + 0.2, "line", False, seg(d.gp, 0.2, 0.5))
    _gear(d, 0.45, 0.62, 0.22, 8, -spin * 2.1, "line", False, seg(d.gp, 0.4, 0.7))


def ring_of_points(d: Draw) -> None:
    count = 18
    r = 0.78
    for i in range(count):
        a = -TAU / 4 + i * TAU / count
        vis = seg(d.gp, i / count * 0.6, i / count * 0.6 + 0.15)
        d.dot(r * math.cos(a), r * math.sin(a), 4, "cyan", alpha=vis, hot=vis > 0.9 and i % 3 == 0)
    sweep = seg(d.gp, 0.5, 1.0)
    if sweep > 0:
        d.stroke(lambda c: c.arc(0, 0, r, -TAU / 4, -TAU / 4 + TAU * sweep), "gold", 2.2, hot=True)
    d.dot(0, 0, 7 * seg(d.gp, 0.6, 0.9), "gold", hot=True)


def branching_tree(d: Draw) -> None:
    levels = 4
    nodes = [[(-0.85, 0.0)]]
    for level in range(1, levels + 1):
        x = -0.85 + 1.65 * level / levels
        count = 2 ** level
        span = min(1.7, 0.35 * count)
        nodes.append([(x, -span / 2 + span * (i + 0.5) / count) for i in range(count)])
    for level in range(1, levels + 1):
        p = seg(d.gp, (level - 1) / levels, level / levels)
        for i, (x, y) in enumerate(nodes[level]):
            px_, py_ = nodes[level - 1][i // 2]
            d.stroke(_line(px_, py_, px_ + (x - px_) * p, py_ + (y - py_) * p), "line", 1.4, alpha=0.8)
            last = level == levels
            d.dot(x, y, 4.5, "gold", alpha=p, hot=last and p > 0.9)
    d.dot(-0.85, 0.0, 6, "gold", hot=True)


def person_outline(d: Draw) -> None:
    head = (0.0, -0.42)
    body = [(-0.62, 0.9), (-0.6, 0.45), (-0.42, 0.18), (-0.14, 0.08), (-0.1, -0.12),
            (0.1, -0.12), (0.14, 0.08), (0.42, 0.18), (0.6, 0.45), (0.62, 0.9)]
    p = seg(d.gp, 0.0, 0.45)
    d.stroke(lambda c: c.arc(head[0], head[1], 0.2, TAU / 4, TAU / 4 + TAU * p), "line", 2.2)
    d.stroke(_partial_polyline(body, p), "line", 2.2)
    aura = seg(d.gp, 0.35, 1.0)
    for i in range(3):
        rr = 0.26 + 0.07 * i + 0.02 * math.sin(d.t * 2 + i)
        d.stroke(lambda c, rr=rr: c.arc(head[0], head[1], rr, -TAU * 0.42, -TAU * 0.08), "gold", 1.6,
                 alpha=aura * (0.9 - 0.25 * i), hot=i == 0)


def clock(d: Draw) -> None:
    r = 0.72
    d.stroke(lambda c: c.arc(0, 0, r * seg(d.gp, 0, 0.2) + 1e-4, 0, TAU), "line", 2.2)
    for i in range(12):
        a = i * TAU / 12
        vis = seg(d.gp, 0.1 + i * 0.02, 0.2 + i * 0.02)
        d.stroke(_line(0.88 * r * math.cos(a), 0.88 * r * math.sin(a), r * math.cos(a), r * math.sin(a)),
                 "line", 1.6, alpha=vis)
    hand = -TAU / 4 + TAU * (0.15 + d.gp * 0.85)
    d.stroke(_line(0, 0, 0.6 * math.cos(hand), 0.6 * math.sin(hand)), "gold", 2.6, hot=True)
    d.stroke(_line(0, 0, 0.38 * math.cos(-TAU / 4 + d.gp), 0.38 * math.sin(-TAU / 4 + d.gp)), "line", 2.6)
    d.dot(0, 0, 6, "gold", hot=True)


def gauge(d: Draw) -> None:
    r = 0.78
    start, end = math.pi, TAU
    d.stroke(lambda c: c.arc(0, 0.25, r, start, end), "line", 2.0, alpha=seg(d.gp, 0, 0.2))
    for i in range(11):
        a = start + (end - start) * i / 10
        d.stroke(_line(0.86 * r * math.cos(a), 0.25 + 0.86 * r * math.sin(a), r * math.cos(a),
                       0.25 + r * math.sin(a)), "line", 1.4, alpha=seg(d.gp, 0.1, 0.3))
    level = 0.82 * seg(d.gp, 0.2, 0.9)
    if level > 0:
        d.stroke(lambda c: c.arc(0, 0.25, r * 0.93, start, start + (end - start) * level), "gold", 4.0,
                 alpha=0.9, hot=True)
    a = start + (end - start) * level
    d.stroke(_line(0, 0.25, 0.68 * math.cos(a), 0.25 + 0.68 * math.sin(a)), "line", 2.6)
    d.dot(0, 0.25, 6, "gold", hot=True)


def seed_to_plant(d: Draw) -> None:
    d.stroke(_line(-1.0, 0.7, 1.0, 0.7), "line", 1.4, alpha=0.8)
    stalks = 5
    for i in range(stalks):
        x = -0.64 + 1.28 * i / (stalks - 1)
        d.dot(x, 0.7, 5, "gold", alpha=seg(d.gp, i * 0.05, i * 0.05 + 0.1), hot=True)
        grow = seg(d.gp, 0.25 + i * 0.05, 0.75 + i * 0.05)
        top = 0.7 - 1.1 * grow
        d.stroke(_line(x, 0.7, x, top), "line", 1.8)
        for g in range(int(grow * 7)):
            gy = top + 0.06 + g * 0.08
            if gy < 0.6:
                d.dot(x - 0.03, gy, 2.8, "gold", hot=g == 0)
                d.dot(x + 0.03, gy + 0.03, 2.8, "gold")


def cross_out(d: Draw) -> None:
    _frame(d, 1.0, 0.5)
    for i in range(4):
        y = -0.45 + 0.3 * i
        d.stroke(_line(-0.6, y, 0.6 - 0.25 * (i % 2), y), "line", 2.0, alpha=0.55)
    p1 = seg(d.gp, 0.3, 0.6)
    p2 = seg(d.gp, 0.55, 0.85)
    d.stroke(_line(-0.7, -0.7, -0.7 + 1.4 * p1, -0.7 + 1.4 * p1), "red", 3.6, alpha=1 if p1 else 0, hot=True)
    d.stroke(_line(0.7, -0.7, 0.7 - 1.4 * p2, -0.7 + 1.4 * p2), "red", 3.6, alpha=1 if p2 else 0, hot=True)


def checklist(d: Draw) -> None:
    rows = 4
    checked = d.gp * rows
    for i in range(rows):
        y = -0.6 + 0.4 * i
        vis = seg(d.gp, i * 0.08, i * 0.08 + 0.15)
        d.stroke(lambda c, y=y: c.rectangle(-0.7, y - 0.11, 0.22, 0.22), "line", 1.8, alpha=vis)
        d.stroke(_line(-0.32, y, 0.7 - 0.15 * (i % 2), y), "line_dim", 2.2, alpha=vis)
        tick = seg(checked, i + 0.3, i + 0.9)
        if tick > 0:
            pts = [(-0.66, y), (-0.6, y + 0.07), (-0.45, y - 0.1)]
            d.stroke(_partial_polyline(pts, tick), "gold", 3.0, hot=True)


def split_compare(d: Draw) -> None:
    d.stroke(_line(0, -0.85, 0, 0.85 * seg(d.gp, 0, 0.3) * 2 - 0.85), "line_dim", 1.4)
    left = seg(d.gp, 0.15, 0.5)
    right = seg(d.gp, 0.45, 0.95)
    d.stroke(_line(-0.85, 0.7, -0.15, 0.7), "line", 1.4)
    d.stroke(_line(0.15, 0.7, 0.85, 0.7), "line", 1.4)
    lh = 0.35 * left
    d.fill(lambda c: c.rectangle(-0.62, 0.7 - lh, 0.24, lh), "red", alpha=0.35)
    d.stroke(lambda c: c.rectangle(-0.62, 0.7 - lh, 0.24, lh), "red", 1.8, alpha=0.9 if left else 0)
    rh = 1.35 * right
    d.fill(lambda c: c.rectangle(0.38, 0.7 - rh, 0.24, rh), "gold", alpha=0.25)
    d.stroke(lambda c: c.rectangle(0.38, 0.7 - rh, 0.24, rh), "gold", 2.0, alpha=0.95 if right else 0,
             hot=right > 0.9)


def single_glow(d: Draw) -> None:
    for i in range(3):
        rr = 0.25 + 0.2 * i + 0.03 * math.sin(d.t * 1.4 + i)
        d.stroke(lambda c, rr=rr: c.arc(0, 0, rr, 0, TAU), "line_dim", 1.3,
                 alpha=seg(d.gp, i * 0.15, i * 0.15 + 0.3), dash=(5, 7))
    d.dot(0, 0, 9 + 2 * math.sin(d.t * 2.2), "gold", alpha=seg(d.gp, 0, 0.2), hot=True)


def logo_end(d: Draw) -> None:
    single_glow(d)


# ------------------------------------------------------------ topic drawings

def draw_icon(d: Draw, name: str, cx: float, cy: float, size: float, p: float,
              color: str = "line", hot: bool = False, width: float = 2.4, alpha: float = 1.0,
              pen: bool = False) -> None:
    """Draw a topic drawing (24x24 line icon) centred at cx,cy, revealed to p.

    ``pen`` adds the travelling light at the tip of the stroke while it draws,
    like the reference: a bright point leads every line onto the screen.
    """
    from .icons import polylines

    if p <= 0:
        return
    lines = polylines(name)
    if not lines:
        return
    scale = size / 24.0
    lengths = [sum(math.dist(a, b) for a, b in zip(pts, pts[1:])) for pts in lines]
    total = sum(lengths) or 1.0
    target = total * min(1.0, p)
    walked = 0.0
    tip = None
    for pts, length in zip(lines, lengths):
        if walked >= target:
            break
        local = min(1.0, (target - walked) / length) if length else 1.0
        walked += length
        mapped = [(cx + (x - 12) * scale, cy + (y - 12) * scale) for x, y in pts]
        d.stroke(_partial_polyline(mapped, local), color, width, alpha=alpha, hot=hot)
        if local < 1.0:
            tip = _point_at(mapped, local)
    if pen and tip is not None and p < 1.0:
        pen_light(d, tip[0], tip[1], alpha)


def pen_light(d: Draw, x: float, y: float, alpha: float = 1.0, color: str = "white_glow") -> None:
    """The bright travelling point that leads a stroke."""
    r = d.px(3.2)
    d.fill(lambda c: c.arc(x, y, r, 0, TAU), color, alpha=alpha)
    d.fill(lambda c: c.arc(x, y, r * 2.6, 0, TAU), "gold", alpha=0.9 * alpha, hot=True)


def _arrow(d: Draw, x1, y1, x2, y2, p, color="line_dim"):
    if p <= 0:
        return
    xe, ye = x1 + (x2 - x1) * p, y1 + (y2 - y1) * p
    d.stroke(_line(x1, y1, xe, ye), color, 1.6, alpha=0.9, dash=(5, 6))
    if p > 0.95:
        ang = math.atan2(y2 - y1, x2 - x1)
        for side in (-1, 1):
            a = ang + math.pi + side * 0.5
            d.stroke(_line(x2, y2, x2 + 0.06 * math.cos(a), y2 + 0.06 * math.sin(a)), color, 1.6)


def _halo(d: Draw, cx, cy, r, p, color="gold"):
    d.stroke(lambda c: c.arc(cx, cy, r, 0, TAU * min(1.0, p)), "line_dim", 1.2, alpha=0.7, dash=(4, 7))
    pulse = 0.5 + 0.5 * math.sin(d.t * 2.0)
    d.stroke(lambda c: c.arc(cx, cy, r * (1.08 + 0.03 * pulse), -TAU / 4, -TAU / 4 + TAU * 0.18 * p),
             color, 1.8, hot=True, alpha=0.9)


def _icons(d: Draw, minimum: int = 1) -> list[str]:
    names = list(d.icons) or ["sparkles"]
    while len(names) < minimum:
        names.append(names[-1])
    return names


@dataclass(frozen=True)
class Slot:
    """Where one drawing sits in a scene and when it is drawn (gp range)."""
    name: str
    x: float
    y: float
    size: float
    accent: str
    start: float
    end: float
    width: float = 2.4


def icon_slots(visual: str, icons: tuple[str, ...] | list[str]) -> list[Slot]:
    """The drawings of an icon scene and their places, in drawing order.

    Shared by the scene itself and by the transitions, so a drawing that
    appears in two consecutive scenes can glide from one place to the other
    instead of being wiped and redrawn.
    """
    names = list(icons) or ["sparkles"]
    if visual == "icon_hero":
        return [Slot(names[0], 0, 0, 1.15, "gold", 0.0, 0.75, 2.6)]
    if visual == "icon_pair":
        a, b = (names + names)[:2]
        return [Slot(a, -0.48, 0, 0.62, "cyan", 0.0, 0.45), Slot(b, 0.48, 0, 0.62, "gold", 0.45, 0.95)]
    if visual == "icon_flow":
        while len(names) < 3:
            names.append(names[-1])
        names = names[:4]
        count = len(names)
        out = []
        for i, name in enumerate(names):
            y = -0.62 + 1.24 * i / max(1, count - 1)
            out.append(Slot(name, 0, y, 0.42, "gold" if i == count - 1 else "cyan",
                            i / count, (i + 0.8) / count, 2.2))
        return out
    if visual == "icon_orbit":
        if len(names) < 2:
            names.append(names[0])
        center, around = names[0], names[1:5]
        out = [Slot(center, 0, 0, 0.6, "gold", 0.0, 0.4)]
        for i, name in enumerate(around):
            a = -TAU / 4 + TAU * i / len(around)
            out.append(Slot(name, 0.72 * math.cos(a), 0.72 * math.sin(a), 0.3, "cyan",
                            0.3 + 0.15 * i, 0.6 + 0.15 * i, 2.0))
        return out
    if visual == "icon_grid":
        cols, rows = 5, 6
        out = []
        for j in range(rows):
            for i in range(cols):
                idx = j * cols + i
                start = idx / (cols * rows) * 0.6
                out.append(Slot(names[0], -0.72 + 1.44 * i / (cols - 1), -0.8 + 1.6 * j / (rows - 1),
                                0.2, "line_dim", start, start + 0.2, 1.8))
        return out
    return []


def lead_slots(visual: str, icons) -> dict[str, Slot]:
    """The first slot of each distinct drawing: the ones that can carry over."""
    out: dict[str, Slot] = {}
    for slot in icon_slots(visual, icons):
        out.setdefault(slot.name, slot)
    return out


def _place(d: Draw, slot: Slot) -> tuple[float, float, float, float]:
    """Position, size and reveal of a slot, honouring carried drawings."""
    carry = d.carry or {}
    if slot.name in carry and lead_slots_cache(d).get(slot.name) == slot:
        start = carry[slot.name]
        if start is None:
            return slot.x, slot.y, slot.size, 1.0
        return start[0], start[1], start[2], 1.0
    return slot.x, slot.y, slot.size, seg(d.gp, slot.start, slot.end)


def lead_slots_cache(d: Draw) -> dict[str, Slot]:
    return lead_slots(_layout_name(d), d.icons)


def _layout_name(d: Draw) -> str:
    return d.visual or "icon_hero"


def _draw_slot(d: Draw, slot: Slot, accent_alpha: float = 0.55, breathe: float = 1.0) -> tuple[float, float, float, float]:
    x, y, size, p = _place(d, slot)
    if slot.name in d.hide and lead_slots_cache(d).get(slot.name) == slot:
        return x, y, size, p
    size *= breathe
    draw_icon(d, slot.name, x, y, size, p, "line", width=slot.width, pen=True)
    draw_icon(d, slot.name, x, y, size, p, slot.accent, hot=True, width=slot.width, alpha=accent_alpha)
    return x, y, size, p


def icon_hero(d: Draw) -> None:
    """One subject, large, drawn on, with a slow breathing glow."""
    d.visual = "icon_hero"
    slot = icon_slots("icon_hero", d.icons)[0]
    _halo(d, 0, 0, 0.78, seg(d.gp, 0, 0.5))
    _draw_slot(d, slot, breathe=1 + 0.015 * math.sin(d.t * 1.6))


def icon_pair(d: Draw) -> None:
    """Two subjects compared or connected: A on the left, B on the right."""
    d.visual = "icon_pair"
    a, b = icon_slots("icon_pair", d.icons)
    _draw_slot(d, a, 0.45)
    _arrow(d, -0.12, 0, 0.12, 0, seg(d.gp, 0.35, 0.55))
    _draw_slot(d, b, 0.6)


def icon_flow(d: Draw) -> None:
    """A process: each subject appears in turn, linked by arrows."""
    d.visual = "icon_flow"
    slots = icon_slots("icon_flow", d.icons)
    count = len(slots)
    for i, slot in enumerate(slots):
        _draw_slot(d, slot, 0.5)
        if i < count - 1:
            nxt = slots[i + 1]
            _arrow(d, 0, slot.y + 0.25, 0, nxt.y - 0.25, seg(d.gp, slot.end - 0.1 / count, nxt.start + 0.05))


def icon_orbit(d: Draw) -> None:
    """A central subject with related subjects around it, connected."""
    d.visual = "icon_orbit"
    slots = icon_slots("icon_orbit", d.icons)
    _draw_slot(d, slots[0], 0.6)
    for slot in slots[1:]:
        x, y, size, p = _place(d, slot)
        a = math.atan2(slot.y, slot.x)
        r0 = 0.38
        d.stroke(_line(r0 * math.cos(a), r0 * math.sin(a), r0 * math.cos(a) + (x - r0 * math.cos(a)) * p * 0.8,
                       r0 * math.sin(a) + (y - r0 * math.sin(a)) * p * 0.8), "line_dim", 1.2, dash=(3, 6))
        _draw_slot(d, slot, 0.45)


def icon_grid(d: Draw) -> None:
    """Scale: many copies of one subject; a few light up."""
    d.visual = "icon_grid"
    slots = icon_slots("icon_grid", d.icons)
    lit = set(d.rng(9).sample(range(len(slots)), 5))
    for idx, slot in enumerate(slots):
        x, y, size, p = _place(d, slot)
        if slot.name in d.hide and lead_slots_cache(d).get(slot.name) == slot:
            continue
        on = idx in lit and d.gp > 0.6
        draw_icon(d, slot.name, x, y, size, p, "gold" if on else "line_dim", hot=on, width=slot.width)


ICON_LAYOUTS = {"icon_hero", "icon_pair", "icon_flow", "icon_orbit", "icon_grid"}


def _illustration(d: Draw) -> None:
    from .illustrate import illustration
    illustration(d)


PRIMITIVES: dict[str, Callable[[Draw], None]] = {
    "illustration": _illustration,
    "icon_hero": icon_hero, "icon_pair": icon_pair, "icon_flow": icon_flow,
    "icon_orbit": icon_orbit, "icon_grid": icon_grid,
    "dot_field": dot_field, "grid": grid, "ladder": ladder, "staircase": staircase,
    "bar_chart": bar_chart, "line_chart": line_chart, "spike_vs_curve": spike_vs_curve,
    "gears": gears, "ring_of_points": ring_of_points, "branching_tree": branching_tree,
    "person_outline": person_outline, "clock": clock, "gauge": gauge,
    "seed_to_plant": seed_to_plant, "cross_out": cross_out, "checklist": checklist,
    "split_compare": split_compare, "single_glow": single_glow, "logo_end": logo_end,
}
