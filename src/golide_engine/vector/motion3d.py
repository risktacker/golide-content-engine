"""Simple 3D for real devices (owner direction 2026-11-05: "anything that can carry 3D... light and
simple... consistency and match the voice just as we do").

Drawn in code, no image cost, on the house base (no floor grid or walls of its own): charcoal
solids with thin white edges and one gold part, the same look as the line drawings. The move
(a lid opening, a drawer sliding out, layers coming apart) takes about a second and lands on
the word the narration says; the object turns slowly for the rest of the scene.

Owner review 2026-11-05 (night): every part is its own solid and no two parts may ever pass
through each other, at any moment of the move (``overlaps`` checks it, the tests run it for
every object). Each pixel shows only the nearest surface (a depth buffer), so a part behind
another can never show through it, whatever the angle.

The storyboard asks for it with a figure line: a preset (``3d: object=laptop; on=opens``) or,
since 2026-11-06, ANY object built from parts (see ``mesh`` and ``MOVES``)::

    3d: object=vault; move=swing; on=opened; box 0 0 0 3 3 3; cyl 0 -1.55 1.3 1.6 0.12 1.6 rx90 gold mover
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageFilter

GOLD = np.array((233, 196, 106), np.float32)
EDGE = np.array((232, 234, 238), np.float32)
BODY = np.array((34, 37, 44), np.float32)
BODY_GOLD = np.array((70, 58, 30), np.float32)
LIGHT = np.array([0.35, -0.55, 0.76]) / np.linalg.norm([0.35, -0.55, 0.76])
MOVE_SECONDS = 0.6          # the move itself: snappy, on the word (owner 2026-11-06: "they need to be fast")
PITCH = math.radians(26)
SS = 2                      # drawn at 2x, then averaged down: smooth edges
FACES = ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0))


def ease(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def box(cx, cy, cz, sx, sy, sz):
    """A solid block: centre x, y, bottom z, and its size."""
    x0, x1, y0, y1, z0, z1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz, cz + sz
    return np.array([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                     (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], float)


def rot_x(p, angle, pivot):
    c, s = math.cos(angle), math.sin(angle)
    q = p - pivot
    return np.c_[q[:, 0], q[:, 1] * c - q[:, 2] * s, q[:, 1] * s + q[:, 2] * c] + pivot


# ---------- the objects: pose(u), u = how far the move has gone (0..1) ----------
# Every part is listed separately; parts may touch but never overlap.

def laptop(u):
    """Base, keyboard deck and trackpad on top of it, then the lid with the screen on its INNER
    face. Closed, the screen faces the keyboard with a small gap; the hinge sits above the back
    edge, so the lid swings up and back past upright without touching the base."""
    angle = -math.radians(108) * u
    hinge = np.array([0.0, 1.0, 0.145])
    lid = rot_x(box(0, 0, 0.145, 3.0, 2.0, 0.065), angle, hinge)
    screen = rot_x(box(0, 0.02, 0.137, 2.7, 1.66, 0.008), angle, hinge)
    return [(box(0, 0, 0, 3.0, 2.0, 0.12), False),
            (box(0, 0.32, 0.12, 2.6, 0.95, 0.012), False),       # keyboard deck
            (box(0, -0.55, 0.12, 0.95, 0.52, 0.006), False),     # trackpad
            (lid, False), (screen, u > 0.55)]


def phone(u):
    """Back glass, battery, logic board, midframe, display, cover glass: equal outlines, stacked;
    they rise apart along the stack, each staying above the one under it."""
    out, z = [], 0.0
    for k, thick in enumerate((0.07, 0.11, 0.05, 0.08, 0.05, 0.06)):
        out.append((box(0, 0, z + u * k * 0.42, 1.25, 2.5, thick), k == 4 and u > 0.5))
        z += thick
    return out


def server(u):
    """An open rack (two sides, top, bottom) with five servers; the middle one slides out the
    front on its rails. Servers sit between the sides and leave a gap above and below."""
    parts = [(box(-1.05, 0, 0, 0.1, 1.6, 3.0), False), (box(1.05, 0, 0, 0.1, 1.6, 3.0), False),
             (box(0, 0, 3.0, 2.2, 1.6, 0.08), False), (box(0, 0, -0.08, 2.2, 1.6, 0.08), False)]
    for k in range(5):
        parts.append((box(0, -1.4 * u if k == 2 else 0.0, 0.12 + k * 0.58, 1.98, 1.5, 0.46), k == 2 and u > 0.3))
    return parts


def chip(u):
    """Substrate, the die in the middle, and the lid: a cap (top plate on four walls) that sits
    around the die, never through it. The lid lifts clear first, then tips back."""
    lift = 1.3 * ease(u / 0.75)
    tip = math.radians(14) * ease((u - 0.45) / 0.55)
    pivot = np.array([0.0, 0.95, 0.3 + lift])
    cap = [box(0, 0, 0.3 + lift, 1.9, 1.9, 0.08),
           box(-0.9, 0, 0.12 + lift, 0.1, 1.9, 0.18), box(0.9, 0, 0.12 + lift, 0.1, 1.9, 0.18),
           box(0, -0.9, 0.12 + lift, 1.7, 0.1, 0.18), box(0, 0.9, 0.12 + lift, 1.7, 0.1, 0.18)]
    return ([(box(0, 0, 0, 2.6, 2.6, 0.12), False), (box(0, 0, 0.12, 1.0, 1.0, 0.1), u > 0.4)]
            + [(rot_x(p, tip, pivot), False) for p in cap])


def battery(u):
    """An open-top case (floor and four walls meeting at the corners without overlapping) holding
    eight cells; the cells rise out one after another, straight up."""
    parts = [(box(0, 0, 0, 2.8, 1.8, 0.1), False),
             (box(-1.35, 0, 0.1, 0.1, 1.8, 0.72), False), (box(1.35, 0, 0.1, 0.1, 1.8, 0.72), False),
             (box(0, -0.85, 0.1, 2.6, 0.1, 0.72), False), (box(0, 0.85, 0.1, 2.6, 0.1, 0.72), False)]
    for i in range(4):
        for j in range(2):
            k = i * 2 + j
            lift = 1.0 * ease((u - k * 0.05) / 0.65)
            parts.append((box(-0.96 + i * 0.64, -0.38 + j * 0.76, 0.1 + lift, 0.52, 0.62, 0.62),
                          (i, j) == (1, 0) and u > 0.5))
    return parts


OBJECTS = {"laptop": (laptop, 1.0), "phone": (phone, 1.05), "server": (server, 0.72),
           "chip": (chip, 1.05), "battery": (battery, 1.0)}


# ---------- the engine: ANY object from parts (owner direction 2026-11-06) ----------
# "The engine that can make 3D, no matter the object." The storyboard describes the object the
# script talks about as simple solid parts (box, cyl, sphere, cone, each placed, sized and turned),
# marks the parts that move and names the move; the engine sizes it, builds it and moves it.
SHAPES = ("box", "cyl", "sphere", "cone")
MOVES = ("lift", "slide", "open", "swing", "spin", "explode", "rise")
MAX_PARTS = 40


def _rot(p: np.ndarray, axis: int, angle: float, pivot) -> np.ndarray:
    """Turn points about the x (0), y (1) or z (2) axis through ``pivot``."""
    if not angle:
        return p
    c, s = math.cos(angle), math.sin(angle)
    i, j = [(1, 2), (2, 0), (0, 1)][axis]
    q = p - pivot
    out = q.copy()
    out[:, i] = q[:, i] * c - q[:, j] * s
    out[:, j] = q[:, i] * s + q[:, j] * c
    return out + pivot


# ---------- geometry: every part is a rounded solid (owner 2026-11-06: "too primitive") ----------
# A part is a cloud of points on its rounded surface; its convex hull gives the triangles. The
# triangle list is worked out once at rest and kept, because every move is rigid.

def _sphere_dirs(rings: int, n: int) -> np.ndarray:
    out = [(0.0, 0.0, -1.0)]
    for r in range(1, rings):
        a = math.pi * r / rings
        out += [(math.sin(a) * math.cos(2 * math.pi * k / n), math.sin(a) * math.sin(2 * math.pi * k / n), -math.cos(a))
                for k in range(n)]
    return np.array(out + [(0.0, 0.0, 1.0)])


CORNER = _sphere_dirs(4, 8)          # a rounded corner
BALL = _sphere_dirs(14, 28)          # a sphere


def rounded_box(corners: np.ndarray, radius: float | None = None) -> np.ndarray:
    """Points of a box (8 corners in ``box`` order, any rotation) with rounded edges."""
    c = np.asarray(corners, float)
    axes = [c[1] - c[0], c[3] - c[0], c[4] - c[0]]
    lengths = [float(np.linalg.norm(a)) for a in axes]
    r = min(min(lengths) * 0.32, max(lengths) * 0.045) if radius is None else radius
    units = [a / (l or 1) for a, l in zip(axes, lengths)]
    frame = np.stack(units, 1)                                   # local -> world
    middle = c.mean(0)
    pts = []
    for corner in c:
        inner = corner - sum(np.sign((corner - middle) @ u) * r * u for u in units)
        pts.append(inner + (CORNER @ frame.T) * r)
    return np.concatenate(pts)


def _round_points(shape: str, at, size, rot) -> np.ndarray:
    x, y, z = at
    w, d, h = (max(0.02, float(v)) for v in size)
    if shape == "box":
        pts = rounded_box(box(x, y, z, w, d, h))
    elif shape == "sphere":
        pts = BALL * (w / 2, d / 2, h / 2) + (x, y, z + h / 2)
    elif shape in ("cyl", "cone"):
        n = 48
        r = min(w, d, h) * 0.08
        rings = []
        ring = np.array([(math.cos(2 * math.pi * k / n), math.sin(2 * math.pi * k / n)) for k in range(n)])
        for zz, shrink in ((0.0, r), (r * 0.3, r * 0.3), (r, 0.0)):
            rings.append(np.c_[x + ring[:, 0] * (w / 2 - shrink), y + ring[:, 1] * (d / 2 - shrink), np.full(n, z + zz)])
        if shape == "cyl":
            for zz, shrink in ((h - r, 0.0), (h - r * 0.3, r * 0.3), (h, r)):
                rings.append(np.c_[x + ring[:, 0] * (w / 2 - shrink), y + ring[:, 1] * (d / 2 - shrink), np.full(n, z + zz)])
        else:
            rings.append(np.c_[x + ring[:, 0] * w * 0.04, y + ring[:, 1] * d * 0.04, np.full(n, z + h * 0.97)])
            rings.append(np.array([[x, y, z + h]]))
        pts = np.concatenate(rings)
    else:
        raise ValueError(f"shape must be one of {', '.join(SHAPES)}")
    middle = np.array([x, y, z + h / 2])
    for axis, deg in enumerate(rot):
        pts = _rot(pts, axis, math.radians(float(deg)), middle)
    return pts


_HULLS: dict = {}


def _hull(key, pts: np.ndarray) -> np.ndarray:
    """Triangles (index triples, wound outward) of the convex hull of the rest-pose points."""
    if key not in _HULLS:
        from scipy.spatial import ConvexHull

        hull = ConvexHull(pts)
        tris = hull.simplices.copy()
        a, b, c = pts[tris[:, 0]], pts[tris[:, 1]], pts[tris[:, 2]]
        flip = (np.cross(b - a, c - a) * hull.equations[:, :3]).sum(1) < 0
        tris[flip] = tris[flip][:, [0, 2, 1]]
        _HULLS[key] = tris
    return _HULLS[key]


_SPECS: dict[str, list] = {}


_EXPLODE: dict = {}  # CAD objects: each part's own explode offset from its design
_COLOURS: dict = {}  # CAD objects: each part's real colour (presets keep the house graphite)


def _cad(spec) -> str | None:
    """The object's name when it is a built CAD object (vector/cad3d.py)."""
    from . import cad3d

    name = spec.get("object") if isinstance(spec, dict) else spec
    return name if name and cad3d.available(name) else None


