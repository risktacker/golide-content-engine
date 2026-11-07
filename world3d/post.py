"""Finishing pass on rendered frames, run with normal Python (no Blender needed):
adds lens glow on bright pixels, then draws labels. python post.py <dir>"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = Path("/usr/share/fonts/opentype/inter/Inter-Medium.otf")
if not FONT.exists():
    FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
GOLD = (255, 190, 70)


def glow(img, threshold=0.82, amount=0.55):
    a = np.asarray(img, dtype=np.float32) / 255
    bright = np.clip((a - threshold) / (1 - threshold), 0, 1)
    src = Image.fromarray((bright * 255).astype(np.uint8))
    w = img.width
    wide = np.asarray(src.filter(ImageFilter.GaussianBlur(w / 90)), dtype=np.float32) / 255
    tight = np.asarray(src.filter(ImageFilter.GaussianBlur(w / 400)), dtype=np.float32) / 255
    return Image.fromarray((np.clip(1 - (1 - a) * (1 - amount * (wide + tight)), 0, 1) * 255).astype(np.uint8))


def draw_labels(img, labels):
    w, h = img.size
    scale = w / 1920
    layer = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    font = ImageFont.truetype(str(FONT), int(78 * scale))
    for lb in labels:
        if lb["alpha"] <= 0.01:
            continue
        al = int(255 * lb["alpha"])
        x, y = lb["x"] * w * 2, lb["y"] * h * 2
        ex, ey = x + lb["dx"] * w * 2, y + lb["dy"] * h * 2
        tw = d.textlength(lb["text"], font=font)
        sign = 1 if lb["dx"] >= 0 else -1
        margin = 60 * scale
        ex = max(margin + (tw if sign < 0 else 0), min(w * 2 - margin - (tw if sign > 0 else 0), ex))
        ey = max(margin + 80 * scale, min(h * 2 - margin, ey))
        r = 7 * scale * 2
        d.ellipse((x - r, y - r, x + r, y + r), fill=(*GOLD, al))
        d.line((x, y, ex, ey), fill=(255, 255, 255, al), width=max(2, int(3 * scale * 2)))
        d.line((ex, ey, ex + sign * (tw + 26 * scale), ey), fill=(255, 255, 255, al), width=max(2, int(3 * scale * 2)))
        tx = ex + 10 * scale if sign > 0 else ex - tw - 10 * scale
        d.text((tx, ey - 100 * scale), lb["text"], font=font, fill=(255, 255, 255, al),
               stroke_width=max(1, int(3 * scale)), stroke_fill=(0, 0, 0, int(al * 0.55)))
    layer = layer.resize((w, h), Image.LANCZOS)
    out = img.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


def main(folder):
    folder = Path(folder)
    labels = json.loads((folder / "labels.json").read_text())
    done = folder / "final"
    done.mkdir(exist_ok=True)
    for png in sorted(folder.glob("f*.png")):
        target = done / png.name
        if target.exists():
            continue
        draw_labels(glow(Image.open(png).convert("RGB")), labels.get(png.stem, [])).save(target)


if __name__ == "__main__":
    main(sys.argv[1])
