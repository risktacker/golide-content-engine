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

def goli(pose: str = "point_left", outfit: str = "royal", mouth: str = "C", expression: str | None = None,
         height: int = 760, upper: float = 0.8) -> Image.Image:
    """Goli as a transparent cut-out for a thumbnail (owner 2026-11-12: our host replaces the person in
    the reference thumbnails). `upper` keeps the top part (head and chest) so his face reads big."""
    from playwright.sync_api import sync_playwright

    from ..edit import mascot

    w = 1200
    svg = mascot.svg(pose, width=w, mouth=mouth, outfit=outfit, expression=expression)
    # room around the character: a pointing arm or raised hands reach past the 400 x 540 drawing box
    svg = re.sub(r'height="\d+" viewBox="0 0 400 540"', f'height="{w * 620 // 720}" viewBox="-160 -40 720 620"', svg, 1)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": w, "height": w * 620 // 720})
        page.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
        png = page.locator("svg").first.screenshot(omit_background=True)
        browser.close()
    import io

    img = Image.open(io.BytesIO(png)).convert("RGBA")
    box = img.getbbox()
    img = img.crop(box) if box else img
    img = img.crop((0, 0, img.width, int(img.height * upper)))
    k = height / img.height
    return img.resize((int(img.width * k), height), Image.LANCZOS)


# each style's Goli: pose, mouth, where his cut-out stands (x of its centre, height), and where the
# tiles go instead when he is in the picture, so words, tiles and Goli never cover each other
GOLI = {
    "light_glass": ("point_left", "C", None, 1040, 640),
    "dark_drama": ("shock", "E", "shock", 1040, 620),
    "editorial": ("point_left", "B", "sure", 1060, 620),
    "grid_paper": ("thumbs_up", "D", "happy", 1040, 620),
    "platter": ("point_left", "B", "sure", 1070, 560),
    "photo_card": ("shock", "D", "shock", 1080, 620),
    "words": ("point_left", "C", "sure", 1040, 660),
    "studio": ("point", "C", "sure", 335, 640),
}
ZONE = 860            # with Goli in the picture, words and tiles stay left of this line; he owns the right


STUDIO = ROOT / "assets" / "thumbs" / "studio-backdrop.jpg"   # Goli's own set, empty (rendered from edit/studio.py)
SCREEN = (749, 69, 1235, 433)       # the set's big screen, in the 1280 x 720 thumbnail


def _studio_bg(screen: Image.Image | None = None, glow: tuple = (64, 110, 255)) -> Image.Image:
    """2026-11-12 (owner): a thumbnail is a picture of a real place: Goli's studio behind him, a little
    out of focus like a camera shot, with the story's own thing on the big screen."""
    b = Image.open(STUDIO).convert("RGBA").resize((W, H), Image.LANCZOS)
    if screen is not None:
        x0, y0, x1, y1 = SCREEN
        pic = screen.convert("RGBA")
        k = max((x1 - x0) / pic.width, (y1 - y0) / pic.height)
        pic = pic.resize((int(pic.width * k) + 1, int(pic.height * k) + 1), Image.LANCZOS)
        pic = pic.crop(((pic.width - (x1 - x0)) // 2, (pic.height - (y1 - y0)) // 2,
                        (pic.width + (x1 - x0)) // 2, (pic.height + (y1 - y0)) // 2))
        mask = Image.new("L", pic.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, pic.width - 1, pic.height - 1], 10, fill=255)
        b.paste(pic, (x0, y0), mask)
        _glow(b, ((x0 + x1) // 2, (y0 + y1) // 2), 300, glow + (60,))
    b = b.filter(ImageFilter.GaussianBlur(3.2))                    # depth of field: the set sits behind
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(shade)
    for i in range(H // 2):                                          # darker toward the bottom: words sit there
        d.line([(0, H - i), (W, H - i)], fill=(4, 6, 12, int(200 * (1 - i / (H / 2)) ** 1.4)))
    b.alpha_composite(shade)
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-260, -200, W + 260, H + 200], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(120))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 170))
    dark.putalpha(Image.eval(vig, lambda v: int(170 * (1 - v / 255))))
    b.alpha_composite(dark)
    return b


def _rim(cut: Image.Image, colour: tuple = (120, 170, 255)) -> Image.Image:
    """A thin back-light around Goli so he separates from the set (studio lighting)."""
    a = cut.getchannel("A")
    halo = Image.new("RGBA", cut.size, colour + (0,))
    halo.putalpha(a.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(6)))
    out = Image.new("RGBA", cut.size, (0, 0, 0, 0))
    out.alpha_composite(halo)
    out.alpha_composite(cut)
    return out


def _big(b: Image.Image, xy: tuple, text: str, font, fill, depth: int = 10, edge=(0, 0, 0)) -> None:
    """Thumbnail lettering: heavy outline and an extruded 3D block under the face."""
    x, y = xy
    d = ImageDraw.Draw(b)
    for k in range(depth, 0, -1):
        d.text((x + k * .6, y + k), text, font=font, fill=tuple(int(c * .35) for c in fill), stroke_width=8,
               stroke_fill=edge)
    d.text((x, y), text, font=font, fill=fill, stroke_width=8, stroke_fill=edge)