def labels(name) -> list[str]:
    """Viewer-facing part names (CAD objects), in part order; empty for other objects."""
    from . import cad3d

    cad = _cad(name)
    return [p[5] for p in cad3d.parts(cad)] if cad else []


def part_index(name, words: str) -> int | None:
    """The part a few spoken words refer to, matched on shared words with its label."""
    import re as _re

    want = {w for w in _re.findall(r"[a-z0-9]+", str(words).lower()) if len(w) > 2}
    best, score = None, 0
    for i, label in enumerate(labels(name)):
        have = set(_re.findall(r"[a-z0-9]+", label.lower()))
        hit = len(want & have) + sum(1 for w in want for h in have if w != h and (w in h or h in w)) * 0.5
        if hit > score:
            best, score = i, hit
    return best


def _spec_key(spec: dict) -> str:
    import json

    if not spec.get("parts") and _cad(spec):
        return json.dumps({"cad": _cad(spec).lower()})
    return json.dumps({"parts": spec.get("parts")}, sort_keys=True)


def _normalised(spec: dict) -> list:
    """The parts as rounded point clouds, scaled so the object's longest side is 3 units, centred,
    standing on z = 0 (the storyboard may use any units)."""
    key = _spec_key(spec)
    if key not in _SPECS and not spec.get("parts") and _cad(spec):
        from . import cad3d

        loaded = cad3d.parts(_cad(spec))
        for i, (pts, tris, *_rest) in enumerate(loaded):  # noqa: B007
            _HULLS[(key, i)] = tris            # a CAD part keeps its own triangles, not a hull
        _SPECS[key] = [(pts, gold, mover) for pts, _, gold, mover, *_ in loaded]
        _EXPLODE[key] = [part[4] for part in loaded]
        _COLOURS[key] = np.array([part[6] for part in loaded], np.float32)
    if key not in _SPECS:
        parts = []
        for part in (spec.get("parts") or [])[:MAX_PARTS]:
            pts = _round_points(part["shape"], part["at"], part["size"], part.get("rot") or (0, 0, 0))
            parts.append((pts, bool(part.get("gold")), bool(part.get("mover"))))
        if not parts:
            raise ValueError("a 3D object needs at least one part")
        every = np.concatenate([p for p, *_ in parts])
        lo, hi = every.min(0), every.max(0)
        scale = 3.0 / max(1e-6, float((hi - lo).max()))
        shift = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
        _SPECS[key] = [((p - shift) * scale, g, m) for p, g, m in parts]
    return _SPECS[key]


