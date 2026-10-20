"""Exact diagrams: networks, flows and trees (owner direction 2026-10-20).

"Networks, roots, maps... make them more defined and recognisable." A traced
sketch of a network is a tangle; these are built: clean rounded boxes with sharp
names, straight links, one node glowing, and the pen draws them link by link.

    network: hub=Public Benefit Fund; nodes=Stockholders, Board, Researchers, Public; glow=hub
    flow: steps=Shares, Fund, Grants, Public; glow=Fund
    tree: root=Anthropic; children=Fund, Board, Stockholders; glow=Fund
          (an item line "Fund > Research, Safety" adds a third level under one child)

Every layout is measured before anything is drawn: names shrink or wrap onto
two lines until no box overlaps another or leaves the frame. A diagram that
still cannot fit raises FigureError, and the scene falls back to its sketch.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .core import DIM, GOLD, WHITE, Canvas, FigureError, new_canvas

MAX_NODES = 7
MAX_NAME = 24
GAP = 0.06        # clear space between boxes (math units; the frame is 2 units tall)
EDGE = 0.04       # clear space to the frame


@dataclass
class Box:
    text: str
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    lines: tuple = ()
    small: bool = False
    glow: bool = False

    def overlaps(self, other: "Box") -> bool:
        return (abs(self.x - other.x) * 2 < self.w + other.w + GAP * 2
                and abs(self.y - other.y) * 2 < self.h + other.h + GAP * 2)


def _names(text: str) -> list[str]:
    return [n.strip()[:MAX_NAME] for n in str(text or "").replace(">", ",").split(",") if n.strip()]


def _canvas(size) -> tuple[Canvas, float]:
    aspect = size[0] / size[1]
    return new_canvas(size, (-aspect, -1.0, aspect, 1.0)), aspect


def _wrap(text: str) -> tuple[str, ...]:
    words = text.split()
    if len(words) < 2:
        return (text,)
    best = min(range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(" ".join(words[k:]))))
    return " ".join(words[:best]), " ".join(words[best:])


def _measure(c: Canvas, box: Box, style: int) -> None:
    """style 0: normal, 1: small, 2: small on two lines."""
    box.small = style >= 1
    box.lines = _wrap(box.text) if style == 2 else (box.text,)
    font = c.small if box.small else c.font
    widths, height = [], 0.0
    for line in box.lines:
        x0, y0, x1, y1 = c.draw.textbbox((0, 0), line, font=font)
        widths.append((x1 - x0) / c.scale)
        height = max(height, (y1 - y0) / c.scale)
    box.w = max(widths) + 0.16
    box.h = height * len(box.lines) * 1.25 + 0.12


def _fits(boxes: list[Box], aspect: float) -> bool:
    for i, a in enumerate(boxes):
        if abs(a.x) + a.w / 2 > aspect - EDGE or abs(a.y) + a.h / 2 > 1 - EDGE:
            return False
        if any(a.overlaps(b) for b in boxes[i + 1:]):
            return False
    return True


def _crosses(a: Box, b: Box, other: Box) -> bool:
    """Does the straight link a-b pass through ``other`` (with the usual gap)?"""
    x0, y0, x1, y1 = other.x - other.w / 2 - GAP, other.y - other.h / 2 - GAP, other.x + other.w / 2 + GAP, \
        other.y + other.h / 2 + GAP
    for k in range(1, 40):
        t = k / 40
        x, y = a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t
        if x0 < x < x1 and y0 < y < y1:
            return True
    return False


def _solve(c: Canvas, aspect: float, boxes: list[Box], arrangements):
    """Try normal, small, then wrapped names, each with every arrangement, until one fits:
    no box overlaps another or leaves the frame, and no straight link runs through a box.

    arrangements: (arrange(boxes), links) pairs; returns the arrange function used."""
    for style in (0, 1, 2):
        for box in boxes:
            _measure(c, box, style)
        for arrange, links in arrangements:
            arrange(boxes)
            if _fits(boxes, aspect) and not any(
                    _crosses(a, b, o) for a, b in links for o in boxes if o is not a and o is not b):
                return arrange
    raise FigureError("the diagram does not fit; use fewer or shorter names")


def _rounded(c: Canvas, b: Box, color, width: float) -> None:
    """A rounded rectangle as one smooth pen stroke (its corners turn gently)."""
    r = min(b.w, b.h) * 0.32
    pts = []
    for (ox, oy), start in (((b.x + b.w / 2 - r, b.y + b.h / 2 - r), 0), ((b.x - b.w / 2 + r, b.y + b.h / 2 - r), 90),
                            ((b.x - b.w / 2 + r, b.y - b.h / 2 + r), 180), ((b.x + b.w / 2 - r, b.y - b.h / 2 + r), 270)):
        for k in range(7):
            a = math.radians(start + 15 * k)
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    pts.append(pts[0])
    c.poly(pts, color, width)


def _draw_box(c: Canvas, b: Box) -> None:
    color = GOLD if b.glow else WHITE
    _rounded(c, b, color, 1.4 if b.glow else 1.1)
    step = (b.h - 0.12) / len(b.lines)
    for i, line in enumerate(b.lines):
        c.label(b.x, b.y + (len(b.lines) - 1) / 2 * step - i * step, line, color, small=b.small)


def _edge_point(b: Box, tx: float, ty: float) -> tuple[float, float]:
    """Where the line from the box centre toward (tx, ty) leaves the box (with a small gap)."""
    dx, dy = tx - b.x, ty - b.y
    if dx == 0 and dy == 0:
        return b.x, b.y
    sx = (b.w / 2) / abs(dx) if dx else math.inf
    sy = (b.h / 2) / abs(dy) if dy else math.inf
    s = min(sx, sy) + 0.03 / math.hypot(dx, dy)
    return b.x + dx * s, b.y + dy * s


def _link(c: Canvas, a: Box, b: Box, color=WHITE, arrow: bool = False) -> None:
    p, q = _edge_point(a, b.x, b.y), _edge_point(b, a.x, a.y)
    (c.arrow if arrow else c.seg)(p, q, color, 1.0)


def _is_glow(name: str, glow: str, index: int) -> bool:
    g = glow.strip().lower()
    return bool(g) and (g == name.lower() or g == str(index + 1))


# ------------------------------------------------------------------ network

def network(size, params, items) -> Canvas:
    hub_name = str(params.get("hub") or "").strip()[:MAX_NAME]
    names = _names(params.get("nodes", ""))[:MAX_NODES]
    if not hub_name or len(names) < 2:
        raise FigureError("network needs hub= and at least two nodes=")
    glow = str(params.get("glow") or "hub").strip()
    c, aspect = _canvas(size)
    hub_glow = glow.lower() in {"hub", hub_name.lower()}
    hub = Box(hub_name, glow=hub_glow)
    nodes = [Box(n, glow=not hub_glow and _is_glow(n, glow, i)) for i, n in enumerate(names)]

    def ring(boxes):
        hub.x = hub.y = 0.0
        wmax = max(b.w for b in nodes)
        hmax = max(b.h for b in nodes)
        rx = max(0.05, aspect - wmax / 2 - EDGE * 2)
        ry = max(0.05, 1 - hmax / 2 - EDGE * 2)
        # Portrait frames turn the ring so no node sits level with the hub.
        offset = math.pi / len(nodes) if aspect < 1 else 0.0
        for i, b in enumerate(nodes):
            a = math.pi / 2 - math.tau * i / len(nodes) - offset
            b.x, b.y = rx * math.cos(a), ry * math.sin(a)

    def outline(boxes):
        """Tall frames: the hub on top, the nodes listed below it off one spine."""
        hub.x, hub.y = -aspect + EDGE * 2 + hub.w / 2, 1 - EDGE * 2 - hub.h / 2
        step = (hub.y - hub.h / 2 - (-1 + EDGE * 2)) / len(nodes)
        for i, b in enumerate(nodes):
            b.x = -aspect + EDGE * 2 + 0.22 + b.w / 2
            b.y = hub.y - hub.h / 2 - step * (i + 0.5)

    used = _solve(c, aspect, [hub] + nodes, [(ring, [(hub, b) for b in nodes]), (outline, [])])
    if used is outline:
        _draw_box(c, hub)
        spine = hub.x - hub.w / 2 + 0.1
        for b in nodes:
            c.poly([(spine, hub.y - hub.h / 2), (spine, b.y), (b.x - b.w / 2 - 0.02, b.y)],
                   GOLD if (hub.glow or b.glow) else WHITE, 1.0)
            _draw_box(c, b)
        return c
    _draw_box(c, hub)
    for b in nodes:  # link first, so the pen runs out from the centre to each node
        _link(c, hub, b, GOLD if (hub.glow or b.glow) else WHITE)
        _draw_box(c, b)
    index = {b.text.lower(): b for b in nodes}
    for item in items:  # extra links between nodes: "Board - Public"
        if "-" in item:
            left, right = (s.strip().lower() for s in item.split("-", 1))
            if left in index and right in index:
                _link(c, index[left], index[right], DIM)
    return c


# ------------------------------------------------------------------ flow

def flow(size, params, items) -> Canvas:
    names = _names(params.get("steps", "") or ", ".join(items))[:6]
    if len(names) < 2:
        raise FigureError("flow needs at least two steps=")
    glow = str(params.get("glow") or "").strip()
    c, aspect = _canvas(size)
    boxes = [Box(n, glow=_is_glow(n, glow, i)) for i, n in enumerate(names)]

    def across(bs):
        total = sum(b.w for b in bs)
        space = (aspect * 2 - EDGE * 4 - total) / (len(bs) - 1)
        if space < 0.14:  # no room for an arrow between two boxes
            for b in bs:
                b.x = b.y = 0.0  # forces an overlap, so the next arrangement is tried
            return
        x = -aspect + EDGE * 2
        for b in bs:
            b.x, b.y = x + b.w / 2, 0.0
            x += b.w + space

    def down(bs):
        top = 1 - EDGE * 2 - bs[0].h / 2
        step = (top * 2) / (len(bs) - 1)
        for i, b in enumerate(bs):
            b.x, b.y = 0.0, top - step * i
        if step - max(b.h for b in bs) < 0.14:
            for b in bs:
                b.y = 0.0

    order = [across, down] if aspect >= 1.0 else [down, across]
    _solve(c, aspect, boxes, [(f, []) for f in order])
    for i, b in enumerate(boxes):
        if i:
            _link(c, boxes[i - 1], b, GOLD if b.glow else WHITE, arrow=True)
        _draw_box(c, b)
    return c


# ------------------------------------------------------------------ tree

def tree(size, params, items) -> Canvas:
    root_name = str(params.get("root") or "").strip()[:MAX_NAME]
    names = _names(params.get("children", ""))[:5]
    if not root_name or not names:
        raise FigureError("tree needs root= and children=")
    glow = str(params.get("glow") or "").strip()
    grand_names: dict[str, list[str]] = {}
    for item in items:
        if ">" in item:
            parent, _, kids = item.partition(">")
            if parent.strip().lower() in {n.lower() for n in names}:
                grand_names[parent.strip().lower()] = _names(kids)[:3]
    c, aspect = _canvas(size)
    root = Box(root_name, glow=glow.lower() in {"root", root_name.lower()})
    kids = [Box(n, glow=_is_glow(n, glow, i)) for i, n in enumerate(names)]
    grand = {k.text.lower(): [Box(g) for g in grand_names.get(k.text.lower(), [])] for k in kids}
    every = [root] + kids + [g for gs in grand.values() for g in gs]

    def branch(_bs):
        levels = 3 if any(grand.values()) else 2
        ys = [0.72, 0.0, -0.72] if levels == 3 else [0.5, -0.5]
        root.x, root.y = 0.0, ys[0]
        slot = (aspect * 2 - EDGE * 4) / len(kids)
        for i, k in enumerate(kids):
            k.x, k.y = -aspect + EDGE * 2 + slot * (i + 0.5), ys[1]
            gs = grand[k.text.lower()]
            if gs:
                # The grandchildren sit side by side under their parent, kept inside the frame.
                width = sum(g.w for g in gs) + GAP * 3 * (len(gs) - 1)
                start = min(max(k.x - width / 2, -aspect + EDGE * 2), aspect - EDGE * 2 - width)
                for g in gs:
                    g.x, g.y = start + g.w / 2, ys[2]
                    start += g.w + GAP * 3

    def outline(_bs):
        """An indented outline, read top to bottom (tall or narrow frames)."""
        rows = [root] + [b for k in kids for b in [k] + grand[k.text.lower()]]
        top = 1 - EDGE * 2 - root.h / 2
        bottom = -1 + EDGE * 2 + rows[-1].h / 2
        step = (top - bottom) / max(1, len(rows) - 1)
        left = -aspect + EDGE * 2
        for i, b in enumerate(rows):
            depth = 0 if b is root else 1 if b in kids else 2
            b.x, b.y = left + 0.18 * depth + b.w / 2, top - step * i

    order = [branch, outline] if aspect >= 1.0 else [outline, branch]
    across = _solve(c, aspect, every, [(f, []) for f in order]) is branch
    _draw_box(c, root)
    for k in kids:
        color = GOLD if k.glow else WHITE
        if across:
            mid = (root.y - root.h / 2 + k.y + k.h / 2) / 2
            c.poly([(root.x, root.y - root.h / 2), (root.x, mid), (k.x, mid), (k.x, k.y + k.h / 2)], color, 1.0)
        else:
            spine = root.x - root.w / 2 + 0.08
            c.poly([(spine, root.y - root.h / 2), (spine, k.y), (k.x - k.w / 2, k.y)], color, 1.0)
        _draw_box(c, k)
        for g in grand[k.text.lower()]:
            if across:
                mid = (k.y - k.h / 2 + g.y + g.h / 2) / 2
                c.poly([(k.x, k.y - k.h / 2), (k.x, mid), (g.x, mid), (g.x, g.y + g.h / 2)], DIM, 0.9)
            else:
                spine = k.x - k.w / 2 + 0.08
                c.poly([(spine, k.y - k.h / 2), (spine, g.y), (g.x - g.w / 2, g.y)], DIM, 0.9)
            _draw_box(c, g)
    return c
