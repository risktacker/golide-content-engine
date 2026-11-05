"""Simple 3D on the GOLIDE base (2026-11-05 sample for the owner): anything that can be shown in
plain 3D, not only phone layers. Drawn in code, no image cost.

Same look as the line drawings: charcoal solids with thin white edges, one part in gold, on the
house black stage (vignette, blue-violet haze, stars, faint dot grid). No floor grid or walls of
its own. Three moves in one 12 s Short:
  1. a laptop turns and its lid opens (hinge)
  2. a server rack: one drawer slides out (slide)
  3. a chip: the lid lifts off and the die lights up (open / reveal)
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, SECONDS = 720, 1280, 30, 12.0
GOLD = (233, 196, 106)
EDGE = (232, 234, 238)
FONT = str(Path(__file__).resolve().parents[2] / "assets" / "fonts" / "Poppins-SemiBold.ttf")
LIGHT = np.array([0.35, -0.55, 0.76]) / np.linalg.norm([0.35, -0.55, 0.76])


def ease(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


# ---------- the house base: black stage, haze, stars, faint dot grid ----------
def make_base() -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.45) / (H * 0.6)) ** 2)
    base = np.stack([12 - 6 * r, 13 - 6 * r, 18 - 8 * r], -1)
    haze = np.exp(-(((xx - W * 0.6) / (W * 0.5)) ** 2 + ((yy - H * 0.35) / (H * 0.3)) ** 2))[..., None]
    base = base + haze * np.array([10, 8, 22])
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for y in range(20, H, 36):          # faint dot grid, dimmer toward the edges
        for x in range(20, W, 36):
            a = max(0.0, 1 - math.hypot((x - W / 2) / W, (y - H / 2) / H) * 1.6)
            c = int(38 + 22 * a)
            d.point((x, y), fill=(c, c, c + 4))
    rng = np.random.default_rng(3)
    for _ in range(90):
        x, y, s = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 1.6)
        c = int(rng.uniform(90, 170))
        d.ellipse([x - s, y - s, x + s, y + s], fill=(c, c, c + 10))
    return img


# ---------- tiny 3D: boxes, transforms, painter's order ----------
FACES = ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0))


def box(cx, cy, cz, sx, sy, sz):
    x0, x1, y0, y1, z0, z1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz, cz + sz
    return np.array([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                     (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], float)


def rot_x(p, angle, pivot):
    c, s = math.cos(angle), math.sin(angle)
    q = p - pivot
    return np.c_[q[:, 0], q[:, 1] * c - q[:, 2] * s, q[:, 1] * s + q[:, 2] * c] + pivot


def project(p, yaw, pitch, dist, cy_frac=0.44):
    """World z is up. Turn by yaw, look down by pitch; returns screen points and depth."""
    cyw, syw, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    x1, y1 = x * cyw - y * syw, x * syw + y * cyw
    up = z * cp + y1 * sp
    depth = dist + y1 * cp - z * sp
    f = 1250 / depth
    return np.stack([W / 2 + x1 * f, H * cy_frac - up * f], -1), depth


def draw_solids(img, solids, yaw, pitch, dist):
    """solids: list of (corners, gold: bool). Fill charcoal by light, white edges, gold part glows."""
    d = ImageDraw.Draw(img)
    glow = Image.new("RGB", img.size, (0, 0, 0))
    g = ImageDraw.Draw(glow)
    polys = []
    for corners, gold in solids:
        pts, depth = project(corners, yaw, pitch, dist)
        middle = corners.mean(0)
        for face in FACES:
            p3 = corners[list(face)]
            n = np.cross(p3[1] - p3[0], p3[2] - p3[0])
            n = n / (np.linalg.norm(n) or 1)
            if n @ (p3.mean(0) - middle) < 0:      # point the normal outward
                n = -n
            polys.append((float(depth[list(face)].mean()), [tuple(pts[i]) for i in face], n, gold))
    for _, poly, n, gold in sorted(polys, key=lambda x: -x[0]):
        lit = 0.45 + 0.55 * max(0.0, float(n @ LIGHT))
        fill = tuple(int(c * lit) for c in ((70, 58, 30) if gold else (34, 37, 44)))
        d.polygon(poly, fill=fill)
        d.line(poly + [poly[0]], fill=GOLD if gold else EDGE, width=2 if gold else 1, joint="curve")
        if gold:
            g.line(poly + [poly[0]], fill=GOLD, width=9)
    return Image.fromarray(np.clip(np.asarray(img, np.int16)
                                   + np.asarray(glow.filter(ImageFilter.GaussianBlur(10)), np.int16), 0, 255).astype(np.uint8))


# ---------- the three moves ----------
def laptop(t):            # 0-4 s: turns, lid opens on its hinge
    open_ = ease((t - 0.8) / 1.8)
    base = box(0, 0, 0, 3.0, 2.0, 0.12)
    hinge = np.array([0, 1.0, 0.12])
    lid = rot_x(box(0, 0, 0.12, 3.0, 2.0, 0.07), -math.radians(108) * open_, hinge)
    screen = rot_x(box(0, 0, 0.19, 2.7, 1.7, 0.012), -math.radians(108) * open_, hinge)
    return [(base, False), (lid, False), (screen, open_ > 0.6)], "The lid opens on a real hinge"


def rack(t):              # 4-8 s: one drawer slides out
    out = ease((t - 5.0) / 1.4)
    parts = [(box(-1.05, 0, 0, 0.1, 1.6, 3.0), False), (box(1.05, 0, 0, 0.1, 1.6, 3.0), False),
             (box(0, 0, 3.0, 2.2, 1.6, 0.08), False), (box(0, 0, -0.08, 2.2, 1.6, 0.08), False)]
    for k in range(5):
        slide = -1.3 * out if k == 2 else 0.0
        parts.append((box(0, slide, 0.12 + k * 0.58, 2.0, 1.5, 0.46), k == 2 and out > 0.3))
    return parts, "One server slides out of the rack"


def chip(t):              # 8-12 s: the lid lifts, the die lights up
    lift = ease((t - 8.8) / 1.4)
    parts = [(box(0, 0, 0, 2.6, 2.6, 0.12), False),
             (box(0, 0, 0.12, 1.0, 1.0, 0.1), lift > 0.4),
             (rot_x(box(0, 0, 0.12 + lift * 1.3, 1.9, 1.9, 0.14), math.radians(14) * lift, np.array([0, 0, 0.2])), False)]
    return parts, "Under the lid: the chip itself"


def frame(t, base):
    local = t % 4
    yaw = math.radians(-38 + 14 * local)        # a slow turn within each move
    pitch = math.radians(28)
    scene, caption = laptop(t) if t < 4 else rack(t) if t < 8 else chip(t)
    dist = 7.5 if t < 4 else 11.5 if t < 8 else 7.0
    fade = min(1.0, local / 0.35, (4 - local) / 0.35)
    img = draw_solids(base.copy(), scene, yaw, pitch, dist)
    if fade < 1:
        img = Image.blend(base, img, max(0.0, fade))
    d = ImageDraw.Draw(img)
    cap = ImageFont.truetype(FONT, 38)
    lines, words = [], caption.split()
    while words:
        line = words.pop(0)
        while words and d.textlength(line + " " + words[0], font=cap) < W * 0.72:
            line += " " + words.pop(0)
        lines.append(line)
    for i, line in enumerate(lines):
        d.text((W / 2 - d.textlength(line, font=cap) / 2, H * 0.70 + i * 50), line, font=cap, fill=(244, 244, 244))
    mark = ImageFont.truetype(FONT, 18)
    d.text((W / 2 - d.textlength("G O L I D E", font=mark) / 2, H * 0.08), "G O L I D E", font=mark, fill=(150, 150, 156))
    return img


def main(out: Path) -> None:
    base = make_base()
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(SECONDS * FPS)):
        proc.stdin.write(frame(i / FPS, base).tobytes())
    proc.stdin.close()
    proc.wait()


if __name__ == "__main__":
    main(Path(sys.argv[1]))
