"""3D motion prototype (2026-11-02): a real product built from its layers, in true 3D.

No image model, no cost: every part is a 3D solid drawn in code. The camera orbits, the
layers explode apart in time with the narration, each layer gets its name, then the phone
closes back up. Brand: dark stage, floor grid, gold edge light on the part being explained.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, SECONDS = 1280, 720, 30, 9.0
GOLD = (233, 196, 106)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Real iPhone-style stack, top to bottom (names from public teardowns), colour, thickness.
LAYERS = [
    ("Cover glass", (150, 190, 220), 0.06),
    ("OLED panel", (25, 28, 40), 0.05),
    ("Touch layer", (90, 140, 170), 0.03),
    ("Midframe", (175, 178, 186), 0.10),
    ("Logic board", (40, 110, 70), 0.05),
    ("Battery", (60, 62, 70), 0.12),
    ("Back glass", (205, 200, 190), 0.06),
]


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def rounded_rect(w, h, r, seg=5):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)


OUTLINE = rounded_rect(1.0, 2.05, 0.16)


def slab(z0, thick, scale=1.0):
    """Faces of one layer: list of (3D polygon, kind)."""
    o = OUTLINE * scale
    top = np.c_[o, np.full(len(o), z0 + thick)]
    bot = np.c_[o, np.full(len(o), z0)]
    faces = [(top, "top"), (bot[::-1], "bottom")]
    for i in range(len(o)):
        j = (i + 1) % len(o)
        faces.append((np.array([bot[i], bot[j], top[j], top[i]]), "side"))
    return faces


def camera(t):
    """Orbit: front-on, swing to three-quarter, slight rise."""
    yaw = math.radians(-10 + 48 * ease(t / 3.0) - 20 * ease((t - 6.5) / 2.0))
    pitch = math.radians(20 + 30 * ease(t / 3.0))
    dist = 7.0 + 1.6 * ease((t - 2.2) / 2.0) - 1.6 * ease((t - 6.6) / 1.6)
    return yaw, pitch, dist


CENTER = [0.25]


def project(p, yaw, pitch, dist):
    # rotate the world about z (yaw) then tilt about x (pitch); camera looks down -z'
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    x, y, z = p[..., 0], p[..., 1], p[..., 2] - CENTER[0]
    x1, y1 = x * cy - y * sy, x * sy + y * cy
    y2, z2 = y1 * cp + z * sp, -y1 * sp + z * cp
    depth = dist - z2
    f = 780 / depth
    return np.stack([W / 2 - 60 + x1 * f, H * 0.5 - y2 * f], -1), depth


LIGHT = np.array([0.4, -0.5, 0.75]) / np.linalg.norm([0.4, -0.5, 0.75])


def shade(rgb, normal, k=1.0):
    n = normal / (np.linalg.norm(normal) or 1)
    lit = 0.38 + 0.62 * max(0.0, float(n @ LIGHT))
    return tuple(int(min(255, c * lit * k)) for c in rgb)


def floor(draw, yaw, pitch, dist):
    for i in range(-8, 9):
        for a, b in (((i * 0.5, -4, -0.3), (i * 0.5, 4, -0.3)), ((-4, i * 0.5, -0.3), (4, i * 0.5, -0.3))):
            pa, _ = project(np.array(a), yaw, pitch, dist)
            pb, _ = project(np.array(b), yaw, pitch, dist)
            draw.line([tuple(pa), tuple(pb)], fill=(30, 46, 52), width=1)


def frame(t):
    yaw, pitch, dist = camera(t)
    img = Image.new("RGB", (W, H), (9, 11, 15))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    d, g = ImageDraw.Draw(img), ImageDraw.Draw(glow)
    floor(d, yaw, pitch, dist)
    # explode 2.2s -> 4.2s, hold, close 6.6s -> 8.2s
    spread = ease((t - 2.2) / 2.0) * (1 - ease((t - 6.6) / 1.6))
    CENTER[0] = 0.25 + spread * 1.7
    # the layer being explained lights up in gold, one after another while open
    focus = int((t - 4.0) / 0.38) if 4.0 <= t < 6.6 else -1
    faces = []
    z = 0.0
    for index, (name, rgb, thick) in enumerate(reversed(LAYERS)):
        lift = z + spread * index * 0.5
        for poly, kind in slab(lift, thick):
            faces.append((poly, kind, rgb, len(LAYERS) - 1 - index))
        z += thick
    drawn = []
    for poly, kind, rgb, layer in faces:
        pts, depth = project(poly, yaw, pitch, dist)
        a, b = poly[1] - poly[0], poly[2] - poly[0]
        normal = np.cross(a, b)
        drawn.append((float(depth.mean()), pts, kind, rgb, layer, normal))
    for depth, pts, kind, rgb, layer, normal in sorted(drawn, key=lambda x: -x[0]):
        poly = [tuple(p) for p in pts]
        hot = layer == focus
        d.polygon(poly, fill=shade(rgb, normal, 1.25 if hot else 1.0))
        if kind == "top":
            d.line(poly + [poly[0]], fill=GOLD if hot else (70, 76, 86), width=3 if hot else 1)
            if hot:
                g.line(poly + [poly[0]], fill=GOLD, width=10)
    img = Image.fromarray(np.clip(np.asarray(img, np.int16) + np.asarray(glow.filter(ImageFilter.GaussianBlur(9)), np.int16), 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    if spread > 0.6:
        font = ImageFont.truetype(FONT, 20)
        z = 0.0
        for index, (name, rgb, thick) in enumerate(reversed(LAYERS)):
            layer = len(LAYERS) - 1 - index
            lift = z + spread * index * 0.5 + thick / 2
            z += thick
            anchor, _ = project(np.array([0.5, -1.0, lift]), yaw, pitch, dist)
            x, y = anchor + np.array([60, 0])
            a = int(255 * ease((spread - 0.6) / 0.3))
            col = GOLD if layer == focus else (230, 230, 230)
            d.line([tuple(anchor), (x - 8, y)], fill=(120, 120, 120), width=1)
            d.text((x, y - 12), name.upper(), font=font, fill=tuple(int(c * a / 255) for c in col))
    cap = ImageFont.truetype(FONT, 30)
    line = ("seven layers, one phone" if t < 4 else "the panel is where it fails" if t < 6.6 else "and it closes back up")
    d.text((W / 2 - d.textlength(line, font=cap) / 2, H - 70), line, font=cap, fill=(240, 240, 240))
    d.text((W - 150, 30), "G O L I D E", font=ImageFont.truetype(FONT, 16), fill=(150, 150, 150))
    return img


def main(out: Path) -> None:
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(SECONDS * FPS)):
        proc.stdin.write(frame(i / FPS).tobytes())
    proc.stdin.close()
    proc.wait()


if __name__ == "__main__":
    main(Path(sys.argv[1]))