def _built(spec: dict, u: float):
    """The object at move u: the movers (or, for explode, every part) moved."""
    key = _spec_key(spec)
    parts = _normalised(spec)
    move = spec.get("move") if spec.get("move") in MOVES else "lift"
    flagged = any(m for *_, m in parts)
    movers = [p for p, g, m in parts if m] if flagged else [parts[-1][0]]
    pts = np.concatenate(movers)
    lo, hi = pts.min(0), pts.max(0)
    centre = np.concatenate([p for p, *_ in parts]).mean(0)
    out = []
    for i, (rest, gold, mover) in enumerate(parts):
        mover = mover if flagged else i == len(parts) - 1
        v = rest
        if move == "explode" and key in _EXPLODE:
            v = rest + _EXPLODE[key][i] * u        # the design's own direction for each part
        elif move == "explode":
            away = rest.mean(0) - centre
            away = away / np.linalg.norm(away) if np.linalg.norm(away) > 1e-3 else np.array([0, 0, 1.0])
            v = rest + away * 1.1 * u
        elif mover:
            if move == "lift":
                v = rest + (0, 0, 1.3 * u)
            elif move == "rise":
                v = rest + (0, 0, -1.3 * (1 - u))
            elif move == "slide":
                v = rest + (0, -1.5 * u, 0)
            elif move == "open":          # a lid: hinged on its back top edge, swings up and back
                v = _rot(rest, 0, -math.radians(105) * u, np.array([0, hi[1], hi[2]]))
            elif move == "swing":         # a door: hinged on its left edge, swings toward the viewer
                v = _rot(rest, 2, math.radians(100) * u, np.array([lo[0], lo[1], 0]))
            elif move == "spin":
                v = _rot(rest, 2, 2 * math.pi * u, np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, 0]))
        out.append((v, _hull((key, i), rest), gold))
    return out


