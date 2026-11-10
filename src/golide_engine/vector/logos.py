"""Real brand logos for thumbnails (owner 2026-11-10: "real logos are to be used").

The logos come from Simple Icons (CC0 collection of brand marks, simpleicons.org), downloaded from
npm the first time and cached. Each logo is drawn in code as a glossy app tile in the brand's own
colour, the way top tech thumbnails show apps: rounded, lit from above, with a soft shadow. The marks
belong to their owners and are shown to name the product the video is about.
"""

from __future__ import annotations

import io
import json
import os
import re
import tarfile
import urllib.request
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

VERSION = "16.37.0"
TARBALL = f"https://registry.npmjs.org/simple-icons/-/simple-icons-{VERSION}.tgz"
# Common names that are not the Simple Icons title or slug.
ALIASES = {"chatgpt": "openai", "gpt": "openai", "x": "x", "twitter": "x", "meta ai": "meta", "facebook": "facebook",
           "google gemini": "googlegemini", "gemini": "googlegemini", "claude code": "claude", "iphone": "apple",
           "macbook": "apple", "ipad": "apple", "mac": "apple", "aws": "amazonwebservices", "amazon web services":
           "amazonwebservices", "microsoft": "microsoft", "copilot": "githubcopilot", "vs code": "visualstudiocode",
           "tesla roadster": "tesla", "spacex": "spacex", "nvidia gpu": "nvidia", "deepseek": "deepseek"}


def _cache() -> Path:
    return Path(os.environ.get("GOLIDE_LOGOS", Path.home() / ".cache" / "golide-logos")) / VERSION


def slug(name: str) -> str:
    """Simple Icons' own slug rule."""
    s = str(name).lower().strip().replace("+", "plus").replace(".", "dot").replace("&", "and")
    return re.sub(r"[^a-z0-9]", "", s)


@lru_cache(maxsize=1)
def catalogue() -> dict[str, dict]:
    """slug -> {title, hex, svg}. Downloaded once per machine (about 4 MB)."""
    folder = _cache()
    index = folder / "index.json"
    if not index.exists():
        folder.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(TARBALL, timeout=60) as response:
            data = response.read()
        icons: dict[str, dict] = {}
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            meta = json.load(tar.extractfile("package/data/simple-icons.json"))
            meta = meta.get("icons", meta) if isinstance(meta, dict) else meta
            for m in meta:
                s = m.get("slug") or slug(m["title"])
                member = f"package/icons/{s}.svg"
                try:
                    svg = tar.extractfile(member).read().decode("utf-8")
                except (KeyError, AttributeError):
                    continue
                icons[s] = {"title": m["title"], "hex": m.get("hex", "FFFFFF"), "svg": svg}
        index.write_text(json.dumps(icons), encoding="utf-8")
    return json.loads(index.read_text(encoding="utf-8"))


def find(name: str) -> dict | None:
    """The logo for a product or company name, or None (never a guess at a look-alike)."""
    try:
        icons = catalogue()
    except Exception:  # noqa: BLE001 - offline: the thumbnail goes without logos
        return None
    key = str(name).lower().strip()
    for candidate in (ALIASES.get(key, ""), slug(key), slug(key.split(" ")[0]) if " " in key else ""):
        if candidate and candidate in icons:
            return dict(icons[candidate], slug=candidate)
    titles = {slug(v["title"]): k for k, v in icons.items()}
    hit = titles.get(slug(key))
    return dict(icons[hit], slug=hit) if hit else None


