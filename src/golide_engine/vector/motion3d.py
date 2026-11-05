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

The storyboard asks for it with a figure line::

    3d: object=laptop; on=opens
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
MOVE_SECONDS = 1.0          # the move itself: quick, on the word
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


def solids(name: str, u: float):
    builder, scale = OBJECTS[name]
    return [(corners * scale, gold) for corners, gold in builder(u)]


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
    """Every (u, part, part) where two parts pass through each other. Empty means clean."""
    found = []
    for i in range(steps):
        u = i / (steps - 1)
        parts = [c for c, _ in solids(name, u)]
        for p in range(len(parts)):
            for q in range(p + 1, len(parts)):
                if _intersect(parts[p], parts[q], tol):
                    found.append((round(u, 3), p, q))
    return found


# ---------- drawing: depth buffer, one surface per pixel ----------
def project(p, yaw, size, dist=8.0):
    """World z up; turn by yaw, look down by PITCH. Pixels relative to the centre, and depth."""
    cy_, sy_, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(PITCH), math.sin(PITCH)
    x, y, z = p[..., 0], p[..., 1], p[..., 2] - 0.6
    x1, y1 = x * cy_ - y * sy_, x * sy_ + y * cy_
    up = z * cp + y1 * sp
    depth = dist + y1 * cp - z * sp
    f = size * 0.30 * dist / depth
    return np.stack([x1 * f, -up * f], -1), depth


def _raster(name: str, u: float, yaw: float, size: float, ss: int = SS):
    """Face id per pixel (at ss times the size) through a depth buffer, plus the face colours and
    gold flags. Returns (ids, origin in pixels relative to the centre, colours, gold flags)."""
    cy_, sy_, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(PITCH), math.sin(PITCH)
    toward = np.array([sy_ * cp, cy_ * cp, -sp])     # how depth grows with x, y, z
    faces, colours, golds = [], [], []
    for corners, gold in solids(name, u):
        pts, depth = project(corners, yaw, size * ss)
        middle = corners.mean(0)
        for face in FACES:
            p3 = corners[list(face)]
            n = np.cross(p3[1] - p3[0], p3[2] - p3[0])
            n = n / (np.linalg.norm(n) or 1)
            if n @ (p3.mean(0) - middle) < 0:
                n = -n
            if n @ toward > 0.02:          # turned away from the camera: never visible on a solid
                continue
            lit = 0.45 + 0.55 * max(0.0, float(n @ LIGHT))
            faces.append((pts[list(face)], depth[list(face)]))
            colours.append((BODY_GOLD if gold else BODY) * lit)
            golds.append(gold)
    every = np.concatenate([f[0] for f in faces])
    x0, y0 = np.floor(every.min(0)) - 3 * ss
    x1, y1 = np.ceil(every.max(0)) + 3 * ss
    w, h = int(x1 - x0), int(y1 - y0)
    zbuf = np.zeros((h, w), np.float32)   # 1/depth: exact on screen under perspective, 0 = nothing
    ids = np.full((h, w), -1, np.int32)
    for fid, (pts, depth) in enumerate(faces):
        pts = pts - (x0, y0)
        lx, hx = max(0, int(pts[:, 0].min())), min(w, int(pts[:, 0].max()) + 2)
        ly, hy = max(0, int(pts[:, 1].min())), min(h, int(pts[:, 1].max()) + 2)
        if lx >= hx or ly >= hy:
            continue
        gx = (np.arange(lx, hx, dtype=np.float32) + 0.5)[None, :]
        gy = (np.arange(ly, hy, dtype=np.float32) + 0.5)[:, None]
        # inside the (convex) face: on the same side of all four edges
        sign = np.sign((pts[1, 0] - pts[0, 0]) * (pts[2, 1] - pts[0, 1]) - (pts[2, 0] - pts[0, 0]) * (pts[1, 1] - pts[0, 1]))
        if sign == 0:
            continue
        inside = None
        for k in range(4):
            (ax, ay), (bx, by) = pts[k], pts[(k + 1) % 4]
            e = (np.float32((bx - ax) * sign) * (gy - np.float32(ay))) - (np.float32((by - ay) * sign) * (gx - np.float32(ax)))
            inside = (e >= -1e-3) if inside is None else (inside & (e >= -1e-3))
        if not inside.any():
            continue
        # 1/depth over the face (straight on screen under perspective): the plane through three corners
        depth = 1.0 / depth
        (ax, ay), (bx, by), (cx, cy) = pts[0], pts[1], pts[2]
        area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
        kx = np.float32(((cy - ay) * (depth[1] - depth[0]) - (by - ay) * (depth[2] - depth[0])) / area)
        ky = np.float32(((bx - ax) * (depth[2] - depth[0]) - (cx - ax) * (depth[1] - depth[0])) / area)
        d = np.float32(depth[0]) + kx * (gx - np.float32(ax)) + ky * (gy - np.float32(ay))
        zone = zbuf[ly:hy, lx:hx]
        nearer = inside & (d > zone)
        zone[nearer] = d[nearer]
        ids[ly:hy, lx:hx][nearer] = fid
    return ids, (x0 / ss, y0 / ss), np.array(colours, np.float32), np.array(golds, bool)