def _paste_goli(b: Image.Image, cut: Image.Image, cx: int) -> None:
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([cx - cut.width * .38, H - 34, cx + cut.width * .38, H + 30], fill=(0, 0, 0, 90))
    b.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))
    b.alpha_composite(cut, (int(cx - cut.width / 2), H - cut.height))


def compose(style: str, words: str, punch: str, names: list[str], icons: list[dict], out: Path,
            tiles=render_tiles, host: Image.Image | None = None, photo: Path | None = None) -> Path:
    words = " ".join(str(words).split()).upper()
    punch = str(punch).strip().upper() or words.split()[-1]
    rest = " ".join(words.replace(punch, " ").split()) if punch and punch in words else words
    rest = rest or words
    brand = _vivid(_hex(icons[0]["hex"])) if icons else (124, 58, 255)

    if style == "light_glass":
        b = _grad((244, 246, 255), (214, 224, 250))
        _grid(b, 44, (255, 255, 255, 120))
        _glow(b, (920, 360), 300, brand + (80,))
        t = tiles({"w": 700, "h": 720, "fov": 30, "dist": 13.5, "items": [
            _tile(icons[i], pos=p, rot=r, size=3.0 if len(icons) < 3 else 2.5)
            for i, (p, r) in enumerate([([-1.1, 0.7, 0], [8, 22, -8]), ([1.2, -1.1, 0.6], [-6, -24, 7]),
                                         ([0.9, 2.3, -0.6], [10, -10, 4])][:len(icons)])]})
        tw = 470 if host is not None and icons else 520
        f1 = fit(rest, ANTON, tw, 230, 260)
        _text(b, (52, 70), rest, f1, (20, 20, 24), shadow=(0, 8, (40, 40, 120, 50), 12))
        f2 = fit(punch, ANTON, tw, 230, 220)
        _text(b, (52, 90 + f1.getbbox(rest)[3]), punch, f2, grad=(brand, tuple(int(c * 0.62) for c in brand)),
              shadow=(0, 8, (0, 0, 0, 60), 10))
        if host is not None:
            t = t.resize((int(t.width * .5), int(t.height * .5)), Image.LANCZOS)
            # under the words, toward Goli's pointing hand: never on the words
            low = 90 + f1.getbbox(rest)[3] + f2.getbbox(punch)[3]
            _place(b, t, (ZONE - t.width - 150, min(H - t.height, low - 30)))
        else:
            _place(b, t, (580, 0))

    elif style == "platter":
        b = _grad((252, 252, 252), (232, 232, 236))
        slug = "/" + "-".join(w.lower() for w in words.split())
        f = fit(slug, P9, ZONE - 80 if host is not None else 1150, 150, 130)
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
        if host is not None:
            t = t.resize((int(t.width * .66), int(t.height * .66)), Image.LANCZOS)
            _place(b, t, (0, 300), 0.25)
        else:
            _place(b, t, (0, 210), 0.25)

    elif style == "dark_drama":
        b = _grad((8, 26, 28), (4, 10, 12))
        _glow(b, (900, 420), 330, brand + (120,))
        tw = 500 if host is not None else 560
        f1 = fit(rest, ANTON, tw, 200, 190)
        _text(b, (60, 40), rest, f1, (245, 245, 245), shadow=(0, 8, (0, 0, 0, 200), 8))
        f2 = fit(punch, ANTON, tw, 260, 240)
        _text(b, (60, 60 + f1.getbbox(rest)[3]), punch, f2, (238, 46, 46), stroke=6, stroke_fill=(60, 0, 0),
              shadow=(0, 10, (0, 0, 0, 220), 10))
        t = tiles({"w": 660, "h": 720, "fov": 30, "dist": 12.5,
                   "items": [_tile(icons[0], pos=[0, 0, 0], rot=[18, -28, -14], size=3.4)]})
        if host is not None:
            t = t.resize((int(t.width * .5), int(t.height * .5)), Image.LANCZOS)
            b.alpha_composite(t, (ZONE - t.width - 260, H - t.height - 10))
        else:
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
        fb = fit(big, ANTON, 600 if host is not None else 860, 460, 420)
        bw = fb.getbbox(big)[2] - fb.getbbox(big)[0]
        _text(b, (70 + bw / 2, 440), big, fb, (14, 14, 16), anchor="mm")
        t = tiles({"w": 700, "h": 520, "fov": 30, "dist": 11,
                   "items": [_tile(icons[0], pos=[0, 0, 0], rot=[10, -30, 12], size=3.3)],
                   "chrome": [{"kind": "star", "pos": [-2.2, -1.4, 1], "rot": [20, 30, -15], "size": 1.0}]})
        if host is not None:
            t = t.resize((int(t.width * .5), int(t.height * .5)), Image.LANCZOS)
            _place(b, t, (min(ZONE - t.width - 40, 70 + bw - 120), 420))
        else:
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
        if host is not None:
            t = t.resize((int(t.width * .55), int(t.height * .55)), Image.LANCZOS)
            _place(b, t, (ZONE - t.width - 160, 300))
        else:
            _place(b, t, (560, 30))
    elif style == "photo_card":
        # no logo in the story: the source's own real picture, framed and tilted, Goli beside it
        b = _grad((16, 20, 34), (6, 8, 14))
        _glow(b, (640, 420), 360, (64, 110, 255, 90))
        f1 = fit(rest, ANTON, 640, 170, 170)
        _text(b, (44, 24), rest, f1, (246, 246, 246), shadow=(0, 8, (0, 0, 0, 200), 8))
        f2 = fit(punch, ANTON, 640, 200, 200)
        _text(b, (44, 34 + f1.getbbox(rest)[3]), punch, f2, (250, 204, 21), stroke=5, stroke_fill=(60, 40, 0),
              shadow=(0, 10, (0, 0, 0, 220), 10))
        top = 34 + f1.getbbox(rest)[3] + f2.getbbox(punch)[3] + 20
        pic = Image.open(photo).convert("RGB")
        pic.thumbnail((640, max(200, H - top - 40)))
        frame = Image.new("RGBA", (pic.width + 16, pic.height + 16), (232, 194, 104, 255))
        frame.paste(pic, (8, 8))
        frame = frame.rotate(-4, expand=True, resample=Image.BICUBIC)
        b.alpha_composite(frame, (50, top))
    elif style == "studio":
        # Goli in his studio, pointing at the story on the big screen; the words under it
        screen = Image.open(photo).convert("RGB") if photo and Path(photo).exists() else None
        if screen is None and icons:
            screen = Image.new("RGBA", (640, 480), (10, 14, 26, 255))
            _glow(screen, (320, 240), 260, _vivid(_hex(icons[0]["hex"])) + (150,))
            t = tiles({"w": 480, "h": 480, "fov": 30, "dist": 10,
                       "items": [_tile(icons[0], pos=[0, 0, 0], rot=[10, -22, 6], size=3.4)]})
            screen.alpha_composite(t, (80, 0))
        alert = is_alert(words)
        b = _studio_bg(screen, (238, 46, 46) if alert else brand)
        f1 = fit(rest, ANTON, 620, 96, 100)
        f2 = fit(punch, ANTON, 620, 170, 170)
        h1 = f1.getbbox(rest)[3]
        y0 = H - 24 - h1 - 12 - f2.getbbox(punch)[3]
        _big(b, (620, y0), rest, f1, (248, 248, 248), depth=6)
        _big(b, (620, y0 + h1 + 12), punch, f2, (238, 46, 46) if alert else (250, 204, 21), depth=12,
             edge=(30, 6, 6) if alert else (40, 28, 0))
    elif style == "words":
        # no logo and no picture: Goli and the big words on the house glass look
        b = _grad((244, 246, 255), (214, 224, 250))
        _grid(b, 44, (255, 255, 255, 120))
        _glow(b, (1000, 380), 320, (124, 58, 255, 70))
        f1 = fit(rest, ANTON, 700, 260, 260)
        _text(b, (52, 60), rest, f1, (20, 20, 24), shadow=(0, 8, (40, 40, 120, 50), 12))
        f2 = fit(punch, ANTON, 700, 280, 260)
        _text(b, (52, 80 + f1.getbbox(rest)[3]), punch, f2, grad=((124, 58, 255), (70, 30, 160)),
              shadow=(0, 8, (0, 0, 0, 60), 10))
    else:
        raise ValueError(f"unknown style {style}")
    if host is not None:
        _paste_goli(b, _rim(host) if style == "studio" else host, GOLI[style][3])
    out.parent.mkdir(parents=True, exist_ok=True)
    b.convert("RGB").save(out, quality=94)
    return out


def make(title: str, words: str, punch: str, brands: list[str], n: int, out: Path, tiles=render_tiles,
         outfit: str | None = None, photo: Path | None = None, with_goli: bool = True) -> str | None:
    """The styled thumbnail: real logos as glossy tiles, or the source's real picture, with Goli as the
    host (owner 2026-11-12). Every story gets one; nothing is generated."""
    found = [(b, logos.find(b)) for b in brands]
    found = [(b, i) for b, i in found if i][:6]
    names, icons = [b for b, _ in found], [i for _, i in found]
    if icons:
        style = choose(title, len(icons), n)
        if style != "platter":
            names, icons = names[:3], icons[:3]
    elif photo and Path(photo).exists():
        style = "photo_card"
    elif with_goli:
        style = "words"
    else:
        return None
    host = None
    if with_goli:
        pose, mouth, expression, _, height = GOLI[style]
        host = goli(pose, outfit or "royal", mouth, expression, height)
    compose(style, words, punch, names, icons, out, tiles=tiles, host=host, photo=photo)
    return style