def is_model(model) -> bool:
    """A preset name or an engine spec with parts."""
    if isinstance(model, dict):
        return bool(model.get("parts")) or model.get("object") in OBJECTS or bool(_cad(model))
    return model in OBJECTS or bool(_cad(model))


def _preset_boxes(name: str, u: float):
    builder, scale = OBJECTS[name]
    return [(corners * scale, gold) for corners, gold in builder(u)]


_LAST: list = [None, None]


def solids(model, u: float):
    """(points, triangles, gold) for every part at move u. ``model``: a preset name or a spec."""
    key = ((_spec_key(model), model.get("move")) if isinstance(model, dict) else model, float(u))
    if _LAST[0] != key:
        _LAST[0], _LAST[1] = key, _solids(model, u)
    return _LAST[1]


_REST: dict = {}


def _solids(model, u: float):
    if not isinstance(model, dict) and _cad(model):
        model = {"object": model, "move": "explode"}     # a named CAD object comes apart by default
    if isinstance(model, dict):
        if model.get("parts") or _cad(model):
            return _built(model, u)
        model = model.get("object")
    out = []
    for i, (corners, gold) in enumerate(_preset_boxes(model, u)):
        pts = rounded_box(corners)
        if ("preset", model, i) not in _HULLS:
            _hull(("preset", model, i), rounded_box(_preset_boxes(model, 0.0)[i][0]))
        out.append((pts, _HULLS[("preset", model, i)], gold))
    return out


# ---------- the no-overlap check (every pair of parts, through the whole move) ----------
def _axes(a: np.ndarray) -> list[np.ndarray]:
    return [a[1] - a[0], a[3] - a[0], a[4] - a[0]]