def _edges(ids: np.ndarray, golds: np.ndarray, width: int):
    """Lines where the visible surface changes (part edges, silhouettes); gold where a gold part is."""
    edge = np.zeros(ids.shape, bool)
    gold = np.zeros(ids.shape, bool)
    for a, b in ((ids[:, 1:], ids[:, :-1]), (ids[1:, :], ids[:-1, :])):
        diff = a != b
        sl = (slice(None), slice(1, None)) if a.shape[1] != ids.shape[1] else (slice(1, None), slice(None))
        edge[sl] |= diff
        is_gold = np.zeros(a.shape, bool)
        for side in (a, b):
            is_gold |= (side >= 0) & golds[np.clip(side, 0, None)]
        gold[sl] |= diff & is_gold
    for _ in range(max(0, width - 1)):   # thicken
        for mask in (edge, gold):
            grown = mask.copy()
            grown[1:, :] |= mask[:-1, :]
            grown[:-1, :] |= mask[1:, :]
            grown[:, 1:] |= mask[:, :-1]
            grown[:, :-1] |= mask[:, 1:]
            mask[:] = grown
    return edge, gold


def render(name: str, u: float, yaw: float, size: float):
    """The object as an RGBA image and the pixel offset of its top-left from the centre."""
    size = float(size)
    ids, origin, colours, golds = _raster(name, u, yaw, size)
    width = max(1, round(size / 300))
    edge, gold = _edges(ids, golds, width)
    # one colour index per pixel: 0 empty, 1.. faces, then edge and gold
    n = len(colours)
    index = (ids + 1).astype(np.int32)
    index[edge] = n + 1
    index[gold] = n + 2
    palette = np.zeros((n + 3, 4), np.uint8)
    palette[1:n + 1, :3] = colours.clip(0, 255).astype(np.uint8)
    palette[1:, 3] = 255
    palette[n + 1, :3] = EDGE.astype(np.uint8)
    palette[n + 2, :3] = GOLD.astype(np.uint8)
    big = Image.fromarray(palette[index], "RGBA")
    small = big.resize((max(1, big.width // SS), max(1, big.height // SS)), Image.Resampling.BOX)
    # the gold part's soft glow, under the object
    glow_a = Image.fromarray((gold * 255).astype(np.uint8)).resize(small.size, Image.Resampling.BOX)
    glow_a = glow_a.filter(ImageFilter.GaussianBlur(size / 90)).point(lambda v: min(255, int(v * 1.6)))
    glow = Image.new("RGBA", small.size, tuple(int(c) for c in GOLD) + (0,))
    glow.putalpha(glow_a)
    return Image.alpha_composite(glow, small), origin


def layer(frame_size: tuple[int, int], center, size: float, name: str, u: float, yaw: float,
          alpha: float = 1.0) -> Image.Image:
    """The object at move ``u`` as an RGBA layer the size of the frame."""
    img, (ox, oy) = render(name, u, yaw, size)
    if alpha < 1.0:
        img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
    out = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    out.paste(img, (int(round(center[0] + ox)), int(round(center[1] + oy))))
    return out


def edge_points(name: str, u: float, yaw: float, size: float, count: int, seed: int = 0) -> np.ndarray:
    """Points on the visible edges (pixels from the centre): where the scene-change light lands
    on, or leaves from, the object exactly as it looks at that moment."""
    ids, (ox, oy), _, golds = _raster(name, u, yaw, size, ss=1)
    edge, _ = _edges(ids, golds, 1)
    ys, xs = np.nonzero(edge)
    if len(xs) == 0:
        return np.zeros((0, 2))
    pts = np.stack([xs + ox, ys + oy], 1).astype(np.float64)
    pick = np.random.default_rng(seed).choice(len(pts), count, replace=len(pts) < count)
    return pts[pick]


def outline(name: str, u: float, yaw: float, size: float, center) -> list[tuple[list, bool]]:
    """The visible edges as short polylines in pixels (the still picture in the figure file)."""
    ids, (ox, oy), _, golds = _raster(name, u, yaw, size, ss=1)
    edge, gold = _edges(ids, golds, 1)
    out = []
    for mask, is_gold in ((edge & ~gold, False), (gold, True)):
        ys, xs = np.nonzero(mask)
        for x, y in zip(xs[::3], ys[::3]):
            px, py = center[0] + x + ox, center[1] + y + oy
            out.append(([(px, py), (px + 1.0, py + 0.5)], is_gold))
    return out


def extent(name: str, size: float) -> tuple[float, float, float, float]:
    """The box the object fills (pixels from the centre) over its whole move and turn, so it
    can be fitted once per scene and never grows past the drawing area."""
    xs, ys = [], []
    for u in (0.0, 0.25, 0.5, 0.75, 1.0):
        for yaw in (-34, -23, -12):
            for corners, _ in solids(name, u):
                pts, _ = project(corners, math.radians(yaw), size)
                xs += list(pts[:, 0])
                ys += list(pts[:, 1])
    return min(xs), min(ys), max(xs), max(ys)


def fit(name: str, zone: tuple[float, float, float, float], base: float) -> tuple[float, float, float]:
    """Size and centre that keep the object inside ``zone`` (x0, y0, x1, y1 in frame pixels)
    through its whole move: (size, centre x, centre y)."""
    x0, y0, x1, y1 = extent(name, base)
    scale = min(1.0, (zone[2] - zone[0]) / max(1e-6, x1 - x0), (zone[3] - zone[1]) / max(1e-6, y1 - y0))
    cx = (zone[0] + zone[2]) / 2 - (x0 + x1) / 2 * scale
    cy = (zone[1] + zone[3]) / 2 - (y0 + y1) / 2 * scale
    return float(base * scale), float(cx), float(cy)


def move_progress(t: float, start: float) -> float:
    return ease((t - start) / MOVE_SECONDS)


def turn(t: float, scene_start: float, scene_end: float) -> float:
    """A slow turn through the scene, so every side reads as real 3D."""
    span = max(1e-3, scene_end - scene_start)
    return math.radians(-34 + 22 * ease((t - scene_start) / span))


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
