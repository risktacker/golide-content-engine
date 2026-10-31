"""How real devices are built (owner direction 2026-10-31).

"If you are showing the real product it has to be the real product; if you are showing the
mechanics behind it, it has to be the architecture behind it." These figures draw the
architecture from the research, in code: every part has its own place, nothing crosses,
each part is a solid coloured block that appears as the narration reaches it.

    layers: names=cover glass,polarizer,touch sensor,OLED,backplane; title=10+ layers
    fold: layers=6; bar=stuck
"""

from __future__ import annotations

import math

from .core import DIM, GOLD, WHITE, FigureError, new_canvas

# Colours of real layers by what they are (cool glass, coloured functional films, grey metal).
LAYER_COLOURS = [(120, 168, 196), (150, 190, 214), (150, 150, 140), (80, 92, 160), (64, 132, 124),
                 (176, 76, 122), (170, 136, 66), (110, 114, 124), (150, 154, 162), (96, 100, 110)]
METAL = (118, 122, 132)
BAR = (196, 160, 88)
ROSE = (240, 110, 100)


def _names(params, key="names"):
    names = [n.strip() for n in str(params.get(key, "")).split(",") if n.strip()]
    if not 2 <= len(names) <= 10:
        raise FigureError(f"{key}: give 2 to 10 names, separated by commas")
    return names


def layers(size, params, items):
    """An exploded stack: each layer a solid plate, top first, named beside it."""
    names = _names(params)
    n = len(names)
    w, d, gap = 6.0, 3.2, 1.7          # plate width, depth (drawn at an angle), spacing
    c = new_canvas(size, (-0.6, -0.6, 15.5, n * gap + 2.4))
    skew = (1.7, 0.95)                   # how the depth runs on screen
    for i, name in enumerate(names):
        y = (n - 1 - i) * gap + 0.4
        col = LAYER_COLOURS[i % len(LAYER_COLOURS)]
        a, b = (0.0, y), (w, y)
        e, f = (w + skew[0], y + skew[1]), (skew[0], y + skew[1])
        lip = 0.14
        c.panel([a, b, (b[0], b[1] - lip), (a[0], a[1] - lip)], tuple(int(v * 0.55) for v in col), WHITE, 0.8, 0.1)
        c.panel([a, b, e, f], col, WHITE, 0.9)
        c.label(w + skew[0] + 0.45, y + skew[1] * 0.5, name.upper(), WHITE, small="tiny", anchor="lm")
    title = str(params.get("title", "")).strip()
    if title:
        c.label(0.0, n * gap + 1.5, title.upper(), GOLD, small=True, anchor="lm")
    return c


def fold(size, params, items):
    """The hinge of a folding device, end view: two halves, the screen's layers bending in a
    loop between them, the centre support bar, gears, springs and the cable underneath."""
    count = int(float(params.get("layers", 6)))
    count = max(2, min(8, count))
    stuck = str(params.get("bar", "dropped")).strip().lower() in ("stuck", "up", "high")
    c = new_canvas(size, (-6.2, -5.4, 7.6, 7.0))
    ang = math.radians(26)
    length, thick, gap = 6.6, 0.55, 0.95

    def along(side, dist, off=0.0):
        """a point dist up the inner face of a half, off into the gap"""
        x0 = side * gap
        ux, uy = side * math.sin(ang), math.cos(ang)
        nx, ny = -side * math.cos(ang), math.sin(ang)
        return (x0 + ux * dist + nx * off, uy * dist + ny * off)

    for side in (-1, 1):                 # the two halves: solid metal slabs
        ux, uy = side * math.sin(ang), math.cos(ang)
        nx, ny = side * math.cos(ang), -math.sin(ang)
        x0 = side * gap
        q = [(x0, 0.0), (x0 + ux * length, uy * length),
             (x0 + ux * length + nx * thick, uy * length + ny * thick), (x0 + nx * thick, ny * thick)]
        c.panel(q, METAL, WHITE, 1.0)
    # the screen: each layer a coloured band down one face, round the loop and up the other
    r0 = 1.25
    for i in range(count):
        off = 0.08 + i * 0.075
        r = r0 - i * 0.075
        left = [along(-1, length - 0.3, off), along(-1, 0.25, off)]
        loop = [(r * math.cos(t), -0.35 + r * math.sin(t) * 0.95)
                for t in [math.pi + k * math.pi / 30 for k in range(31)]]
        right = [along(1, 0.25, off), along(1, length - 0.3, off)]
        c.poly(left + loop + right, LAYER_COLOURS[i % len(LAYER_COLOURS)], 1.5)
    c.label(along(1, length * 0.62, 0.3)[0] + 1.4, along(1, length * 0.62, 0)[1], "SCREEN LAYERS", GOLD,
            small="tiny", anchor="lm")
    # the centre support bar: dropped below the loop, or stuck up against it
    by = -1.35 if stuck else -2.15
    c.panel([(-0.75, by), (0.75, by), (0.75, by - 0.38), (-0.75, by - 0.38)], BAR, WHITE, 1.0)
    c.label(1.2, by - 0.45, "CENTRE BAR", GOLD, small="tiny", anchor="lm")
    # gears: two meshed, one per half, so both halves turn together
    for gx in (-0.95, 0.95):
        teeth = []
        for k in range(25):
            t = k * math.tau / 24
            rr = 0.82 if k % 2 == 0 else 0.68
            teeth.append((gx + rr * math.cos(t), -3.35 + rr * math.sin(t)))
        c.panel(teeth[:-1], (96, 100, 110), WHITE, 0.9)
        c.circle((gx, -3.35), 0.22, WHITE, 0.8)
    c.label(-4.7, -3.35, "GEARS", WHITE, small="tiny", anchor="rm")
    for side in (-1, 1):                 # springs
        pts = [(side * (2.1 + k * 0.16), -3.35 + (0.18 if k % 2 else -0.18)) for k in range(16)]
        c.poly(pts, (210, 212, 218), 0.9)
    c.label(4.7, -3.35, "SPRINGS", WHITE, small="tiny", anchor="lm")
    # the flex cable crossing under the hinge
    cable = [(-5.0 + k * 0.25, -4.7 - 0.35 * math.exp(-((-5.0 + k * 0.25) / 1.6) ** 2)) for k in range(41)]
    c.poly(cable, GOLD, 1.6)
    c.label(5.2, -4.7, "FLEX CABLE", GOLD, small="tiny", anchor="lm")
    if stuck:
        c.dot(0.55, by + 0.05, ROSE, 4.0)
        c.label(1.6, by + 0.45, "PRESSES HERE", ROSE, small="tiny", anchor="lm")
    return c
