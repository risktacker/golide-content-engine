"""Molecule figures: structural drawings of common molecules with their real bond angles."""

from __future__ import annotations

import math

from .core import GOLD, WHITE, Canvas, FigureError, new_canvas

# name: (formula label, atoms [(symbol, x, y)], bonds [(i, j, order)], angle note or "")
def _bent(angle: float, length: float = 1.0):
    half = math.radians(angle / 2)
    return [(-length * math.sin(half), -length * math.cos(half)), (length * math.sin(half), -length * math.cos(half))]


_W = _bent(104.5)
_N = _bent(107.0)
MOLECULES = {
    "water": ("H2O, water", [("O", 0, 0), ("H", *_W[0]), ("H", *_W[1])], [(0, 1, 1), (0, 2, 1)],
              "bond angle 104.5°"),
    "carbon dioxide": ("CO2, carbon dioxide", [("C", 0, 0), ("O", -1.2, 0), ("O", 1.2, 0)],
                       [(0, 1, 2), (0, 2, 2)], "straight line, 180°"),
    "methane": ("CH4, methane", [("C", 0, 0), ("H", 0, 1.05), ("H", -1.0, -0.35), ("H", 1.0, -0.35),
                                 ("H", 0.3, -0.85)], [(0, 1, 1), (0, 2, 1), (0, 3, 1), (0, 4, 1)],
                "a 3D pyramid shape, 109.5° between bonds"),
    "ammonia": ("NH3, ammonia", [("N", 0, 0), ("H", *_N[0]), ("H", *_N[1]), ("H", 0, -0.55)],
                [(0, 1, 1), (0, 2, 1), (0, 3, 1)], "bond angle 107°"),
    "oxygen": ("O2, oxygen", [("O", -0.6, 0), ("O", 0.6, 0)], [(0, 1, 2)], "double bond"),
    "nitrogen": ("N2, nitrogen", [("N", -0.55, 0), ("N", 0.55, 0)], [(0, 1, 3)], "triple bond"),
    "hydrogen": ("H2, hydrogen", [("H", -0.4, 0), ("H", 0.4, 0)], [(0, 1, 1)], "single bond"),
    "ethanol": ("C2H5OH, ethanol", [("C", -0.9, 0), ("C", 0.4, 0.45), ("O", 1.6, -0.1), ("H", 2.4, 0.35),
                                    ("H", -1.6, 0.6), ("H", -1.4, -0.75), ("H", -0.6, -0.95),
                                    ("H", 0.3, 1.5), ("H", 0.8, -0.4)],
                [(0, 1, 1), (1, 2, 1), (2, 3, 1), (0, 4, 1), (0, 5, 1), (0, 6, 1), (1, 7, 1), (1, 8, 1)],
                "the OH group makes it an alcohol"),
}
_ALIASES = {"h2o": "water", "co2": "carbon dioxide", "ch4": "methane", "nh3": "ammonia", "o2": "oxygen",
            "n2": "nitrogen", "h2": "hydrogen", "c2h5oh": "ethanol", "alcohol": "ethanol"}


def _benzene():
    atoms, bonds = [], []
    for k in range(6):
        a = math.radians(90 + 60 * k)
        atoms.append(("C", math.cos(a), math.sin(a)))
    for k in range(6):
        a = math.radians(90 + 60 * k)
        atoms.append(("H", 1.75 * math.cos(a), 1.75 * math.sin(a)))
        bonds.append((k, (k + 1) % 6, 2 if k % 2 == 0 else 1))
        bonds.append((k, k + 6, 1))
    return "C6H6, benzene", atoms, bonds, "a ring of six carbons, every angle 120°"


MOLECULES["benzene"] = _benzene()


def molecule(size, params, items) -> Canvas:
    name = (params.get("name") or (items[0] if items else "")).strip().lower().replace("_", " ")
    name = _ALIASES.get(name.replace(" ", ""), name)
    if name not in MOLECULES:
        raise FigureError(f"molecule {name!r} is not in the library: {', '.join(sorted(MOLECULES))}")
    title, atoms, bonds, note = MOLECULES[name]
    xs, ys = [a[1] for a in atoms], [a[2] for a in atoms]
    pad = 0.75
    c = new_canvas(size, (min(xs) - pad, min(ys) - pad - 0.7, max(xs) + pad, max(ys) + pad))
    r_big, r_small = 0.32, 0.22
    radius = [r_small if sym == "H" else r_big for sym, _, _ in atoms]
    centre = max(range(len(atoms)), key=lambda i: sum(1 for b in bonds if i in b[:2]))
    for i, j, order in bonds:
        (_, x0, y0), (_, x1, y1) = atoms[i], atoms[j]
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        ux, uy = dx / length, dy / length
        a = (x0 + ux * radius[i], y0 + uy * radius[i])
        b = (x1 - ux * radius[j], y1 - uy * radius[j])
        gap = 0.07
        offsets = [0.0] if order == 1 else [-gap, gap] if order == 2 else [-gap * 1.6, 0.0, gap * 1.6]
        for off in offsets:
            c.seg((a[0] - uy * off, a[1] + ux * off), (b[0] - uy * off, b[1] + ux * off), WHITE, 1.1)
    for k, (sym, x, y) in enumerate(atoms):
        color = GOLD if k == centre and len(atoms) > 2 else WHITE
        c.circle((x, y), radius[k], color, 1.3)
        c.label(x, y, sym, color, small=sym == "H")
    c.label((min(xs) + max(xs)) / 2, min(ys) - 0.75, title, WHITE, small=True)
    if note:
        c.label((min(xs) + max(xs)) / 2, min(ys) - 0.75, note, GOLD, small=True, anchor="mt", dy=c.line * 10)
    return c
