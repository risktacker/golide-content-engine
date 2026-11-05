"""Simple 3D for real devices (owner direction 2026-11-05: "anything that can carry 3D... light and
simple... consistency and match the voice just as we do").

Drawn in code, no image cost, on the house base (no floor grid or walls of its own): charcoal
solids with thin white edges and one gold part, the same look as the line drawings. The move
(a lid opening, a drawer sliding out, layers coming apart) takes about a second and lands on
the word the narration says; the object turns slowly for the rest of the scene.

The storyboard asks for it with a figure line::

    3d: object=laptop; on=opens

``object`` is one of OBJECTS, ``on`` the spoken word the move lands on.
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

GOLD = (233, 196, 106)
EDGE = (232, 234, 238)
LIGHT = np.array([0.35, -0.55, 0.76]) / np.linalg.norm([0.35, -0.55, 0.76])
MOVE_SECONDS = 1.0          # the move itself: quick, on the word
PITCH = math.radians(26)
FACES = ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0))


def ease(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def box(cx, cy, cz, sx, sy, sz):
    x0, x1, y0, y1, z0, z1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz, cz + sz
    return np.array([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                     (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], float)


def rot_x(p, angle, pivot):
    c, s = math.cos(angle), math.sin(angle)
    q = p - pivot
    return np.c_[q[:, 0], q[:, 1] * c - q[:, 2] * s, q[:, 1] * s + q[:, 2] * c] + pivot


# ---------- the objects: pose(u) with u = how far the move has gone (0..1) ----------
def laptop(u):
    hinge = np.array([0, 1.0, 0.12])
    angle = -math.radians(108) * u
    return [(box(0, 0, 0, 3.0, 2.0, 0.12), False),
            (rot_x(box(0, 0, 0.12, 3.0, 2.0, 0.07), angle, hinge), False),
            (rot_x(box(0, 0, 0.19, 2.7, 1.7, 0.012), angle, hinge), u > 0.6)]


def phone(u):
    out, z = [], 0.0
    for k, thick in enumerate((0.07, 0.05, 0.10, 0.06, 0.12, 0.06)):   # back to front
        out.append((box(0, 0, z + u * k * 0.42, 1.25, 2.5, thick), k == 4 and u > 0.5))
        z += thick
    return out


def server(u):
    parts = [(box(-1.05, 0, 0, 0.1, 1.6, 3.0), False), (box(1.05, 0, 0, 0.1, 1.6, 3.0), False),
             (box(0, 0, 3.0, 2.2, 1.6, 0.08), False), (box(0, 0, -0.08, 2.2, 1.6, 0.08), False)]
    for k in range(5):
        parts.append((box(0, -1.3 * u if k == 2 else 0.0, 0.12 + k * 0.58, 2.0, 1.5, 0.46), k == 2 and u > 0.3))
    return parts


def chip(u):
    return [(box(0, 0, 0, 2.6, 2.6, 0.12), False),
            (box(0, 0, 0.12, 1.0, 1.0, 0.1), u > 0.4),
            (rot_x(box(0, 0, 0.12 + u * 1.3, 1.9, 1.9, 0.14), math.radians(14) * u, np.array([0, 0, 0.2])), False)]


def battery(u):
    parts = [(box(0, 0, 0, 2.8, 1.8, 0.1), False), (box(-1.35, 0, 0.1, 0.1, 1.8, 0.7), False),
             (box(1.35, 0, 0.1, 0.1, 1.8, 0.7), False), (box(0, -0.85, 0.1, 2.8, 0.1, 0.7), False)]
    for i in range(4):
        for j in range(2):
            lift = u * (0.9 + 0.12 * (i + j))
            parts.append((box(-0.96 + i * 0.64, -0.38 + j * 0.76, 0.1 + lift, 0.52, 0.62, 0.62), (i, j) == (1, 0) and u > 0.5))
    return parts


OBJECTS = {"laptop": (laptop, 1.0), "phone": (phone, 1.05), "server": (server, 0.72),
           "chip": (chip, 1.05), "battery": (battery, 1.0)}


def solids(name: str, u: float):
    builder, scale = OBJECTS[name]
    out = []
    for corners, gold in builder(u):
        out.append((corners * scale, gold))
    return out


# ---------- drawing ----------
def project(p, yaw, size, center, dist=8.0):
    """World z up. Turn by yaw, look down by PITCH. ``size`` is the drawing area's size in pixels."""
    cy_, sy_, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(PITCH), math.sin(PITCH)
    x, y, z = p[..., 0], p[..., 1], p[..., 2] - 0.6
    x1, y1 = x * cy_ - y * sy_, x * sy_ + y * cy_
    up = z * cp + y1 * sp
    depth = dist + y1 * cp - z * sp
    f = size * 0.30 * dist / depth
    return np.stack([center[0] + x1 * f, center[1] - up * f], -1), depth


def _faces(parts, yaw, size, center):
    polys = []
    for corners, gold in parts:
        pts, depth = project(corners, yaw, size, center)
        middle = corners.mean(0)
        for face in FACES:
            p3 = corners[list(face)]
            n = np.cross(p3[1] - p3[0], p3[2] - p3[0])
            n = n / (np.linalg.norm(n) or 1)
            if n @ (p3.mean(0) - middle) < 0:
                n = -n
            polys.append((float(depth[list(face)].mean()), [tuple(map(float, pts[i])) for i in face], n, gold))
    return sorted(polys, key=lambda x: -x[0])


def layer(frame_size: tuple[int, int], center, size: float, name: str, u: float, yaw: float,
          alpha: float = 1.0) -> Image.Image:
    """The object at move ``u`` as an RGBA layer the size of the frame."""
    img = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    glow = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    width = max(1, round(size / 420))
    for _, poly, n, gold in _faces(solids(name, u), yaw, size, center):
        lit = 0.45 + 0.55 * max(0.0, float(n @ LIGHT))
        fill = tuple(int(c * lit) for c in ((70, 58, 30) if gold else (34, 37, 44)))
        d.polygon(poly, fill=fill + (255,))
        d.line(poly + [poly[0]], fill=(GOLD if gold else EDGE) + (255,), width=width * (2 if gold else 1), joint="curve")
        if gold:
            g.line(poly + [poly[0]], fill=GOLD + (255,), width=width * 8)
    out = Image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(size / 90)), img)
    if alpha < 1.0:
        out.putalpha(out.getchannel("A").point(lambda v: int(v * alpha)))
    return out


def outline(name: str, u: float, yaw: float, size: float, center) -> list[tuple[list, bool]]:
    """The visible edges as polylines in pixels (the still picture and the dots of a scene change)."""
    return [(poly + [poly[0]], gold) for _, poly, _, gold in _faces(solids(name, u), yaw, size, center)]


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
