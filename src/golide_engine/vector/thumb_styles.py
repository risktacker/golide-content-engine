"""Thumbnail editing styles the owner approved (2026-11-10), drawn in code, no image model.

Five styles modelled on thumbnails that work in our niche: light glass, platter row, dark drama,
editorial type and grid paper. Each one: two or three very heavy words in two colours, the real
logos of what the video is about as glossy 3D tiles (Three.js, rendered in headless Chromium), and
a background that fits the story (light for tools and how-tos, dark for crashes and money). The
style rotates so two videos in a row never look the same. No avatars of real people.
"""

from __future__ import annotations

import base64
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import logos

ROOT = Path(__file__).resolve().parents[3]
THREE = ROOT / "assets" / "three"
FONTS = ROOT / "assets" / "fonts" / "thumb"
ANTON, P9, P8, SERIF_I = ("anton-latin-400-normal.woff", "poppins-latin-900-normal.woff",
                          "poppins-latin-800-normal.woff", "dm-serif-display-latin-400-italic.woff")
W, H = 1280, 720
STYLES = ("light_glass", "editorial", "grid_paper", "platter", "dark_drama")
ALERT = re.compile(r"\b(crash|crashed|hack|hacked|breach|leak|leaked|scam|warning|danger|attack|ban|banned|"
                   r"lawsuit|sued|fired|collapse|collapses|lost|loses|loss|outage|down|fail|failed|dead|kill|"
                   r"heist|stolen|exploit|threat|alert|emergency|\-\$)", re.I)


def is_alert(text: str) -> bool:
    return bool(ALERT.search(str(text)))


def choose(title: str, brands: int, n: int) -> str:
    """Dark drama for crashes, losses and danger; the platter row when there are 3+ logos;
    otherwise the light styles, rotating."""
    if is_alert(title):
        return "dark_drama"
    if brands >= 3 and n % 2 == 0:
        return "platter"
    light = ("light_glass", "editorial", "grid_paper")
    return light[n % len(light)]


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def fit(text: str, name: str, max_w: int, max_h: int, start: int = 420) -> ImageFont.FreeTypeFont:
    size = start
    while size > 24:
        f = _font(name, size)
        x0, y0, x1, y1 = f.getbbox(text)
        if x1 - x0 <= max_w and y1 - y0 <= max_h:
            return f
        size -= 6
    return _font(name, 24)


# ---------- 3D tiles

def _tile(icon: dict, **kw) -> dict:
    hexs = icon["hex"]
    light = sum(int(hexs[k:k + 2], 16) for k in (0, 2, 4)) / 3 > 200
    d = {"svg": icon["svg"], "hex": hexs, "mark": "111111" if light else "ffffff"}
    if sum(int(hexs[k:k + 2], 16) for k in (0, 2, 4)) < 90:
        d["hex"] = "1b1c22"
    d.update(kw)
    return d


