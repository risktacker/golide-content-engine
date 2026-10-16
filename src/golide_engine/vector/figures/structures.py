"""Structures: a Warren truss bridge solved by the method of joints (tension and compression)."""

from __future__ import annotations

import numpy as np

from .core import DIM, GOLD, WHITE, Canvas, FigureError, fmt, new_canvas, num


def truss(size, params, items) -> Canvas:
    span, height = num(params, "span", 6.0), num(params, "height", 2.0)
    load = num(params, "load", 10.0)
    panels = int(num(params, "panels", 3))
    unit = params.get("unit", "kN")
    if not 2 <= panels <= 6 or span <= 0 or height <= 0:
        raise FigureError("2 to 6 panels, positive span and height")
    at = int(num(params, "at", panels // 2 if panels % 2 == 0 else panels // 2))
    if not 1 <= at <= panels - 1:
        at = max(1, min(panels - 1, panels // 2))
    w = span / panels
    bottom = [(i * w, 0.0) for i in range(panels + 1)]
    top = [((i + 0.5) * w, height) for i in range(panels)]
    nodes = bottom + top
    T = lambda i: panels + 1 + i  # noqa: E731
    members = [(i, i + 1) for i in range(panels)]                       # bottom chord
    members += [(T(i), T(i + 1)) for i in range(panels - 1)]            # top chord
    for i in range(panels):                                             # diagonals
        members += [(i, T(i)), (T(i), i + 1)]
    # Unknowns: member forces (tension +), pin Rx, Ry at node 0, roller Ry at the last bottom node.
    j = len(nodes)
    m = len(members)
    A = np.zeros((2 * j, m + 3))
    b = np.zeros(2 * j)
    for k, (p, q) in enumerate(members):
        (x0, y0), (x1, y1) = nodes[p], nodes[q]
        length = np.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        A[2 * p, k], A[2 * p + 1, k] = ux, uy
        A[2 * q, k], A[2 * q + 1, k] = -ux, -uy
    A[0, m], A[1, m + 1], A[2 * panels + 1, m + 2] = 1, 1, 1
    b[2 * at + 1] = load                                                # load acts downward at bottom node `at`
    try:
        x = np.linalg.solve(A, b)
    except np.linalg.LinAlgError as exc:
        raise FigureError("this truss cannot be solved") from exc
    forces = x[:m]
    c = new_canvas(size, (-0.9, -1.9, span + 0.9, height + 0.9))
    biggest = int(np.argmax(np.abs(forces)))
    chord = set(range(panels)) | set(range(panels, 2 * panels - 1))
    end_diagonals = {2 * panels - 1, m - 1}  # the diagonals next to the supports carry the most
    for k, (p, q) in enumerate(members):
        color = GOLD if k == biggest else WHITE
        c.seg(nodes[p], nodes[q], color, 1.5 if k == biggest else 1.1)
        f = forces[k]
        if abs(f) < 1e-6 or (k not in chord and k not in end_diagonals and k != biggest):
            continue  # inner diagonals stay unlabelled so the numbers can be read
        mx, my = (nodes[p][0] + nodes[q][0]) / 2, (nodes[p][1] + nodes[q][1]) / 2
        kind = "pull" if f > 0 else "push"
        text = f"{fmt(abs(f), 1)} {kind}"
        tone = color if k == biggest else DIM
        if k < panels:                      # bottom chord: label below
            c.label(mx, my, text, tone, small="tiny", anchor="mt", dy=c.line * 5)
        elif k in chord:                    # top chord: label above
            c.label(mx, my, text, tone, small="tiny", anchor="mb", dy=-c.line * 5)
        else:                               # end diagonals: label outside the truss
            c.label(mx, my, text, tone, small="tiny", anchor="rm" if mx < span / 2 else "lm",
                    dx=-c.line * 6 if mx < span / 2 else c.line * 6)
    for x_, y_ in nodes:
        c.dot(x_, y_, WHITE, 2.4)
    s = 0.25
    c.poly([(0, 0), (-s, -1.5 * s), (s, -1.5 * s), (0, 0)], WHITE, 1.0)
    c.poly([(span, 0), (span - s, -1.5 * s), (span + s, -1.5 * s), (span, 0)], WHITE, 1.0)
    lx = bottom[at][0]
    c.arrow((lx, -0.08), (lx, -1.0), GOLD, 1.5)  # the load hangs from the deck joint
    c.label(lx, -1.0, f"load {fmt(load)} {unit}", GOLD, small=True, anchor="mt", dy=c.line * 4)
    c.label(0, -0.5, f"{fmt(x[m + 1], 2)} {unit}", WHITE, small="tiny", anchor="mt", dy=c.line * 4)
    c.label(span, -0.5, f"{fmt(x[m + 2], 2)} {unit}", WHITE, small="tiny", anchor="mt", dy=c.line * 4)
    c.label(span / 2, height + 0.75, "pull = tension, push = compression", DIM, small="tiny")
    return c