def _intersect(a: np.ndarray, b: np.ndarray, tol: float) -> bool:
    """Separating-axis test for two boxes (8 corners each): True when they overlap by more than tol."""
    axes = _axes(a) + _axes(b)
    axes += [np.cross(x, y) for x in _axes(a) for y in _axes(b)]
    for axis in axes:
        n = np.linalg.norm(axis)
        if n < 1e-9:
            continue
        axis = axis / n
        pa, pb = a @ axis, b @ axis
        if pa.max() <= pb.min() + tol or pb.max() <= pa.min() + tol:
            return False
    return True


def overlaps(name: str, steps: int = 41, tol: float = 1e-4) -> list[tuple[float, int, int]]:
    """Every (u, part, part) where two preset parts pass through each other. Empty means clean."""
    found = []
    for i in range(steps):
        u = i / (steps - 1)
        parts = [c for c, _ in _preset_boxes(name, u)]
        for p in range(len(parts)):
            for q in range(p + 1, len(parts)):
                if _intersect(parts[p], parts[q], tol):
                    found.append((round(u, 3), p, q))
    return found


# ---------- drawing: a product render (depth buffer, smooth normals, real light) ----------
def project(p, yaw, size, dist=8.0):
    """World z up; turn by yaw, look down by PITCH. Pixels relative to the centre, and depth."""
    cy_, sy_, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(PITCH), math.sin(PITCH)
    x, y, z = p[..., 0], p[..., 1], p[..., 2] - 0.6
    x1, y1 = x * cy_ - y * sy_, x * sy_ + y * cy_
    up = z * cp + y1 * sp
    depth = dist + y1 * cp - z * sp
    f = size * 0.30 * dist / depth
    return np.stack([x1 * f, -up * f], -1), depth


KEY = np.array([-0.45, -0.55, 0.70]); KEY /= np.linalg.norm(KEY)
FILL = np.array([0.75, -0.35, 0.25]); FILL /= np.linalg.norm(FILL)
BODY_RGB = np.array((52, 57, 68), np.float32)
GOLD_RGB = np.array((214, 168, 72), np.float32)
RIM = np.array((150, 170, 235), np.float32)


def _fill_python(scr, inv, vn, tris, tpart, zbuf, ids, nbuf):
    h, w = zbuf.shape
    for t in range(len(tris)):
        a, b, c = tris[t]
        ax, ay = scr[a]; bx, by = scr[b]; cx, cy = scr[c]
        area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
        if abs(area) < 1e-6:
            continue
        lx, hx = max(0, int(min(ax, bx, cx))), min(w, int(max(ax, bx, cx)) + 2)
        ly, hy = max(0, int(min(ay, by, cy))), min(h, int(max(ay, by, cy)) + 2)
        for yy in range(ly, hy):
            py = yy + 0.5
            for xx in range(lx, hx):
                px = xx + 0.5
                w0 = ((bx - px) * (cy - py) - (cx - px) * (by - py)) / area
                w1 = ((cx - px) * (ay - py) - (ax - px) * (cy - py)) / area
                w2 = 1.0 - w0 - w1
                if w0 < -1e-4 or w1 < -1e-4 or w2 < -1e-4:
                    continue
                d = w0 * inv[a] + w1 * inv[b] + w2 * inv[c]
                if d > zbuf[yy, xx]:
                    zbuf[yy, xx] = d
                    ids[yy, xx] = tpart[t]
                    for k in range(3):
                        nbuf[yy, xx, k] = w0 * vn[a, k] + w1 * vn[b, k] + w2 * vn[c, k]


try:                                   # compiled when numba is there: ~100x faster
    from numba import njit
    _fill = njit(cache=True, nogil=True)(_fill_python)
except Exception:                      # pragma: no cover
    _fill = _fill_python


