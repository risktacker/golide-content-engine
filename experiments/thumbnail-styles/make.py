import json, math, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
SP = Path("/tmp/claude-0/-home-claude/8d1d9704-a447-57ad-8375-b80b30d6e36f/scratchpad")
TH = SP / "th"; OUT = TH / "out"; OUT.mkdir(exist_ok=True)
ICONS = json.load(open(SP / "logocache/16.37.0/index.json"))
F = TH / "fonts"
def font(name, size): return ImageFont.truetype(str(F / name), size)
ANTON, ARCH, BEBAS = "anton-latin-400-normal.woff", "archivo-black-latin-400-normal.woff", "bebas-neue-latin-400-normal.woff"
P9, P8, P9I = "poppins-latin-900-normal.woff", "poppins-latin-800-normal.woff", "poppins-latin-900-italic.woff"
SERIF_I = "dm-serif-display-latin-400-italic.woff"
W, H = 1280, 720

def tile(slug, **kw):
    i = ICONS[slug]; hexs = i["hex"]
    light = sum(int(hexs[k:k + 2], 16) for k in (0, 2, 4)) / 3 > 200
    d = dict(svg=i["svg"], hex=hexs, mark="111111" if light else "ffffff")
    if hexs in ("000000", "191919", "181717"): d.update(hex="1b1c22")
    d.update(kw); return d

specs = []
def icons(name, w, h, items, **kw):
    s = dict(out=str(OUT / f"{name}.png"), w=w, h=h, items=items, **kw); specs.append(s); return s["out"]

# ---- 3D renders
icons("e1", 900, 720, [tile("claude", pos=[-1.5, 0.5, 0], rot=[8, 22, -8], size=3.1),
                        tile("blender", pos=[1.7, -0.9, 0.6], rot=[-6, -24, 7], size=3.1)], fov=30, dist=13, shadow=0.18)
icons("e2", 1280, 520, [tile(s, pos=[x, 0.55, 0], rot=[4, x * -3, 0], size=2.3) for s, x in
                        zip(["googlegemini", "perplexity"], [-6.9, -4.3])]
                       + [tile("claude", pos=[-1.3, 0.95, 0.6], rot=[4, 0, 0], size=2.7)]
                       + [tile(s, pos=[x, 0.55, 0], rot=[4, x * -3, 0], size=2.3) for s, x in
                          zip(["github", "meta", "youtube"], [1.6, 4.3, 7.0])],
       platter=dict(r=7.8, pos=[0.4, -0.75, -0.3]), fov=26, dist=17, camY=3.2, exposure=1.0)
icons("e3", 700, 720, [tile("nvidia", pos=[0, 0, 0], rot=[18, -28, -14], size=3.6)], fov=30, dist=12)
icons("e4", 700, 520, [tile("tesla", pos=[0, 0, 0], rot=[10, -30, 12], size=3.3)], fov=30, dist=11,
      chrome=[dict(kind="star", pos=[-2.2, -1.4, 1], rot=[20, 30, -15], size=1.0)])
icons("e5", 720, 690, [tile("github", pos=[-2.6, 0.9, 0], rot=[6, 20, -10], size=2.9, badge="e8197a"),
                         tile("figma", pos=[2.5, 1.0, -0.4], rot=[-4, -18, 9], size=2.9, badge="e8197a", hex="F5F5F7", mark="111111"),
                         tile("python", pos=[0.0, -1.4, 0.9], rot=[-8, 4, -3], size=3.1, badge="e8197a")], fov=30, dist=15, shadow=0.22)
icons("e6", 560, 560, [tile("claude", pos=[0, 0, 0], rot=[12, -26, 10], size=3.2, style="glass", mark="d97757")], fov=30, dist=10)
subprocess.run(["node", str(TH / "icons.js"), str(TH / "specs.json")], check=True) if not json.dump(specs, open(TH / "specs.json", "w")) else None