def _glyph(svg: str, size: int, rgb: tuple[int, int, int]) -> Image.Image:
    import cairosvg

    hexs = "#%02x%02x%02x" % rgb
    svg = re.sub(r"<svg ", f'<svg fill="{hexs}" ', svg, count=1)
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=size, output_height=size)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def tile(icon: dict, size: int) -> Image.Image:
    """A glossy app tile: brand colour, white mark (dark when the brand colour is pale), a top
    sheen, a darker lower lip for depth, and a soft shadow. Size in pixels; returns RGBA with margin."""
    hexs = icon.get("hex", "FFFFFF")
    base = tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))
    light = sum(base) / 3 > 200
    if light:                                  # a white brand becomes a white tile with its dark mark
        mark = (18, 18, 22)
    else:
        mark = (255, 255, 255)
    pad = int(size * 0.22)
    W = size + pad * 2
    out = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    r = int(size * 0.24)
    box = [pad, pad, pad + size, pad + size]

    shadow = Image.new("L", (W, W), 0)
    ImageDraw.Draw(shadow).rounded_rectangle([box[0], box[1] + size * 0.06, box[2], box[3] + size * 0.06], r, fill=200)
    shadow = shadow.filter(ImageFilter.GaussianBlur(size * 0.07))
    out.paste(Image.new("RGBA", (W, W), (0, 0, 0, 255)), (0, 0), shadow)

    # body: a vertical gradient of the brand colour, lighter at the top
    def mix(c, t, k):
        return tuple(int(a + (b - a) * k) for a, b in zip(c, t))
    top, bottom = mix(base, (255, 255, 255), 0.28), mix(base, (0, 0, 0), 0.22)
    if sum(base) < 60:                         # black brands get a graphite body so the tile reads
        top, bottom = (70, 72, 80), (16, 16, 20)
    grad = Image.new("RGBA", (W, W))
    gd = ImageDraw.Draw(grad)
    for y in range(W):
        k = min(1.0, max(0.0, (y - box[1]) / size))
        gd.line([(0, y), (W, y)], fill=mix(top, bottom, k) + (255,))
    lip = Image.new("L", (W, W), 0)
    ImageDraw.Draw(lip).rounded_rectangle([box[0], box[1] + size * 0.035, box[2], box[3] + size * 0.035], r, fill=255)
    out.paste(Image.new("RGBA", (W, W), mix(bottom, (0, 0, 0), 0.35) + (255,)), (0, 0), lip)
    body = Image.new("L", (W, W), 0)
    ImageDraw.Draw(body).rounded_rectangle(box, r, fill=255)
    out.paste(grad, (0, 0), body)

    # the mark
    g = _glyph(icon["svg"], int(size * 0.56), mark)
    shade = Image.new("RGBA", g.size, (0, 0, 0, 0))
    shade.putalpha(g.getchannel("A").point(lambda v: v * 0.35))
    off = pad + (size - g.size[0]) // 2
    out.alpha_composite(shade.filter(ImageFilter.GaussianBlur(size * 0.012)), (off, off + int(size * 0.015)))
    out.alpha_composite(g, (off, off))

    # sheen across the top half, and a thin bright edge
    sheen = Image.new("L", (W, W), 0)
    sd = ImageDraw.Draw(sheen)
    for y in range(box[1], box[1] + int(size * 0.5)):
        k = 1 - (y - box[1]) / (size * 0.5)
        sd.line([(box[0], y), (box[2], y)], fill=int(70 * k ** 1.6))
    sheen = ImageChops.multiply(sheen, body)
    out.paste(Image.new("RGBA", (W, W), (255, 255, 255, 255)), (0, 0), sheen)
    edge = Image.new("L", (W, W), 0)
    ImageDraw.Draw(edge).rounded_rectangle(box, r, outline=90, width=max(2, size // 90))
    out.paste(Image.new("RGBA", (W, W), (255, 255, 255, 255)), (0, 0), ImageChops.multiply(edge, body))
    return out


def place(image: Image.Image, names: list[str], text_edge: float) -> list[str]:
    """Put up to three real logos on the thumbnail, large, in front of the object on the right and
    clear of the words. Returns the names that had a logo."""
    found = [(n, find(n)) for n in names]
    found = [(n, i) for n, i in found if i][:3]
    if not found:
        return []
    w, h = image.size
    size = int(h * (0.36 if len(found) == 1 else 0.30 if len(found) == 2 else 0.25))
    x0 = max(int(w * text_edge) + int(w * 0.02), int(w * 0.5))
    spots = {1: [(0.80, 0.70)], 2: [(0.66, 0.70), (0.86, 0.50)], 3: [(0.62, 0.74), (0.80, 0.56), (0.93, 0.78)]}[len(found)]
    angles = {1: [-8], 2: [-10, 8], 3: [-10, 6, -4]}[len(found)]
    canvas = image.convert("RGBA")
    for (name, icon), (fx, fy), angle in zip(found, spots, angles):
        t = tile(icon, size).rotate(angle, resample=Image.BICUBIC, expand=True)
        cx = max(x0 + t.size[0] // 2, int(w * fx))
        cx = min(cx, w - t.size[0] // 2 + int(size * 0.15))
        cy = int(h * fy)
        canvas.alpha_composite(t, (cx - t.size[0] // 2, cy - t.size[1] // 2))
    image.paste(canvas.convert("RGB"))
    return [n for n, _ in found]