def _raster(name, u: float, yaw: float, size: float, ss: int = SS):
    """Per pixel (at ss times the size): part id, 1/depth, smooth normal. Returns
    (part ids, origin in pixels from the centre, normals, gold flags, view direction)."""
    cy_, sy_, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(PITCH), math.sin(PITCH)
    toward = np.array([sy_ * cp, cy_ * cp, -sp])     # how depth grows with x, y, z
    parts = solids(name, u)
    projected = []
    for pts, tris, gold in parts:
        scr, depth = project(pts, yaw, size * ss)
        fn = np.cross(pts[tris[:, 1]] - pts[tris[:, 0]], pts[tris[:, 2]] - pts[tris[:, 0]])
        vn = np.zeros_like(pts)
        for k in range(3):
            np.add.at(vn, tris[:, k], fn)
        vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-9
        projected.append((scr, depth, tris, fn, vn))
    every = np.concatenate([p[0] for p in projected])
    x0, y0 = np.floor(every.min(0)) - 3 * ss
    x1, y1 = np.ceil(every.max(0)) + 3 * ss
    w, h = int(x1 - x0), int(y1 - y0)
    zbuf = np.zeros((h, w), np.float32)
    ids = np.full((h, w), -1, np.int32)
    nbuf = np.zeros((h, w, 3), np.float32)
    scrs, invs, vns, tris_all, tparts, offset = [], [], [], [], [], 0
    for pid, (scr, depth, tris, fn, vn) in enumerate(projected):
        visible = tris[(fn @ toward) < 0]
        scrs.append(scr - (x0, y0)); invs.append(1.0 / depth); vns.append(vn)
        tris_all.append(visible + offset); tparts.append(np.full(len(visible), pid, np.int32))
        offset += len(scr)
    _fill(np.ascontiguousarray(np.concatenate(scrs), np.float64), np.concatenate(invs).astype(np.float64),
          np.ascontiguousarray(np.concatenate(vns), np.float64), np.ascontiguousarray(np.concatenate(tris_all), np.int64),
          np.concatenate(tparts), zbuf, ids, nbuf)
    hit = ids >= 0
    nbuf[hit] /= np.linalg.norm(nbuf[hit], axis=1, keepdims=True) + 1e-9
    golds = np.array([g for *_, g in parts], bool)
    return ids, (x0 / ss, y0 / ss), nbuf, golds, toward


def _colours_of(name):
    """Each part's own colour for a CAD object, else None (the house graphite and gold)."""
    if isinstance(name, dict) or _cad(name):
        spec = name if isinstance(name, dict) else {"object": name}
        return _COLOURS.get(_spec_key(spec))
    return None


def _edges(ids: np.ndarray, width: int = 1):
    """Where one part meets another or the background: the silhouettes."""
    edge = np.zeros(ids.shape, bool)
    edge[:, 1:] |= ids[:, 1:] != ids[:, :-1]
    edge[1:, :] |= ids[1:, :] != ids[:-1, :]
    for _ in range(max(0, width - 1)):
        grown = edge.copy()
        grown[1:, :] |= edge[:-1, :]
        grown[:-1, :] |= edge[1:, :]
        grown[:, 1:] |= edge[:, :-1]
        grown[:, :-1] |= edge[:, 1:]
        edge = grown
    return edge


def _shade(ids, nbuf, golds, toward, colours=None):
    """Graphite with a soft key light, a cool fill, a sharp highlight and a blue rim; gold parts
    are polished metal. Only the pixels the object covers are lit."""
    view = (-toward).astype(np.float32)
    half = (KEY + view) / np.linalg.norm(KEY + view)
    filled = ids >= 0
    n = nbuf[filled].astype(np.float32)
    g = golds[ids[filled]]
    diff = np.clip(n @ KEY.astype(np.float32), 0, 1)
    fill = np.clip(n @ FILL.astype(np.float32), 0, 1)
    facing = np.clip(n @ view, 0, 1)
    spec = np.clip(n @ half.astype(np.float32), 0, 1)
    rim = (1 - facing) ** 3
    light = 0.30 + 0.85 * diff + 0.25 * fill
    out = np.empty((len(n), 3), np.float32)
    body, metal = ~g, g
    if colours is not None:   # real colours: each part lit in its own colour, a clear-coat highlight on top
        base = colours[ids[filled]]
        out = base * light[:, None] * 0.82 + 150.0 * (spec ** 40)[:, None] + RIM * (0.35 * rim)[:, None]
        colour = np.zeros(ids.shape + (3,), np.float32)
        colour[filled] = out
        gold = np.zeros(ids.shape, bool)
        gold[filled] = g
        return colour, gold
    out[body] = BODY_RGB * light[body, None] + 140.0 * (spec[body] ** 46)[:, None] + RIM * (0.55 * rim[body])[:, None]
    out[metal] = (GOLD_RGB * light[metal, None] + GOLD_RGB * (spec[metal] ** 18 * 1.0)[:, None]
                  + RIM * (0.25 * rim[metal])[:, None])
    colour = np.zeros(ids.shape + (3,), np.float32)
    colour[filled] = out
    gold = np.zeros(ids.shape, bool)
    gold[filled] = g
    return colour, gold


GEOMETRY: dict = {}   # the last render's parts on screen, for marks drawn over it (vector.render)