def paste(base, img, xy, shadow=0):
    img = Image.open(img).convert("RGBA") if isinstance(img, (str, Path)) else img
    if shadow:
        s = Image.new("RGBA", img.size, (0, 0, 0, 0)); s.putalpha(img.getchannel("A").point(lambda v: int(v * shadow)))
        base.alpha_composite(s.filter(ImageFilter.GaussianBlur(14)), (xy[0] + 8, xy[1] + 18))
    base.alpha_composite(img, xy)

def text(base, xy, s, f, fill, stroke=0, stroke_fill=None, shadow=None, anchor="la", grad=None):
    d = ImageDraw.Draw(base)
    if shadow:
        sh = Image.new("RGBA", base.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text((xy[0] + shadow[0], xy[1] + shadow[1]), s, font=f, fill=shadow[2], anchor=anchor, stroke_width=stroke)
        base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(shadow[3])))
    if grad:   # vertical gradient fill
        m = Image.new("L", base.size, 0); ImageDraw.Draw(m).text(xy, s, font=f, fill=255, anchor=anchor)
        g = Image.new("RGBA", base.size); gd = ImageDraw.Draw(g); x0, y0, x1, y1 = m.getbbox()
        for y in range(y0, y1 + 1):
            k = (y - y0) / max(1, y1 - y0); gd.line([(0, y), (base.size[0], y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(grad[0], grad[1])) + (255,))
        if stroke: d.text(xy, s, font=f, fill=stroke_fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)
        base.paste(g, (0, 0), m); return
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)

def bg_grad(top, bottom, w=W, h=H):
    g = Image.new("RGBA", (w, h)); d = ImageDraw.Draw(g)
    for y in range(h):
        k = y / h; d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(top, bottom)) + (255,))
    return g

def grid(base, step, col, width=1):
    d = ImageDraw.Draw(base)
    for x in range(0, base.size[0], step): d.line([(x, 0), (x, base.size[1])], fill=col, width=width)
    for y in range(0, base.size[1], step): d.line([(0, y), (base.size[0], y)], fill=col, width=width)