def render_tiles(spec: dict) -> Image.Image:
    """The glossy 3D tiles as a transparent image (Three.js in headless Chromium)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                                          "--ignore-gpu-blocklist"])
        page = browser.new_page(viewport={"width": 1600, "height": 1000})

        def serve(route):
            path = route.request.url.split("://", 1)[1].split("/", 1)[1].split("?")[0]
            f = THREE / path if path != "" else THREE / "tiles.html"
            if path.startswith("three/"):
                f = THREE / path[len("three/"):]
            if not f.exists():
                return route.fulfill(status=404, body="")
            route.fulfill(path=str(f), content_type="text/javascript" if f.suffix == ".js" else None)

        page.route("**/*", serve)
        page.goto("http://tiles.local/tiles.html")
        page.wait_for_function("window.ready === true", timeout=60000)
        data = page.evaluate("(s) => window.draw(s)", spec)
        browser.close()
    import io

    return Image.open(io.BytesIO(base64.b64decode(data.split(",", 1)[1]))).convert("RGBA")


# ---------- drawing helpers

def _grad(top, bottom, w=W, h=H) -> Image.Image:
    g = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(g)
    for y in range(h):
        k = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(top, bottom)) + (255,))
    return g


def _grid(base, step, col, width=1):
    d = ImageDraw.Draw(base)
    for x in range(0, base.size[0], step):
        d.line([(x, 0), (x, base.size[1])], fill=col, width=width)
    for y in range(0, base.size[1], step):
        d.line([(0, y), (base.size[0], y)], fill=col, width=width)


def _glow(base, xy, r, col):
    g = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([xy[0] - r, xy[1] - r, xy[0] + r, xy[1] + r], fill=col)
    base.alpha_composite(g.filter(ImageFilter.GaussianBlur(r * 0.5)))


def _text(base, xy, s, f, fill=None, stroke=0, stroke_fill=None, shadow=None, anchor="la", grad=None):
    if shadow:
        sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((xy[0] + shadow[0], xy[1] + shadow[1]), s, font=f, fill=shadow[2], anchor=anchor,
                                stroke_width=stroke)
        base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(shadow[3])))
    d = ImageDraw.Draw(base)
    if grad:
        m = Image.new("L", base.size, 0)
        ImageDraw.Draw(m).text(xy, s, font=f, fill=255, anchor=anchor)
        box = m.getbbox() or (0, 0, 1, 1)
        g = Image.new("RGBA", base.size)
        gd = ImageDraw.Draw(g)
        for y in range(box[1], box[3] + 1):
            k = (y - box[1]) / max(1, box[3] - box[1])
            gd.line([(0, y), (base.size[0], y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(*grad)) + (255,))
        base.paste(g, (0, 0), m)
        return
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)


def _place(base: Image.Image, tiles_img: Image.Image, xy: tuple[int, int], strength: float = 0.38) -> None:
    """Tiles with a soft, close shadow under them (a studio product look), never hard blocks."""
    a = tiles_img.getchannel("A")
    shadow = Image.new("RGBA", tiles_img.size, (20, 20, 40, 0))
    shadow.putalpha(a.point(lambda v: int(v * strength)))
    pad = 60
    canvas = Image.new("RGBA", (tiles_img.size[0] + pad * 2, tiles_img.size[1] + pad * 2), (0, 0, 0, 0))
    canvas.alpha_composite(shadow, (pad + 6, pad + 26))
    canvas = canvas.filter(ImageFilter.GaussianBlur(22))
    base.alpha_composite(canvas, (xy[0] - pad, xy[1] - pad))
    base.alpha_composite(tiles_img, xy)


def _hex(h: str) -> tuple[int, int, int]:
    return tuple(int(h[k:k + 2], 16) for k in (0, 2, 4))


def _vivid(rgb, floor=90):
    """A brand colour bright enough to be the accent word (black brands become our purple)."""
    return rgb if max(rgb) >= floor and sum(rgb) > 160 else (124, 58, 255)


# ---------- the styles

def compose(style: str, words: str, punch: str, names: list[str], icons: list[dict], out: Path,
            tiles=render_tiles) -> Path:
    words = " ".join(str(words).split()).upper()
    punch = str(punch).strip().upper() or words.split()[-1]
    rest = " ".join(w for w in words.split() if w != punch) or words
    brand = _vivid(_hex(icons[0]["hex"])) if icons else (124, 58, 255)

    if style == "light_glass":
        b = _grad((244, 246, 255), (214, 224, 250))
        _grid(b, 44, (255, 255, 255, 120))
        _glow(b, (920, 360), 300, brand + (80,))
        t = tiles({"w": 700, "h": 720, "fov": 30, "dist": 13.5, "items": [
            _tile(icons[i], pos=p, rot=r, size=3.0 if len(icons) < 3 else 2.5)
            for i, (p, r) in enumerate([([-1.1, 0.7, 0], [8, 22, -8]), ([1.2, -1.1, 0.6], [-6, -24, 7]),
                                         ([0.9, 2.3, -0.6], [10, -10, 4])][:len(icons)])]})
        f1 = fit(rest, ANTON, 520, 230, 260)
        _text(b, (52, 70), rest, f1, (20, 20, 24), shadow=(0, 8, (40, 40, 120, 50), 12))
        f2 = fit(punch, ANTON, 520, 230, 220)
        _text(b, (52, 90 + f1.getbbox(rest)[3]), punch, f2, grad=(brand, tuple(int(c * 0.62) for c in brand)),
              shadow=(0, 8, (0, 0, 0, 60), 10))
        _place(b, t, (580, 0))

    elif style == "platter":
        b = _grad((252, 252, 252), (232, 232, 236))
        slug = "/" + "-".join(w.lower() for w in words.split())
        f = fit(slug, P9, 1150, 150, 130)
        _text(b, (60, 40), slug, f, (18, 18, 28))
        x1 = 60 + f.getbbox(slug)[2]
        d = ImageDraw.Draw(b)
        d.line([(70, 196), (x1 * 0.4, 186), (x1 * 0.75, 182), (x1 * 0.98, 190)], fill=(232, 40, 40), width=14)
        k = len(icons)
        size = min(3.4, 14.5 / max(k, 1))
        xs = [(i - (k - 1) / 2) * size * 1.13 for i in range(k)]
        mid = k // 2
        items = [_tile(icons[i], pos=[x, 0.3 + size * 0.11 + (0.4 if i == mid else 0), 0.6 if i == mid else 0],
                       rot=[4, x * -3, 0], size=size * (1.17 if i == mid else 1.0)) for i, x in enumerate(xs)]
        t = tiles({"w": 1280, "h": 520, "fov": 26, "dist": 17, "camY": 3.2, "items": items,
                   "platter": {"r": max(5.5, k * size * 0.62), "pos": [0, -0.75, -0.3]}})
        _place(b, t, (0, 210), 0.25)

    elif style == "dark_drama":
        b = _grad((8, 26, 28), (4, 10, 12))
        _glow(b, (900, 420), 330, brand + (120,))
        f1 = fit(rest, ANTON, 560, 200, 190)
        _text(b, (60, 40), rest, f1, (245, 245, 245), shadow=(0, 8, (0, 0, 0, 200), 8))
        f2 = fit(punch, ANTON, 560, 260, 240)
        _text(b, (60, 60 + f1.getbbox(rest)[3]), punch, f2, (238, 46, 46), stroke=6, stroke_fill=(60, 0, 0),
              shadow=(0, 10, (0, 0, 0, 220), 10))
        t = tiles({"w": 660, "h": 720, "fov": 30, "dist": 12.5,
                   "items": [_tile(icons[0], pos=[0, 0, 0], rot=[18, -28, -14], size=3.4)]})
        b.alpha_composite(t, (620, 0))

    elif style == "editorial":
        b = Image.new("RGBA", (W, H), (250, 250, 250, 255))
        d = ImageDraw.Draw(b)
        pill = icons[0].get("title") or (names[0] if names else rest).title()
        pf = fit(pill, P8, 520, 60, 52)
        pw = pf.getbbox(pill)[2] + 90
        d.rounded_rectangle([150, 46, 150 + pw, 140], 48, fill=(14, 14, 16))
        _text(b, (150 + pw / 2, 93), pill, pf, (255, 255, 255), anchor="mm")
        big = punch if len(punch) >= 3 else words
        fb = fit(big, ANTON, 860, 460, 420)
        bw = fb.getbbox(big)[2] - fb.getbbox(big)[0]
        _text(b, (70 + bw / 2, 440), big, fb, (14, 14, 16), anchor="mm")
        t = tiles({"w": 700, "h": 520, "fov": 30, "dist": 11,
                   "items": [_tile(icons[0], pos=[0, 0, 0], rot=[10, -30, 12], size=3.3)],
                   "chrome": [{"kind": "star", "pos": [-2.2, -1.4, 1], "rot": [20, 30, -15], "size": 1.0}]})
        _place(b, t, (min(W - 600, 70 + bw - 260), 230))

    elif style == "grid_paper":
        b = Image.new("RGBA", (W, H), (244, 240, 230, 255))
        _grid(b, 40, (226, 220, 206, 255), 2)
        top = rest.title()
        _text(b, (50, 40), top, fit(top, P9, 520, 160, 150), (16, 16, 18))
        _text(b, (50, 200), punch.title() + ".", fit(punch.title() + ".", SERIF_I, 520, 150, 128), (226, 24, 112))
        d = ImageDraw.Draw(b)
        pts = [(150 + t * 6, 420 + 60 * math.sin(t / 9)) for t in range(0, 52)]
        for k in range(0, len(pts) - 1, 2):
            d.line([pts[k], pts[k + 1]], fill=(226, 24, 112), width=7)
        d.polygon([(468, 420), (430, 395), (432, 448)], fill=(226, 24, 112))
        spots = [([-2.6, 0.9, 0], [6, 20, -10]), ([2.5, 1.0, -0.4], [-4, -18, 9]), ([0.0, -1.4, 0.9], [-8, 4, -3])]
        t = tiles({"w": 720, "h": 690, "fov": 30, "dist": 15, "items": [
            _tile(icons[i], pos=p, rot=r, size=2.9, badge="e8197a") for i, (p, r) in enumerate(spots[:len(icons)])]})
        _place(b, t, (560, 30))
    else:
        raise ValueError(f"unknown style {style}")
    out.parent.mkdir(parents=True, exist_ok=True)
    b.convert("RGB").save(out, quality=94)
    return out


def make(title: str, words: str, punch: str, brands: list[str], n: int, out: Path, tiles=render_tiles) -> str | None:
    """The styled thumbnail when the story has at least one real logo; None otherwise."""
    found = [(b, logos.find(b)) for b in brands]
    found = [(b, i) for b, i in found if i][:6]
    if not found:
        return None
    names, icons = [b for b, _ in found], [i for _, i in found]
    style = choose(title, len(icons), n)
    if style != "platter":
        names, icons = names[:3], icons[:3]
    compose(style, words, punch, names, icons, out, tiles=tiles)
    return style