def _geometry(name, u, yaw, size, ids, origin, ss=SS):
    """Per part, in the render image's pixels: bounding box, centre and the two ends of its longest
    axis (for a measurement line)."""
    out = []
    for i, (pts, _tris, _g) in enumerate(solids(name, u)):
        ys, xs = np.nonzero(ids == i)
        if not len(xs):
            out.append(None)
            continue
        box = (xs.min() / ss, ys.min() / ss, xs.max() / ss, ys.max() / ss)
        centred = pts - pts.mean(0)
        axis = np.linalg.svd(centred, full_matrices=False)[2][0]
        along = centred @ axis
        ends = np.stack([pts.mean(0) + axis * along.min(), pts.mean(0) + axis * along.max()])
        scr, _ = project(ends, yaw, size)
        scr = scr - np.array(origin)
        out.append({"box": box, "centre": ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), "ends": scr.tolist()})
    return out


def render(name, u: float, yaw: float, size: float, highlight: tuple = (), tint=None):
    """The object as an RGBA image (a product render on the house black) and the pixel offset of
    its top-left from the centre. highlight: part numbers lit in ``tint`` while they are talked about."""
    size = float(size)
    ids, origin, nbuf, golds, toward = _raster(name, u, yaw, size)
    colours = _colours_of(name)
    if highlight:
        base = colours if colours is not None else np.tile(BODY_RGB, (len(golds), 1)).astype(np.float32)
        colours = base.copy()
        tint = np.asarray(tint if tint is not None else GOLD, np.float32)
        for i in highlight:
            if 0 <= i < len(colours):
                colours[i] = colours[i] * 0.35 + tint * 0.65
        golds = golds.copy()
        golds[:] = False
        for i in highlight:
            if 0 <= i < len(golds):
                golds[i] = True
    colour, gold = _shade(ids, nbuf, golds, toward, colours)
    edge = _edges(ids, max(1, round(size / 500)))
    filled = ids >= 0
    colour[edge & filled] = colour[edge & filled] * 0.55 + np.float32(225) * 0.18   # a fine seam where parts meet
    rgba = np.zeros(ids.shape + (4,), np.uint8)
    rgba[..., :3] = colour.clip(0, 255).astype(np.uint8)
    rgba[..., 3] = np.where(filled, 255, 0)
    big = Image.fromarray(rgba, "RGBA")
    small = big.resize((max(1, big.width // SS), max(1, big.height // SS)), Image.Resampling.BOX)
    # a soft contact shadow under the object, and the gold part's glow
    floor = np.zeros(ids.shape, np.uint8)
    pts = np.concatenate([p for p, *_ in solids(name, u)])
    low = pts[:, 2] <= pts[:, 2].min() + 0.25
    if low.any():
        ground = pts[low].copy()
        ground[:, 2] = pts[:, 2].min()
        scr, _ = project(ground, yaw, size * SS)
        ox, oy = origin[0] * SS, origin[1] * SS
        from PIL import ImageDraw
        sh = Image.fromarray(floor)
        lo, hi = scr.min(0) - (ox, oy), scr.max(0) - (ox, oy)
        pad = (hi[0] - lo[0]) * 0.08
        ImageDraw.Draw(sh).ellipse([lo[0] - pad, lo[1] + (hi[1] - lo[1]) * 0.15, hi[0] + pad, hi[1] + pad], fill=150)
        floor = np.asarray(sh)
    shadow = Image.fromarray(floor).resize(small.size, Image.Resampling.BOX).filter(ImageFilter.GaussianBlur(size / 40))
    glow_a = Image.fromarray((gold * 255).astype(np.uint8)).resize(small.size, Image.Resampling.BOX)
    glow_a = glow_a.filter(ImageFilter.GaussianBlur(size / 70)).point(lambda v: min(255, int(v * 1.1)))
    under = Image.new("RGBA", small.size, (0, 0, 0, 0))
    under.putalpha(shadow)
    glow_rgb = GOLD
    if colours is not None and golds.any():      # the story part glows in its own colour
        glow_rgb = np.clip(colours[int(np.argmax(golds))] * 1.25 + 30, 0, 255)
    GEOMETRY.clear()
    GEOMETRY.update(parts=_geometry(name, u, yaw, size, ids, origin))
    glow = Image.new("RGBA", small.size, tuple(int(c) for c in glow_rgb) + (0,))
    glow.putalpha(glow_a)
    return Image.alpha_composite(Image.alpha_composite(under, glow), small), origin


def layer(frame_size: tuple[int, int], center, size: float, name, u: float, yaw: float,
          alpha: float = 1.0) -> Image.Image:
    """The object at move ``u`` as an RGBA layer the size of the frame."""
    img, (ox, oy) = render(name, u, yaw, size)
    if alpha < 1.0:
        img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
    out = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    out.paste(img, (int(round(center[0] + ox)), int(round(center[1] + oy))))
    return out


def edge_points(name, u: float, yaw: float, size: float, count: int, seed: int = 0) -> np.ndarray:
    """Points on the visible outline (pixels from the centre): where the scene-change light lands
    on, or leaves from, the object exactly as it looks at that moment."""
    ids, (ox, oy), *_ = _raster(name, u, yaw, size, ss=1)
    edge = _edges(ids) & (ids >= 0)
    ys, xs = np.nonzero(edge)
    if len(xs) == 0:
        return np.zeros((0, 2))
    pts = np.stack([xs + ox, ys + oy], 1).astype(np.float64)
    pick = np.random.default_rng(seed).choice(len(pts), count, replace=len(pts) < count)
    return pts[pick]


def outline(name, u: float, yaw: float, size: float, center) -> list[tuple[list, bool]]:
    """The visible outline as short polylines in pixels (the still picture in the figure file)."""
    ids, (ox, oy), _, golds, _ = _raster(name, u, yaw, size, ss=1)
    edge = _edges(ids) & (ids >= 0)
    gold = edge & golds[np.clip(ids, 0, None)]
    out = []
    for mask, is_gold in ((edge & ~gold, False), (gold, True)):
        ys, xs = np.nonzero(mask)
        for x, y in zip(xs[::3], ys[::3]):
            px, py = center[0] + x + ox, center[1] + y + oy
            out.append(([(px, py), (px + 1.0, py + 0.5)], is_gold))
    return out


def extent(name: str, size: float, moves=(0.0, 0.25, 0.5, 0.75, 1.0)) -> tuple[float, float, float, float]:
    """The box the object fills (pixels from the centre) over its whole move and turn, so it
    can be fitted once per scene and never grows past the drawing area."""
    xs, ys = [], []
    for u in moves:
        for yaw in (-34, -23, -12):
            for corners, *_ in solids(name, u):
                pts, _ = project(corners, math.radians(yaw), size)
                xs += list(pts[:, 0])
                ys += list(pts[:, 1])
    return min(xs), min(ys), max(xs), max(ys)


def fit(name: str, zone: tuple[float, float, float, float], base: float) -> tuple[float, float, float]:
    """Size and centre that keep the object inside ``zone`` (x0, y0, x1, y1 in frame pixels)
    through its whole move: (size, centre x, centre y)."""
    x0, y0, x1, y1 = extent(name, base)
    grow = 1.7 if _cad(name) else 1.0    # CAD objects fill the zone; presets keep their approved size
    scale = min(grow, (zone[2] - zone[0]) / max(1e-6, x1 - x0), (zone[3] - zone[1]) / max(1e-6, y1 - y0))
    cx = (zone[0] + zone[2]) / 2 - (x0 + x1) / 2 * scale
    cy = (zone[1] + zone[3]) / 2 - (y0 + y1) / 2 * scale
    return float(base * scale), float(cx), float(cy)


def fit_range(name, zone, base):
    """(closed fit, opened fit). A CAD object fills the drawing area closed and the camera pulls
    back as it opens, so it is always as big as the area allows; other objects keep one fit."""
    if not _cad(name):
        one = fit(name, zone, base)
        return one, one

    def at(moves):
        x0, y0, x1, y1 = extent(name, base, moves)
        scale = min(2.6, (zone[2] - zone[0]) / max(1e-6, x1 - x0), (zone[3] - zone[1]) / max(1e-6, y1 - y0))
        # standing on the floor: the base stays put while the camera pulls back
        return (float(base * scale), (zone[0] + zone[2]) / 2 - (x0 + x1) / 2 * scale, zone[3] - y1 * scale)

    return at((0.0,)), at((1.0,))


def move_progress(t: float, start: float) -> float:
    return ease((t - start) / MOVE_SECONDS)


def turn(t: float, scene_start: float, scene_end: float) -> float:
    """A slow turn through the scene, so every side reads as real 3D."""
    span = max(1e-3, scene_end - scene_start)
    return math.radians(-40 + 34 * ease((t - scene_start) / span))


def trigger_time(lines, word: str, fallback: float) -> float:
    """When the narration says ``word``: its line's start plus its place inside the line."""
    word = (word or "").strip().lower()
    if word:
        for line in lines:
            words = str(line.text).lower().replace(",", " ").replace(".", " ").split()
            for k, w in enumerate(words):
                if w.startswith(word[:max(3, len(word) - 2)]):
                    return line.start + (line.end - line.start) * k / max(1, len(words))
    return fallback