def glow(base, xy, r, col):
    g = Image.new("RGBA", base.size, (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([xy[0] - r, xy[1] - r, xy[0] + r, xy[1] + r], fill=col)
    base.alpha_composite(g.filter(ImageFilter.GaussianBlur(r * 0.5)))

# 1. LIGHT GLASS (Brendan Jowett style): light airy background, giant heavy type, two big glossy tiles
b = bg_grad((244, 246, 255), (214, 224, 250)); grid(b, 44, (255, 255, 255, 120))
glow(b, (920, 360), 300, (160, 140, 255, 90))
text(b, (52, 70), "3D", font(ANTON, 300), (20, 20, 24), shadow=(0, 10, (40, 40, 120, 70), 12))
text(b, (52, 400), "RENDERS", font(ANTON, 170), None, grad=((140, 60, 255), (86, 20, 220)), shadow=(0, 8, (60, 0, 160, 90), 10))
text(b, (58, 600), "WITH CLAUDE + BLENDER", font(P9, 40), (24, 24, 30))
paste(b, OUT / "e1.png", (400, 0), shadow=0.0)
b.convert("RGB").save(OUT / "1-light-glass.jpg", quality=92)

# 2. PLATTER ROW (Matt Penny style): white, slash title with red swoosh, icons on a chrome platter
b = bg_grad((252, 252, 252), (232, 232, 236))
text(b, (60, 40), "/ai-video-tools", font(P9, 116), (18, 18, 28))
d = ImageDraw.Draw(b); d.line([(70, 196), (300, 186), (560, 182), (760, 190)], fill=(232, 40, 40), width=14, joint="curve")
paste(b, OUT / "e2.png", (0, 210), shadow=0.0)
b.convert("RGB").save(OUT / "2-platter-row.jpg", quality=92)

# 3. DARK DRAMA (Paper Billions style, no person): deep teal-green night, brand glow, giant white + red
b = bg_grad((8, 26, 28), (4, 10, 12)); glow(b, (900, 420), 330, (118, 185, 0, 120))
text(b, (60, 40), "NVIDIA", font(ANTON, 190), (245, 245, 245), shadow=(0, 8, (0, 0, 0, 200), 8))
text(b, (60, 250), "-$400B", font(ANTON, 240), (238, 46, 46), stroke=6, stroke_fill=(60, 0, 0), shadow=(0, 10, (0, 0, 0, 220), 10))
text(b, (66, 560), "IN ONE DAY", font(P9, 56), (200, 255, 120))
paste(b, OUT / "e3.png", (600, 0))
b.convert("RGB").save(OUT / "3-dark-drama.jpg", quality=92)

# 4. EDITORIAL BIG TYPE (RoundUp style): white, one massive word, a 3D logo cutting through it
b = Image.new("RGBA", (W, H), (250, 250, 250, 255))
d = ImageDraw.Draw(b); d.rounded_rectangle([150, 46, 640, 140], 48, fill=(14, 14, 16))
text(b, (395, 93), "Tesla Roadster", font(P8, 52), (255, 255, 255), anchor="mm")
text(b, (560, 440), "FLIES?", font(ANTON, 420), (14, 14, 16), anchor="mm")
paste(b, OUT / "e4.png", (760, 260), shadow=0.25)
b.convert("RGB").save(OUT / "4-editorial-type.jpg", quality=92)

# 5. GRID PAPER + SCRIPT (Free & Unlimited style): cream grid, black + magenta italic, dashed arrow, tiles with badges
b = Image.new("RGBA", (W, H), (244, 240, 230, 255)); grid(b, 40, (226, 220, 206, 255), 2)
text(b, (50, 40), "Free &", font(P9, 150), (16, 16, 18))
text(b, (50, 200), "Unlimited.", font(SERIF_I, 128), (226, 24, 112))
d = ImageDraw.Draw(b)
pts = [(150 + t * 6, 420 + 60 * math.sin(t / 9)) for t in range(0, 52)]
for k in range(0, len(pts) - 1, 2): d.line([pts[k], pts[k + 1]], fill=(226, 24, 112), width=7)
d.polygon([(468, 420), (430, 395), (432, 448)], fill=(226, 24, 112))
paste(b, OUT / "e5.png", (560, 30), shadow=0.0)
b.convert("RGB").save(OUT / "5-grid-paper.jpg", quality=92)

# 6. REAL OBJECT + HIGHLIGHT (F-47 style): the real machine, cyan dashed highlight, bold caption
hero = Image.open(SP / "rb/frames/s0000.jpg").convert("RGBA").crop((300, 60, 1180, 555)).resize((W, H))
b = bg_grad((70, 86, 104), (28, 34, 44)); b.alpha_composite(Image.eval(hero, lambda v: v), (0, 0))
b = Image.blend(bg_grad((70, 86, 104), (28, 34, 44)), b, 0.85)
d = ImageDraw.Draw(b)
def dashed(points, col, w=6, dash=18):
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        L = math.hypot(x1 - x0, y1 - y0); n = int(L // dash)
        for i in range(0, n, 2):
            a, c = i / n, min(1, (i + 1) / n); d.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * c, y0 + (y1 - y0) * c)], fill=col, width=w)
dashed([(660, 60), (830, 345), (790, 360), (660, 60)], (80, 230, 255), 7)
glow(b, (760, 260), 110, (80, 230, 255, 50))
text(b, (640, 560), "Why Each Blade", font(P9, 70), (255, 255, 255), stroke=5, stroke_fill=(0, 0, 0), anchor="mm")
text(b, (640, 645), "Is 55 m Long", font(P9, 70), (255, 255, 255), stroke=5, stroke_fill=(0, 0, 0), anchor="mm")
b.convert("RGB").save(OUT / "6-real-object.jpg", quality=92)

# contact sheet
names = ["1-light-glass", "2-platter-row", "3-dark-drama", "4-editorial-type", "5-grid-paper", "6-real-object"]
sheet = Image.new("RGB", (2 * 640 + 30, 3 * 360 + 40), (30, 30, 34))
for i, n in enumerate(names):
    sheet.paste(Image.open(OUT / f"{n}.jpg").resize((640, 360)), (10 + (i % 2) * 650, 10 + (i // 2) * 370))
sheet.save(OUT / "sheet.jpg", quality=88)
print("ok")
