"""More places for ReachMora (owner 2026-11-21: "it's the whole world"), drawn in the kit's own ink style.

Loaded into the kit's engine.sets.SETS by rm_hook/sitecustomize.py (the kit's files are never edited). Every set
draws its static background on the 1920x1080 design canvas (with room beyond the edges for camera moves) and returns
the kit's info dict. Characters stand at FLOOR (1010), the kit's default for sets it does not know.
Options every set reads: time (day/dusk/night), and where it fits text (a sign, a logo name), wall/colour.
"""
import math
import random

import skia
from engine.kit import *  # noqa: F401,F403  (the kit's drawing helpers: rect, circ, poly, line, label, fp, ...)
from engine.sets import AMBIENT, block, cloud, far_city, moon, plant, sky, stars, sun, wall_clock

FLOOR = 1010
L0, R0 = -900, W + 900       # draw past the frame for camera moves
STEEL = '#8C95A6'; DARKSTEEL = '#4A5163'; WOOD = '#8E5C36'; DARKWOOD = '#5A3A22'


def _in_band(x):
    """Characters stand between x 250 and 1670 (the writer's rule): no pole or pillar there, it would grow out of a head."""
    return 230 <= x <= 1690


def _info(time='day', lights=(), bulbs=(), floor=FLOOR, spots=((520, FLOOR), (960, FLOOR), (1400, FLOOR))):
    return dict(floor=floor, ambient=AMBIENT.get(time, AMBIENT['day']), lights=list(lights), bulbs=list(bulbs), spots=list(spots))


def _room(c, wall, floor_col, horizon=820, stripe=None, boards=True):
    c.drawRect(skia.Rect(L0, -700, R0, horizon), fp(wall))
    if stripe:
        for i in range(-14, 48): c.drawLine(i * 62, -700, i * 62, horizon, ink(8, stripe))
    c.drawRect(skia.Rect(L0, horizon, R0, H + 700), fp(floor_col))
    if boards:
        for i in range(-12, 40): c.drawLine(960 + (i - 14) * 70, horizon, 960 + (i - 14) * 300, H + 400, ink(3, shade(floor_col, .86)))
    line(c, L0, horizon, R0, horizon, LW)


def _sky(c, time, h):
    sky(c, time, h)
    if time == 'night': stars(c); moon(c, 1560, 150, 40)
    elif time == 'day': sun(c, 1580, 170, 62); cloud(c, 420, 220, 1.1, '#FFFFFF', 235); cloud(c, 1150, 300, .8, '#FFFFFF', 220)
    else: cloud(c, 650, 250, 1.1, '#E58A7A')


def _ground(c, top, col, line_=True):
    c.drawRect(skia.Rect(L0, top, R0, H + 700), fp(col))
    if line_: line(c, L0, top, R0, top, LW)


_LOGOS = {}


def _dark(hexc):
    h = str(hexc).lstrip("#"); r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return .2126 * r + .7152 * g + .0722 * b < 128


def brand(c, art, cx, cy, size, dark_bg=True):
    """A real brand mark (simple-icons SVG attached to the story by longform.attach_logos) drawn at its own colour;
    a mark too dark for a dark sign is drawn white. Returns False when there is no mark."""
    if not isinstance(art, dict) or not art.get("svg"):
        return False
    hexc = "#" + str(art.get("hex") or "FFFFFF").lstrip("#")
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    lum = .2126 * r + .7152 * g + .0722 * b
    if dark_bg and lum < 70: hexc = "#FFFFFF"
    if not dark_bg and lum > 215: hexc = "#1C1C22"
    px = max(8, int(size * OS * 1.5))
    key = (art["svg"][:200], hexc, px)
    if key not in _LOGOS:
        svg = art["svg"].replace("<svg ", f'<svg fill="{hexc}" width="{px}" height="{px}" ', 1)
        dom = skia.SVGDOM.MakeFromStream(skia.MemoryStream(svg.encode()))
        if dom is None:                      # a mark skia cannot read: the name stays in text, the shot still draws
            _LOGOS[key] = None
        else:
            surf = skia.Surface(px, px); cv = surf.getCanvas(); cv.clear(skia.ColorTRANSPARENT)
            dom.setContainerSize(skia.Size(px, px)); dom.render(cv); _LOGOS[key] = surf.makeImageSnapshot()
    if _LOGOS[key] is None:
        return False
    c.drawImageRect(_LOGOS[key], skia.Rect(cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2), LINEAR)
    return True


def _sign(c, text, x, y, w, h, fill, colr='#FFFFFF', size=70, art=None):
    """A sign; with a real logo (art) the mark stands at its left and the name beside it."""
    rect(c, x - w / 2, y - h / 2, x + w / 2, y + h / 2, fill, LW, r=14)
    if art and art.get("svg"):
        m = h * .7; brand(c, art, x - w / 2 + 20 + m / 2, y, m, dark_bg=_dark(fill))
        tx = x + (20 + m) / 2
        label(c, text, tx, y + size * .34, fit_size(text, size, w - 70 - m), colr, align='center', skew=0)
    else:
        label(c, text, x, y + size * .34, fit_size(text, size, w - 40), colr, align='center', skew=0)


def _screen(c, x0, y0, x1, y1, kind='up', seed=1):
    rect(c, x0, y0, x1, y1, '#1A1D2A', LW, r=8)
    r = random.Random(seed); n = 9; pts = []; v = .5
    for i in range(n):
        v = min(.9, max(.1, v + r.uniform(-.18, .18) + (.06 if kind == 'up' else -.06)))
        pts.append((x0 + 20 + i * (x1 - x0 - 40) / (n - 1), y1 - 20 - v * (y1 - y0 - 40)))
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    c.drawPath(p, ink(5, '#5FCB72' if kind == 'up' else '#FF5A5A'))


def _person_dot(c, x, y, s, col):
    circ(c, x, y - 40 * s, 22 * s, '#E6BE8E', LW * .5 * s); rect(c, x - 26 * s, y - 18 * s, x + 26 * s, y + 30 * s, col, LW * .5 * s, r=12 * s)


def _tree(c, x, y, s=1.0, col='#3E9A56', kind='round'):
    rect(c, x - 12 * s, y - 90 * s, x + 12 * s, y, '#6A4428', LW * .7)
    if kind == 'pine':
        for k in range(3): poly(c, [(x - (90 - k * 18) * s, y - (70 + k * 70) * s), (x + (90 - k * 18) * s, y - (70 + k * 70) * s), (x, y - (190 + k * 70) * s)], col, LW * .7)
    else:
        for (dx, dy, r) in ((-40, -130, 70), (40, -130, 70), (0, -190, 80)): circ(c, x + dx * s, y + dy * s, r * s, col, LW * .7)


# ---------------------------------------------------------------- tech
def set_datacenter(c, o):
    """High-tech data-centre aisle (owner's model, @afterhourtheories): bright white hall, white racks with dark faces
    and cyan lights, yellow and blue cable trays on top, light bars above, a red sign at the far end."""
    vx, vy = 960, 520
    c.drawRect(skia.Rect(L0, -700, R0, H + 700), fp('#E6E8EE'))
    c.drawRect(skia.Rect(L0, 780, R0, H + 700), fp('#D8DBE2'))
    for i in range(-10, 11): c.drawLine(vx + i * 28, vy, vx + i * 420, H + 300, ink(2, '#C4C8D2'))
    for k in range(8): yy = 780 + k * k * 9; c.drawLine(L0, yy, R0, yy, ink(2, '#C4C8D2'))
    for k in range(6):                                            # ceiling light bars running to the end
        f = 1 - k / 6.0; w = 60 + 200 * f ** 1.6; y = vy - 120 - 520 * f ** 1.6
        rect(c, vx - w / 2 - 6, y - 10 * f - 4, vx + w / 2 + 6, y + 10 * f + 4, '#F8FAFF', LW * .4)
    sign = (o.get('sign') or '').upper()
    rect(c, vx - 230, vy - 150, vx + 230, vy - 40, '#E04848', LW * .7)
    if sign: label(c, sign, vx, vy - 75, fit_size(sign, 56, 420), '#F2C14E', align='center', skew=0)
    rect(c, vx - 150, vy - 40, vx + 150, vy + 60, '#FFFFFF', LW * .5)
    for side in (-1, 1):
        for k in range(7):
            f0, f1 = 1 - k / 7.0, 1 - (k + 1) / 7.0
            xa, xb = vx + side * (160 + 1100 * f0 ** 1.6), vx + side * (160 + 1100 * f1 ** 1.6)
            ta, tb = vy - 40 - 520 * f0 ** 1.6, vy - 40 - 520 * f1 ** 1.6
            ba, bb = vy + 60 + 640 * f0 ** 1.6, vy + 60 + 640 * f1 ** 1.6
            poly(c, [(xa, ta), (xb, tb), (xb, bb), (xa, ba)], '#2E333F', LW * .5)
            inset = (xb - xa) * .08
            poly(c, [(xa, ta), (xa + inset, ta), (xa + inset, ba), (xa, ba)], '#F4F5F8', 0)
            for j in range(1, 9):
                ya, yb = ta + (ba - ta) * j / 9, tb + (bb - tb) * j / 9
                c.drawLine(xa, ya, xb, yb, ink(max(1, 2 * f0), '#454B5A'))
                lx = xa + (xb - xa) * .7; ly = ya + (yb - ya) * .7 - 6 * f0
                c.drawCircle(lx, ly, max(1.5, 4 * f0), fp('#5FE0E0' if (j + k) % 3 else '#5FE08A'))
            for (dy, colr, h) in ((-60, '#3B6EA8', 26), (-100, '#F2C14E', 34)):   # trays on top of the racks
                h0, h1 = h * f0 + 2, h * f1 + 2
                poly(c, [(xa, ta + dy * f0), (xb, tb + dy * f1), (xb, tb + dy * f1 + h1), (xa, ta + dy * f0 + h0)], colr, LW * .4)
            poly(c, [(xa, ta - 24 * f0), (xb, tb - 24 * f1), (xb, tb), (xa, ta)], '#E04848', 0)
    return dict(floor=FLOOR, ambient=None, lights=[], bulbs=[(960, 420, 700, '#FFFFFF', 30)], spots=[(700, FLOOR), (1220, FLOOR)])


def set_factory(c, o):
    """High-tech factory (owner's model): bright hall, white machines, a yellow-railed conveyor running into the
    distance, gantry rails with hanging lamps, a blue ceiling."""
    vx, vy = 960, 560
    c.drawRect(skia.Rect(L0, -700, R0, vy), fp('#5A66B0'))
    for k in range(7):
        f = 1 - k / 7.0; y = vy - 40 - 560 * f ** 1.5; w = 200 + 1400 * f ** 1.5
        for sx in (-1, 1):
            poly(c, [(vx + sx * w * .15, y), (vx + sx * w * .45, y), (vx + sx * w * .42, y + 26 * f), (vx + sx * w * .17, y + 26 * f)], '#E8E27A', 0)
    for sx in (-1, 1):
        line(c, vx + sx * 60, vy - 40, vx + sx * 900, -400, 26, '#2E333F')
        for k in range(1, 6):
            f = k / 6.0; x = vx + sx * (60 + 840 * f ** 1.4); y = vy - 40 - 900 * f ** 1.4 * .52
            line(c, x, y, x, y + 40 * f + 10, 6 * f + 2, '#2E333F')
            rect(c, x - 40 * f - 8, y + 40 * f + 10, x + 40 * f + 8, y + 100 * f + 30, '#F4F5F8', LW * .5, r=8)
            c.drawRect(skia.Rect(x - 40 * f - 8, y + 40 * f + 10, x + 40 * f + 8, y + 50 * f + 16), fp('#3B6EA8'))
    c.drawRect(skia.Rect(L0, vy, R0, H + 700), fp('#EDEAE0'))
    for i in range(-12, 13): c.drawLine(vx + i * 34, vy, vx + i * 500, H + 300, ink(2, '#D6D2C4'))
    for k in range(10): yy = vy + k * k * 7; c.drawLine(L0, yy, R0, yy, ink(2, '#D6D2C4'))
    for side in (-1,):
        for k in range(6):
            f0, f1 = 1 - k / 6.0, 1 - (k + 1) / 6.0
            xa, xb = vx + side * (130 + 1000 * f0 ** 1.5), vx + side * (130 + 1000 * f1 ** 1.5)
            ta, tb = vy - 20 - 420 * f0 ** 1.5, vy - 20 - 420 * f1 ** 1.5
            ba, bb = vy + 30 + 560 * f0 ** 1.5, vy + 30 + 560 * f1 ** 1.5
            poly(c, [(xa, ta), (xb, tb), (xb, bb), (xa, ba)], '#F4F2E8', LW * .5)
            poly(c, [(xa, ta), (xb, tb), (xb, tb + 40 * f1 + 4), (xa, ta + 40 * f0 + 4)], '#E8E27A', 0)
            mx = xa + (xb - xa) * .5
            rect(c, mx - 18 * f0, ta + 70 * f0, mx + 18 * f0, ta + 200 * f0, '#3E9A56', LW * .3)
    # the conveyor: from the right foreground into the distance (characters stand left of it)
    p = skia.Path(); p.moveTo(vx + 40, vy); p.lineTo(vx + 90, vy); p.lineTo(2300, H + 400); p.lineTo(1500, H + 400); p.close()
    shape(c, p, '#2E333F', LW * .7)
    line(c, vx + 40, vy, 1500, H + 400, 22, '#F2C14E'); line(c, vx + 90, vy, 2300, H + 400, 22, '#F2C14E')
    for k in range(1, 9):
        f = (k / 9.0) ** 1.6; cx = vx + 65 + (1900 - vx - 65) * f; cy = vy + (H + 400 - vy) * f
        rect(c, cx - 24 * f - 6, cy - 8 * f - 3, cx + 24 * f + 6, cy + 4, '#E8C27A', LW * .3)
    return dict(floor=FLOOR, ambient=None, lights=[], bulbs=[(960, 560, 600, '#FFF3C8', 40)], spots=[(380, FLOOR), (760, FLOOR), (1150, FLOOR)])


def set_lab(c, o):
    """Clean lab: white tiles, bench with flasks and a microscope, shelf of bottles."""
    _room(c, '#E8F0F2', '#C9D3D8', 830, boards=False)
    for i in range(-16, 50):
        for j in range(-6, 13): c.drawRect(skia.Rect(i * 70 + 2, j * 70 + 2, i * 70 + 68, j * 70 + 68), ink(2, '#D2DDE2'))
    rect(c, 120, 180, 760, 210, WOOD, LW * .7)
    r = random.Random(2)
    for k in range(9):
        x = 150 + k * 66; h = r.uniform(60, 110); rect(c, x, 180 - h, x + 44, 180, r.choice(['#7FC8F8', '#5FCB72', '#FF9A3C', '#E8E0D0', '#FF6FA0']), LW * .5, r=8)
    rect(c, 1100, 640, 1860, 680, '#F4F4F2', LW); rect(c, 1130, 680, 1830, 900, '#9BA6B4', LW * .8)
    for (x, colr) in ((1200, '#5FCB72'), (1300, '#7FC8F8'), (1400, '#FF6FA0')):
        poly(c, [(x - 16, 540), (x + 16, 540), (x + 16, 580), (x + 46, 640), (x - 46, 640), (x - 16, 580)], '#F6FBFF', LW * .6)
        poly(c, [(x - 26, 610), (x + 26, 610), (x + 46, 640), (x - 46, 640)], colr, 0)
    rect(c, 1560, 620, 1700, 640, DARKSTEEL, LW * .6); line(c, 1630, 620, 1630, 520, 16, DARKSTEEL)
    line(c, 1630, 520, 1590, 440, 26, '#C9CFD8'); c.drawLine(1590, 440, 1630, 520, ink(LW))
    rect(c, 40, 380, 520, 830, '#D8DEE2', LW); rect(c, 70, 410, 490, 640, '#BFE3F2', LW * .6)
    return _info(o.get('time', 'day'), [('pool', 960, 400, 1000, .95)])


def set_cutaway(c, o):
    """Dollhouse cut-away of an office tower: 3x3 lit rooms with desks and screens, a sign on the roof (owner's model)."""
    _sky(c, o.get('time', 'dusk'), 1000)
    x0, x1, y0, y1 = 400, 1520, 250, 980
    rect(c, x0 - 30, y0 - 30, x1 + 30, y1, '#3A3F4C', LW)
    cols = ['#F6E7C8', '#DCEAF2', '#F2D8D8']
    for i in range(3):
        for j in range(3):
            a, b = x0 + i * (x1 - x0) / 3, y0 + j * (y1 - y0) / 3
            rect(c, a + 12, b + 12, a + (x1 - x0) / 3 - 12, b + (y1 - y0) / 3 - 12, cols[(i + j) % 3], LW * .6)
            cx, cy = a + (x1 - x0) / 6, b + (y1 - y0) / 3 - 30
            rect(c, cx - 90, cy - 50, cx + 90, cy - 36, WOOD, LW * .5); rect(c, cx - 40, cy - 110, cx + 40, cy - 56, '#1A1D2A', LW * .5)
            _person_dot(c, cx - 110, cy - 30, .9, ['#3B4660', '#C8242C', '#3E9A56'][(i * 3 + j) % 3])
    sign = o.get('sign') or (o.get('logo_art') or {}).get('title') or o.get('logo') or 'HQ'
    _sign(c, sign.upper(), 960, y0 - 100, 560, 110, '#1C1C22', '#F2C14E', 76, o.get('logo_art'))
    _ground(c, y1, '#4A5163')
    return _info(o.get('time', 'dusk'), [('pool', 960, 600, 900, .95)], [(960, 600, 700, '#FFD98A', 40)])


def set_openoffice(c, o):
    """Modern open-plan tech office: glass wall onto the city, rows of desks with monitors."""
    _sky(c, o.get('time', 'day'), 700)
    blur_begin(c, 2.0); far_city(c, 640, o.get('time', 'day'), 6); c.restore()
    for i in range(-4, 12): line(c, i * 220, -200, i * 220, 700, 8, '#C9CFD8')
    rect(c, L0, 640, R0, 700, '#C9CFD8', LW * .7)
    _ground(c, 700, '#B7BDC6')
    for row, (y, s) in enumerate(((800, .8), (930, 1.0))):
        for k in range(-1, 6):
            x = 160 + k * 360 + row * 180
            rect(c, x - 140 * s, y - 20 * s, x + 140 * s, y, '#F4F4F2', LW * .6)
            rect(c, x - 60 * s, y - 120 * s, x + 60 * s, y - 40 * s, '#1A1D2A', LW * .5)
            c.drawRect(skia.Rect(x - 50 * s, y - 110 * s, x + 50 * s, y - 50 * s), fp('#3B6EA8'))
    return _info(o.get('time', 'day'), [('pool', 960, 500, 1000, .95)])


# ---------------------------------------------------------------- money
def set_vault(c, o):
    """Bank vault: round steel door open at the back, shelves of gold and cash."""
    _room(c, '#5A6070', '#3E4350', 830, boards=False)
    for i in range(-14, 48):
        for j in range(-6, 12): c.drawRect(skia.Rect(i * 90 + (j % 2) * 45, j * 60, i * 90 + 86 + (j % 2) * 45, j * 60 + 56), ink(2, '#4E5462'))
    circ(c, 960, 430, 330, '#2A2E38', LW); circ(c, 960, 430, 290, '#151820', LW * .6)
    circ(c, 1360, 470, 300, '#B9BDC6', LW)
    for k in range(8):
        a = k * math.pi / 4; c.drawLine(1360, 470, 1360 + 230 * math.cos(a), 470 + 230 * math.sin(a), ink(10, '#8C95A6'))
    circ(c, 1360, 470, 70, '#D9DDE4', LW * .8)
    for side, x in ((-1, 300), (1, 1620)):
        for k in range(3):
            y = 380 + k * 150; rect(c, x - 200, y, x + 200, y + 16, '#7A6A4A', LW * .5)
            for q in range(4):
                bx = x - 170 + q * 90
                if (k + q) % 2: poly(c, [(bx, y), (bx + 14, y - 40), (bx + 64, y - 40), (bx + 78, y)], GOLD, LW * .5)
                else: rect(c, bx, y - 46, bx + 78, y, '#7DBE7A', LW * .5); rect(c, bx + 30, y - 46, bx + 48, y, '#F6EED4', 0)
    return _info(o.get('time', 'night'), [('pool', 960, 430, 700, .9)], [(960, 430, 400, '#FFD98A', 40)])


def set_trading(c, o):
    """Trading floor: a wall of red and green charts, a ticker strip, desks with screens."""
    _room(c, '#1E2332', '#2A3044', 820, boards=False)
    for i in range(6):
        for j in range(2):
            x = 60 + i * 310; y = 90 + j * 250
            _screen(c, x, y, x + 280, y + 220, 'up' if (i + j) % 2 else 'down', i * 3 + j)
    rect(c, L0, 600, R0, 660, '#111420', LW * .7)
    tick = o.get('ticker', 'NVDA +4.2   TSLA -3.1   BTC +2.7   AAPL +0.8   GOLD +1.1   ')
    x = -200
    while x < W + 200:
        label(c, tick, x, 645, 40, '#F2C14E', skew=0); x += text_w(tick, 40)
    for k in range(-1, 7):
        x = 80 + k * 300; rect(c, x - 120, 900, x + 120, 930, '#3A3F4C', LW * .6)
        rect(c, x - 70, 820, x + 70, 890, '#111420', LW * .5); c.drawRect(skia.Rect(x - 60, 830, x + 60, 880), fp('#2F6B45' if k % 2 else '#7A2228'))
    return dict(floor=FLOOR, ambient='#5A6AB0', lights=[('pool', 960, 300, 1100, .95)], bulbs=[(960, 300, 900, '#7FC8F8', 30)],
                spots=[(520, FLOOR), (960, FLOOR), (1400, FLOOR)])


def set_mining(c, o):
    """Crypto mining room: racks of rigs with fans, cables, warm glow."""
    _room(c, '#2A2730', '#3A3540', 820, boards=False)
    for i in range(-2, 9):
        for j in range(4):
            x = i * 230; y = 120 + j * 170
            rect(c, x + 10, y, x + 220, y + 150, '#3E3A46', LW * .6)
            for q in range(3):
                cx = x + 50 + q * 66; circ(c, cx, y + 75, 28, '#1A1820', LW * .4)
                for b in range(4): a = b * math.pi / 2 + .4; c.drawLine(cx, y + 75, cx + 24 * math.cos(a), y + 75 + 24 * math.sin(a), ink(3, '#5A5664'))
                c.drawCircle(cx + 22, y + 22, 5, fp('#FF9A3C'))
    for k in range(6): line(c, 200 + k * 300, 800, 260 + k * 300, 1060, 6, '#C8242C' if k % 2 else '#2F6B9A')
    return dict(floor=FLOOR, ambient='#7A5A6A', lights=[('pool', 960, 500, 1000, .9)], bulbs=[(960, 500, 800, '#FF9A3C', 40)],
                spots=[(520, FLOOR), (960, FLOOR), (1400, FLOOR)])


def set_exchange(c, o):
    """A stock exchange front: columns, a pediment, a banner, flags (generic, never a real building's likeness)."""
    _sky(c, o.get('time', 'day'), 900)
    rect(c, 260, 260, 1660, 330, '#E6E0D2', LW); poly(c, [(220, 260), (1700, 260), (960, 80)], '#EFEADF', LW)
    for k in range(7):
        x = 360 + k * 200; rect(c, x - 40, 330, x + 40, 840, '#F4F0E6', LW * .8)
        for q in (-20, 0, 20): line(c, x + q, 350, x + q, 820, 3, '#D8D2C2')
    sign = o.get('sign', 'STOCK EXCHANGE'); label(c, sign.upper(), 960, 312, fit_size(sign.upper(), 54, 1300), '#3A3F4C', align='center', skew=0)
    rect(c, 300, 560, 1620, 700, '#3B6EA8', LW * .7)
    for k in range(5): line(c, 420 + k * 270, 560, 420 + k * 270, 700, 4, '#F4F0E6')
    rect(c, 200, 840, 1720, 900, '#D8D2C2', LW); _ground(c, 900, '#B9B4A8')
    return _info(o.get('time', 'day'), [('pool', 960, 500, 1000, .9)])


# ---------------------------------------------------------------- institutions
def set_court(c, o):
    """Courtroom: wood panels, the judge's raised bench with a seal, flags, the witness box."""
    _room(c, '#7A4E2E', '#5A3A22', 820, stripe='#6E4428')
    rect(c, 560, 420, 1360, 820, '#6A4428', LW); rect(c, 520, 380, 1400, 430, '#8E5C36', LW)
    circ(c, 960, 230, 110, '#D0A548', LW); circ(c, 960, 230, 80, '#C8A040', LW * .5); label(c, 'COURT', 960, 245, 40, '#5A3A22', align='center', skew=0)
    for x in (130, 1790):                    # owner 2026-11-21: poles never stand where a character's head goes
        line(c, x, 820, x, 200, 8, '#3A3F4C'); poly(c, [(x, 210), (x + 120 * (1 if x < 960 else -1), 230), (x, 330)], '#3B6EA8' if x < 960 else '#C8242C', LW * .6)
    rect(c, 1500, 640, 1820, 820, '#8E5C36', LW); rect(c, 100, 640, 420, 820, '#8E5C36', LW)
    return _info(o.get('time', 'day'), [('pool', 960, 400, 900, .95)], [(960, 230, 300, '#FFD98A', 30)])


def set_parliament(c, o):
    """Parliament chamber: tiers of green benches facing a speaker's chair and lectern."""
    _room(c, '#6E5A44', '#3E6A4A', 640, stripe='#625038', boards=False)
    rect(c, 830, 230, 1090, 560, '#5A3A22', LW); rect(c, 870, 280, 1050, 520, '#2F6B45', LW * .6)
    circ(c, 960, 200, 60, GOLD, LW * .7)
    for k in range(5):
        y = 640 + k * 90; s = 1 + k * .25
        for side in (-1, 1):
            x0, x1 = 960 + side * (180 * s), 960 + side * (900 * s)
            rect(c, min(x0, x1), y, max(x0, x1), y + 50, '#2F6B45', LW * .6)
            for q in range(1, 8):
                hx_ = x0 + (x1 - x0) * q / 8; circ(c, hx_, y - 14, 16 * s * .8, '#E6BE8E', LW * .3)
    rect(c, 880, 600, 1040, 700, WOOD, LW)
    return _info(o.get('time', 'day'), [('pool', 960, 400, 1000, .95)])


def set_hospital(c, o):
    """Hospital ward: pale green wall, a bed with rails, a heart monitor, IV stand, curtain."""
    _room(c, '#D6E8DE', '#C2CCC6', 830, boards=False)
    for i in range(-12, 40): c.drawLine(L0, 600 + i * 0, R0, 600, ink(0))
    rect(c, L0, 560, R0, 600, '#B8D0C2', LW * .5)
    rect(c, 1150, 720, 1800, 800, '#F4F4F2', LW); rect(c, 1150, 680, 1340, 730, '#FFFFFF', LW * .6)
    rect(c, 1130, 640, 1160, 900, STEEL, LW * .6); rect(c, 1790, 680, 1820, 900, STEEL, LW * .6); rect(c, 1160, 800, 1790, 840, DARKSTEEL, LW * .6)
    rect(c, 1500, 360, 1760, 540, '#1A1D2A', LW); hp = skia.Path(); hp.moveTo(1520, 460)
    for (x, y) in ((1580, 460), (1600, 400), (1625, 510), (1645, 440), (1660, 460), (1740, 460)): hp.lineTo(x, y)
    c.drawPath(hp, ink(5, '#5FE08A'))
    line(c, 1880, 880, 1880, 300, 8, STEEL); rect(c, 1850, 300, 1910, 400, '#DCEAF2', LW * .6)
    for k in range(9): c.drawLine(60 + k * 50, 120, 40 + k * 50, 860, ink(18, '#9CC8D6' if k % 2 else '#8ABBCB'))
    rect(c, 20, 100, 520, 124, STEEL, LW * .5)
    return _info(o.get('time', 'day'), [('pool', 960, 380, 1000, .95)])


def set_classroom(c, o):
    """Classroom: chalkboard, a clock, rows of desks."""
    _room(c, '#E8D8B0', '#9A7A54', 820)
    rect(c, 420, 130, 1500, 560, WOOD, LW); rect(c, 450, 160, 1470, 530, '#2F5A46', LW * .6)
    txt = o.get('board_text', ''); label(c, txt, 960, 380, fit_size(txt, 90, 900), '#F4F0E6', align='center', skew=0) if txt else None
    wall_clock(c, 1700, 220)
    for row, (y, s) in enumerate(((880, .8), (990, 1.0))):
        for k in range(-1, 6):
            x = 200 + k * 340 + row * 170; rect(c, x - 110 * s, y - 20 * s, x + 110 * s, y, '#C9965A', LW * .6)
            line(c, x - 90 * s, y, x - 90 * s, y + 70 * s, 6, DARKSTEEL); line(c, x + 90 * s, y, x + 90 * s, y + 70 * s, 6, DARKSTEEL)
    return _info(o.get('time', 'day'), [('pool', 960, 350, 1000, .95)])


def set_newsroom(c, o):
    """TV news studio: a curved desk, a big screen with the show's name, studio lights."""
    c.drawRect(skia.Rect(L0, -700, R0, H + 700), sp(radial(960, 400, 1400, [hx('#1E3A6A'), hx('#0E1A38')])))
    rect(c, 360, 90, 1560, 620, '#0A1228', LW); c.drawRect(skia.Rect(380, 110, 1540, 600), sp(linear(0, 110, 0, 600, [hx('#3B6EA8'), hx('#1E3A6A')])))
    show = o.get('sign', 'BREAKING NEWS'); rect(c, 380, 470, 1540, 580, '#C8242C', 0)
    label(c, show.upper(), 960, 548, fit_size(show.upper(), 70, 1080), '#FFFFFF', align='center', skew=0)
    for k in range(-8, 30): c.drawLine(k * 120, -400, k * 120 + 60, 60, ink(2, '#2A4A80'))
    p = skia.Path(); p.moveTo(380, 780); p.quadTo(960, 700, 1540, 780); p.lineTo(1500, 900); p.quadTo(960, 830, 420, 900); p.close(); shape(c, p, '#E8ECF2', LW)
    _ground(c, 900, '#111A30')
    return dict(floor=FLOOR, ambient='#6A78C0', lights=[('pool', 960, 450, 1000, .95)], bulbs=[(960, 340, 700, '#7FC8F8', 40)],
                spots=[(700, FLOOR), (1220, FLOOR)])


def set_stage(c, o):
    """A stage: red curtains, a spotlight on a podium, the audience's heads in front."""
    c.drawRect(skia.Rect(L0, -700, R0, H + 700), fp('#14121A'))
    for side in (-1, 1):
        for k in range(10):
            x = 960 + side * (720 + k * 60); c.drawRect(skia.Rect(min(x, x + side * 60), -300, max(x, x + side * 60), 900), fp('#9A1F2A' if k % 2 else '#B8242F'))
    for k in range(40): c.drawRect(skia.Rect(-200 + k * 60, -100, -140 + k * 60, 110), fp('#9A1F2A' if k % 2 else '#B8242F'))
    _ground(c, 900, '#6A4428'); cone = cone_path(960, -100, 200, 900, 1000)
    c.drawPath(cone, fp('#FFF3C8', 60))
    rect(c, 880, 740, 1040, 900, WOOD, LW); rect(c, 860, 720, 1060, 750, '#A87A50', LW * .7)
    sign = o.get('sign'); _sign(c, sign.upper(), 960, 820, 140, 60, '#1C1C22', GOLD, 40) if sign else None
    return dict(floor=FLOOR, ambient='#3A3450', lights=[('path', cone, .95, 30), ('oval', 960, 900, 500, 120, .9)],
                bulbs=[(960, 0, 300, '#FFF3C8', 80)], spots=[(700, FLOOR), (1220, FLOOR)])


def set_press(c, o):
    """Press conference: a backdrop printed with the name, a podium with microphones, flags."""
    art = o.get('logo_art')
    name = (o.get('sign') or (art or {}).get('title') or o.get('logo') or 'PRESS').upper()
    c.drawRect(skia.Rect(L0, -700, R0, 900), fp('#1E3A6A'))
    for j in range(-4, 10):
        for i in range(-6, 20):
            x, y = i * 330 + (j % 2) * 165, j * 120
            if art and (i + j) % 2 == 0:
                brand(c, art, x, y - 14, 70)
            else:
                label(c, name, x, y, fit_size(name, 44, 280), '#3B5E96', align='center', skew=0)
    _ground(c, 900, '#2A3044')
    for x in (150, 1770):
        line(c, x, 900, x, 280, 8, '#C9CFD8'); poly(c, [(x, 290), (x + (130 if x < 960 else -130), 320), (x, 450)], '#C8242C' if x < 960 else '#F4F0E6', LW * .6)
    poly(c, [(860, 640), (1060, 640), (1040, 900), (880, 900)], '#3A3F4C', LW)
    for dx in (-40, 0, 40): line(c, 960 + dx, 640, 960 + dx * 1.5, 560, 5, INK); circ(c, 960 + dx * 1.5, 556, 12, '#1C1C22', LW * .4)
    if not brand(c, art, 960, 735, 80): _sign(c, name, 960, 740, 170, 60, '#1C1C22', '#FFFFFF', 34)
    return _info(o.get('time', 'day'), [('pool', 960, 450, 1000, .95)])


def set_prison(c, o):
    """A cell: block wall, a cot, a high barred window."""
    _room(c, '#8A8E96', '#5E626A', 840, boards=False)
    for i in range(-14, 48):
        for j in range(-6, 14): c.drawRect(skia.Rect(i * 100 + (j % 2) * 50, j * 60, i * 100 + 96 + (j % 2) * 50, j * 60 + 56), ink(2, '#7A7E86'))
    rect(c, 820, 120, 1100, 320, '#BFE3F2', LW)
    for k in range(1, 6): line(c, 820 + k * 47, 120, 820 + k * 47, 320, 10, DARKSTEEL)
    rect(c, 1250, 760, 1800, 820, '#B9B4A8', LW); rect(c, 1250, 820, 1800, 850, DARKSTEEL, LW * .6)
    for k in range(-12, 40): line(c, k * 120, -700, k * 120, -640, 1, DARKSTEEL)
    return _info(o.get('time', 'day'), [('pool', 960, 220, 700, .9)])


def set_stadium(c, o):
    """A stadium: tiers of crowd dots, floodlights, the green pitch."""
    _sky(c, o.get('time', 'night'), 400)
    r = random.Random(5)
    for k in range(6):
        y = 300 + k * 70; c.drawRect(skia.Rect(L0, y, R0, y + 70), fp(shade('#3A3F4C', 1 + k * .05)))
        for i in range(160): c.drawCircle(-800 + i * 22 + r.uniform(-4, 4), y + 30 + r.uniform(-8, 8), 8, fp(r.choice(['#E6BE8E', '#C99F70', '#8A5A3A', '#F1CFA8', '#C8242C', '#3B6EA8', '#F2C14E'])))
    for x in (200, 1720):
        line(c, x, 300, x, -100, 12, DARKSTEEL); rect(c, x - 90, -160, x + 90, -80, '#FFF3C8', LW * .6)
    _ground(c, 720, '#3E9A56')
    for k in range(10): c.drawRect(skia.Rect(L0, 720 + k * 40 + k * k * 2, R0, 740 + k * 40 + k * k * 2), fp('#46A85E'))
    line(c, 960, 720, 960, H + 300, 6, '#F4F0E6')
    return _info(o.get('time', 'night'), [('pool', 960, 700, 1100, .95)], [(200, -120, 300, '#FFF3C8', 80), (1720, -120, 300, '#FFF3C8', 80)])


def set_market(c, o):
    """An open-air market: stalls with striped awnings, crates of fruit, people."""
    _sky(c, o.get('time', 'day'), 820)
    blur_begin(c, 2.0); far_city(c, 600, o.get('time', 'day'), 11); c.restore()
    for k, x in enumerate((-60, 460, 980, 1500)):
        colr = ['#C8242C', '#2F6B9A', '#3E9A56', '#F2A13C'][k]
        rect(c, x, 520, x + 440, 800, '#C9965A', LW * .7)
        aw = poly(c, [(x - 20, 440), (x + 460, 440), (x + 480, 520), (x - 40, 520)], colr, LW)
        c.save(); c.clipPath(aw, doAntiAlias=True)
        for i in range(0, 12, 2): c.drawRect(skia.Rect(x - 40 + i * 44, 430, x + 4 + i * 44, 530), fp('#F4EFE2'))
        c.restore(); c.drawPath(aw, ink(LW))
        for q in range(6): circ(c, x + 50 + q * 66, 690, 26, ['#FF9A3C', '#5FCB72', '#C8242C', '#F2C14E'][q % 4], LW * .4)
    _ground(c, 820, '#B9A27A')
    return _info(o.get('time', 'day'), [('pool', 960, 600, 1000, .95)])


# ---------------------------------------------------------------- space
def _earth(c, x, y, r, seed=3):
    circ(c, x, y, r, '#3B7CC8', LW)
    c.save(); p = skia.Path(); p.addCircle(x, y, r); c.clipPath(p, doAntiAlias=True)
    rr = random.Random(seed)
    for _ in range(7):
        cx, cy = x + rr.uniform(-r, r), y + rr.uniform(-r, r); c.drawOval(skia.Rect(cx - r * .35, cy - r * .22, cx + r * .35, cy + r * .22), fp('#5FAE5A'))
    c.drawCircle(x + r * .35, y + r * .35, r * 1.0, fp((0, 0, 30), 60)); c.restore()
    c.drawCircle(x, y, r + 18, ink(10, '#7FC8F8', 90))


def set_space(c, o):
    """Space: stars, the Earth big, the Moon far off."""
    c.drawRect(skia.Rect(L0, -700, R0, H + 700), sp(radial(960, 500, 1500, [hx('#1A1E40'), hx('#05060F')])))
    r = random.Random(9)
    for _ in range(260): c.drawCircle(r.uniform(L0, R0), r.uniform(-600, H + 600), r.uniform(1.2, 3.4), fp('#FFFFFF', r.uniform(120, 255)))
    _earth(c, 520, 900, 520); circ(c, 1600, 220, 70, '#D9D6CC', LW * .7)
    return dict(floor=FLOOR, ambient=None, lights=[], bulbs=[(520, 900, 700, '#7FC8F8', 40)], spots=[(1200, FLOOR), (1500, FLOOR)])


def set_moon(c, o):
    """Moon surface: grey ground with craters, the Earth in a black sky."""
    c.drawRect(skia.Rect(L0, -700, R0, H + 700), fp('#05060F'))
    r = random.Random(4)
    for _ in range(200): c.drawCircle(r.uniform(L0, R0), r.uniform(-600, 700), r.uniform(1.2, 3), fp('#FFFFFF', r.uniform(120, 255)))
    _earth(c, 1450, 230, 140)
    p = skia.Path(); p.moveTo(L0, 760)
    for k in range(-9, 31): p.quadTo(k * 100 + 50, 740 + (k % 3) * 14, k * 100 + 100, 760)
    p.lineTo(R0, H + 700); p.lineTo(L0, H + 700); p.close(); shape(c, p, '#B9B6AE', LW)
    for (x, y, w) in ((300, 880, 220), (900, 820, 140), (1500, 930, 260), (1200, 1040, 180), (-100, 1000, 200)):
        oval(c, x - w, y - w * .22, x + w, y + w * .22, '#9C988E', LW * .6); oval(c, x - w * .8, y - w * .12, x + w * .8, y + w * .2, '#8A867C', 0)
    flag = o.get('flag')
    if flag: line(c, 1650, 900, 1650, 640, 6, '#D9DDE4'); _sign(c, flag.upper(), 1730, 690, 160, 90, '#FFFFFF', INK, 40)
    return dict(floor=FLOOR, ambient=None, lights=[], bulbs=[], spots=[(600, FLOOR), (1100, FLOOR)])


def set_mars(c, o):
    """Mars: red dunes, a salmon sky, a dome base and a rover."""
    c.drawRect(skia.Rect(L0, -700, R0, 800), sp(linear(0, -200, 0, 800, [hx('#E8A47A'), hx('#F4C9A0')])))
    circ(c, 1550, 180, 40, '#FFF0D8', LW * .5)
    for (y, colr) in ((700, '#C8643A'), (780, '#B0502C')):
        p = skia.Path(); p.moveTo(L0, y)
        for k in range(-9, 31): p.quadTo(k * 120 + 60, y - 50 * ((k % 2) + .3), k * 120 + 120, y)
        p.lineTo(R0, H + 700); p.lineTo(L0, H + 700); p.close(); shape(c, p, colr, LW)
    for (x, rr) in ((1300, 170), (1530, 110)):
        p = skia.Path(); p.addArc(skia.Rect(x - rr, 800 - rr, x + rr, 800 + rr), 180, 180); p.close(); shape(c, p, '#DCEAF2', LW)
        for k in range(1, 4): c.drawLine(x - rr + k * rr / 2, 800 - math.sqrt(max(0, rr * rr - (k * rr / 2 - rr) ** 2)), x - rr + k * rr / 2, 800, ink(3, '#9CB8C8'))
    rect(c, 300, 840, 520, 900, '#D9DDE4', LW * .7); circ(c, 330, 910, 26, DARKSTEEL, LW * .5); circ(c, 490, 910, 26, DARKSTEEL, LW * .5)
    line(c, 470, 840, 470, 780, 5, INK); rect(c, 440, 760, 500, 790, '#3A3F4C', LW * .5)
    flag = o.get('flag')
    if flag: line(c, 1100, 860, 1100, 600, 6, '#D9DDE4'); _sign(c, flag.upper(), 1180, 650, 160, 90, '#FFFFFF', INK, 40)
    return dict(floor=FLOOR, ambient=None, lights=[], bulbs=[], spots=[(700, FLOOR), (1000, FLOOR)])


def set_launchpad(c, o):
    """Launch pad: the service tower, a rocket on the pad, fences, a wide sky."""
    time = o.get('time', 'dusk'); _sky(c, time, 860)
    for k in range(10): rect(c, 1240, 860 - k * 70, 1330, 790 - k * 70, '#C8242C' if k % 2 else '#8A2A2A', LW * .5)
    for k in range(10): line(c, 1240, 860 - k * 70, 1330, 790 - k * 70, 3, INK)
    rect(c, 1330, 300, 1400, 316, DARKSTEEL, LW * .5)
    rect(c, 1420, 180, 1540, 860, '#F4F4F2', LW); poly(c, [(1420, 180), (1540, 180), (1480, 40)], '#F4F4F2', LW)
    poly(c, [(1420, 760), (1360, 860), (1420, 860)], '#3A3F4C', LW * .6); poly(c, [(1540, 760), (1600, 860), (1540, 860)], '#3A3F4C', LW * .6)
    txt = o.get('sign', ''); label(c, txt, 1480, 500, fit_size(txt, 40, 300), INK, align='center', rot=-90, skew=0) if txt else None
    rect(c, 1150, 860, 1800, 900, '#8C95A6', LW)
    _ground(c, 900, '#9A9282')
    for k in range(-8, 30): line(c, k * 60, 900, k * 60, 860, 3, '#5A5E6A')
    line(c, L0, 870, 1100, 870, 3, '#5A5E6A')
    return _info(time, [('pool', 1480, 500, 700, .9)], spots=[(500, FLOOR), (900, FLOOR)])


# ---------------------------------------------------------------- travel
def set_airport(c, o):
    """Airport gate: a glass wall onto the runway and a plane, rows of seats, a departure board."""
    time = o.get('time', 'day'); _sky(c, time, 720)
    _ground(c, 620, '#8C8A90', False)
    line(c, L0, 680, R0, 680, 6, '#F4F0E6')
    rect(c, 700, 520, 1500, 600, '#F4F4F2', LW); poly(c, [(1500, 520), (1580, 560), (1500, 600)], '#F4F4F2', LW)
    poly(c, [(980, 560), (1120, 560), (1000, 680)], '#D9DDE4', LW * .7); poly(c, [(720, 520), (780, 520), (720, 440)], '#3B6EA8', LW * .7)
    for k in range(10): c.drawCircle(820 + k * 64, 550, 10, fp('#3B6EA8'))
    for i in range(-4, 12): line(c, i * 220, -200, i * 220, 720, 10, '#B9BDC6')
    rect(c, L0, 700, R0, 740, '#B9BDC6', LW * .7); _ground(c, 740, '#D8D2C2')
    rect(c, 120, 140, 620, 420, '#1A1D2A', LW)
    for k in range(5): label(c, ['LUSAKA  ON TIME', 'DUBAI   BOARDING', 'LONDON  DELAYED', 'BEIJING 21:40', 'NEW YORK 23:05'][k], 150, 200 + k * 50, 34, '#F2C14E', skew=0)
    for k in range(-1, 7):
        x = 100 + k * 300; rect(c, x - 120, 900, x + 120, 930, '#3B6EA8', LW * .6); rect(c, x - 120, 850, x + 120, 900, '#4F80BC', LW * .6)
    return _info(time, [('pool', 960, 450, 1100, .95)])


def set_port(c, o):
    """Shipping port: the sea, a container ship, cranes, stacked containers on the quay."""
    time = o.get('time', 'day'); _sky(c, time, 640)
    c.drawRect(skia.Rect(L0, 640, R0, 860), fp('#3B6EA8')); line(c, L0, 640, R0, 640, LW)
    for i in range(30): c.drawLine((i * 173) % 2600 - 400, 680 + (i % 6) * 28, (i * 173) % 2600 - 340, 680 + (i % 6) * 28, ink(3, '#7FB8DA'))
    poly(c, [(250, 620), (1250, 620), (1180, 720), (320, 720)], '#C8242C', LW); rect(c, 1080, 470, 1200, 620, '#F4F4F2', LW * .7)
    colrs = ['#3B6EA8', '#F2A13C', '#3E9A56', '#C8242C', '#8A5AB0']
    for j in range(3):
        for i in range(9): rect(c, 300 + i * 85, 560 - j * 52, 380 + i * 85, 610 - j * 52, colrs[(i + j * 2) % 5], LW * .5)
    for x in (1400, 1720):
        line(c, x, 860, x, 200, 16, '#F2A13C'); line(c, x - 260, 220, x + 120, 220, 16, '#F2A13C'); line(c, x - 220, 220, x - 220, 420, 3, INK)
        rect(c, x - 250, 420, x - 190, 450, '#3A3F4C', LW * .4)
    _ground(c, 860, '#8C8A90')
    for i in range(6): rect(c, 1300 + i * 100, 780, 1390 + i * 100, 860, colrs[i % 5], LW * .5)
    return _info(time, [('pool', 960, 500, 1100, .95)])


def set_highway(c, o):
    """A highway running to the horizon: lanes, a guard rail, hills, a road sign."""
    time = o.get('time', 'day'); _sky(c, time, 560)
    p = skia.Path(); p.moveTo(L0, 560)
    for k in range(-6, 20): p.quadTo(k * 200 + 100, 470 + (k % 3) * 30, k * 200 + 200, 560)
    p.lineTo(R0, 700); p.lineTo(L0, 700); p.close(); shape(c, p, '#6AAE6A', LW)
    _ground(c, 560, '#7FB46A')
    poly(c, [(900, 560), (1020, 560), (2100, H + 200), (-180, H + 200)], '#4A4E5A', LW)
    for k in range(9):
        a, b = 560 + 18 * k * k * .8, 560 + 18 * (k + .5) ** 2 * .8; c.drawLine(960, a, 960, min(b, H + 200), ink(6 + k * 2, '#F2C14E'))
    line(c, 900, 560, -180, H + 200, 8, '#F4F0E6'); line(c, 1020, 560, 2100, H + 200, 8, '#F4F0E6')
    sign = o.get('sign', 'NEXT EXIT')
    line(c, 1780, 820, 1780, 420, 10, DARKSTEEL); _sign(c, sign.upper(), 1700, 380, 380, 120, '#2F6B45', '#FFFFFF', 54)
    return _info(time, [('pool', 960, 500, 1200, .95)], spots=[(700, FLOOR), (1250, FLOOR)])


def set_station(c, o):
    """Train station platform: a train at the platform, pillars, a hanging clock."""
    _room(c, '#C9B89A', '#9A9282', 820, boards=False)
    for i in range(-4, 12):
        if not _in_band(i * 260): rect(c, i * 260 - 20, -100, i * 260 + 20, 820, '#6A6E7A', LW * .6)
    rect(c, L0, 380, R0, 720, '#D9DDE4', LW); rect(c, L0, 420, R0, 470, '#C8242C', 0)
    for i in range(-6, 22): rect(c, i * 150 + 20, 500, i * 150 + 120, 600, '#7FB8DA', LW * .6)
    rect(c, L0, 720, R0, 760, '#3A3F4C', LW * .7); rect(c, L0, 820, R0, 850, '#F2C14E', 0)
    circ(c, 960, 140, 60, '#F4F4F2', LW); line(c, 960, 140, 960, 100, 5); line(c, 960, 140, 990, 150, 5); line(c, 960, 80, 960, -100, 5)
    return _info(o.get('time', 'day'), [('pool', 960, 400, 1100, .95)])


# ---------------------------------------------------------------- nature and home
def set_farm(c, o):
    """Farm: furrowed fields, a red barn, a silo, a fence."""
    time = o.get('time', 'day'); _sky(c, time, 620)
    _ground(c, 620, '#8AB65A')
    for k in range(14): c.drawLine(960 + (k - 7) * 60, 620, 960 + (k - 7) * 400, H + 300, ink(10, '#76A04A'))
    rect(c, 1250, 360, 1650, 640, '#B8242F', LW); poly(c, [(1220, 370), (1680, 370), (1450, 220)], '#8A1F2A', LW)
    rect(c, 1390, 480, 1510, 640, '#F4F0E6', LW * .7); line(c, 1390, 480, 1510, 640, 5, '#B8242F'); line(c, 1510, 480, 1390, 640, 5, '#B8242F')
    rect(c, 1700, 260, 1820, 640, '#B9BDC6', LW); p = skia.Path(); p.addArc(skia.Rect(1700, 200, 1820, 320), 180, 180); p.close(); shape(c, p, '#8C95A6', LW)
    for k in range(-10, 30): line(c, k * 90, 760, k * 90, 860, 8, '#C9965A')
    line(c, L0, 790, R0, 790, 8, '#C9965A'); line(c, L0, 830, R0, 830, 8, '#C9965A')
    return _info(time, spots=[(500, FLOOR), (900, FLOOR), (1300, FLOOR)])


def set_forest(c, o):
    """Forest: layered pines and round trees, a path into the woods."""
    time = o.get('time', 'day'); _sky(c, time, 700)
    for (y, s, colr, sd) in ((640, .7, '#5A8A6A', 1), (720, .9, '#3E7A50', 2)):
        rr = random.Random(sd)
        for k in range(-6, 26): _tree(c, k * 120 + rr.uniform(-30, 30), y, s, colr, 'pine')
    _ground(c, 760, '#6AAE5A')
    poly(c, [(900, 760), (1020, 760), (1300, H + 200), (620, H + 200)], '#C9A87A', LW * .7)
    for x in (120, 360, 1600, 1820): _tree(c, x, 1000, 1.4, '#3E9A56')
    return _info(time, spots=[(500, FLOOR), (960, FLOOR), (1400, FLOOR)])


def set_ocean(c, o):
    """Ocean: the horizon, rolling waves, a sailing boat, a sand strip in front."""
    time = o.get('time', 'day'); _sky(c, time, 560)
    c.drawRect(skia.Rect(L0, 560, R0, 900), sp(linear(0, 560, 0, 900, [hx('#4F8FB8'), hx('#2F6B9A')]))); line(c, L0, 560, R0, 560, LW)
    for row in range(6):
        y = 600 + row * 50
        p = skia.Path(); p.moveTo(L0, y)
        for k in range(-9, 40): p.quadTo(k * 80 + 40, y - 14, k * 80 + 80, y)
        c.drawPath(p, ink(4, '#BFE3F2', 160))
    poly(c, [(1240, 640), (1500, 640), (1460, 690), (1280, 690)], '#8E5C36', LW * .7); line(c, 1370, 640, 1370, 420, 5)
    poly(c, [(1376, 430), (1376, 630), (1490, 630)], '#F4F4F2', LW * .6)
    _ground(c, 900, '#E8D6A8')
    return _info(time, spots=[(500, FLOOR), (960, FLOOR), (1400, FLOOR)])


def set_desert(c, o):
    """Desert: dunes, a hot sun, cactus."""
    time = o.get('time', 'day'); sky(c, time, 760); sun(c, 1500, 200, 90) if time == 'day' else None
    for (y, colr) in ((640, '#E8C27A'), (740, '#DDB062'), (860, '#D2A050')):
        p = skia.Path(); p.moveTo(L0, y)
        for k in range(-5, 16): p.quadTo(k * 260 + 130, y - 90 * ((k % 2) + .2), k * 260 + 260, y)
        p.lineTo(R0, H + 700); p.lineTo(L0, H + 700); p.close(); shape(c, p, colr, LW)
    for (x, y, s) in ((300, 900, 1.0), (1650, 860, .8)):
        rect(c, x - 26 * s, y - 230 * s, x + 26 * s, y, '#4F9A5A', LW * .7, r=26 * s)
        rect(c, x - 90 * s, y - 170 * s, x - 50 * s, y - 80 * s, '#4F9A5A', LW * .6, r=20 * s); rect(c, x + 50 * s, y - 200 * s, x + 90 * s, y - 110 * s, '#4F9A5A', LW * .6, r=20 * s)
    return _info(time, spots=[(600, FLOOR), (1000, FLOOR), (1300, FLOOR)])


def set_mountains(c, o):
    """Mountains: snowy peaks in layers, pines below."""
    time = o.get('time', 'day'); _sky(c, time, 900)
    for (base, colr, sd, hgt) in ((760, '#8A96B4', 1, 520), (820, '#6A7898', 2, 420)):
        rr = random.Random(sd); x = L0
        while x < R0:
            w = rr.uniform(400, 700); top = base - hgt * rr.uniform(.6, 1)
            poly(c, [(x, base), (x + w / 2, top), (x + w, base)], colr, LW)
            poly(c, [(x + w / 2 - w * .1, top + (base - top) * .2), (x + w / 2, top), (x + w / 2 + w * .1, top + (base - top) * .2)], '#F4F4F2', LW * .6)
            x += w * .7
    _ground(c, 820, '#6AAE5A')
    for k in range(-6, 26): _tree(c, k * 110, 860, .6, '#3E7A50', 'pine')
    return _info(time, spots=[(500, FLOOR), (960, FLOOR), (1400, FLOOR)])


def set_kitchen(c, o):
    """Kitchen: tiled splash-back, wall cabinets, a counter, a fridge and a stove."""
    _room(c, '#F2E6CC', '#C9A87A', 860)
    for i in range(-14, 48):
        for j in range(8, 11): c.drawRect(skia.Rect(i * 60, j * 60, i * 60 + 58, j * 60 + 58), ink(2, '#E2D2B0'))
    for k in range(5): rect(c, 300 + k * 230, 140, 510 + k * 230, 400, '#7FAE9A', LW * .7); circ(c, 490 + k * 230, 380, 8, GOLD, LW * .3)
    rect(c, 200, 660, 1500, 700, '#E8E4DA', LW); rect(c, 220, 700, 1480, 860, '#7FAE9A', LW * .8)
    rect(c, 700, 600, 900, 660, '#3A3F4C', LW * .6); circ(c, 750, 600, 20, '#1C1C22', LW * .4); circ(c, 850, 600, 20, '#1C1C22', LW * .4)
    rect(c, 1580, 260, 1860, 860, '#E8ECF2', LW); line(c, 1580, 520, 1860, 520, LW * .7); line(c, 1600, 380, 1600, 470, 8, DARKSTEEL)
    return _info(o.get('time', 'day'), [('pool', 960, 400, 1000, .95)])


def set_bedroom(c, o):
    """Bedroom: a bed with a blanket, a nightstand lamp, a window."""
    time = o.get('time', 'night'); _room(c, '#9AB0D0', '#8A5A36', 820)
    rect(c, 200, 150, 700, 560, '#E8E0D0', LW)
    c.save(); c.clipRect(skia.Rect(220, 170, 680, 540)); _sky(c, time, 600); c.restore()
    line(c, 450, 150, 450, 560, LW * .7); line(c, 200, 355, 700, 355, LW * .7)
    rect(c, 1050, 520, 1150, 820, '#6A4428', LW); rect(c, 1050, 700, 1850, 820, '#3B6EA8', LW); rect(c, 1150, 640, 1350, 700, '#F4F4F2', LW * .7)
    rect(c, 860, 700, 1010, 820, WOOD, LW); line(c, 935, 700, 935, 620, 6); poly(c, [(880, 620), (990, 620), (965, 560), (905, 560)], '#FFF0C8', LW * .7)
    return _info(time, [('pool', 935, 600, 500, .95), ('pool', 450, 350, 500, .7)], [(935, 590, 300, '#FFD98A', 80)])


def set_hq(c, o):
    """A company HQ: a glass tower with the company's name on top, a plaza with trees."""
    time = o.get('time', 'day'); _sky(c, time, 860)
    blur_begin(c, 2.0); far_city(c, 760, time, 4); c.restore()
    rect(c, 700, 140, 1220, 860, '#7FB8DA' if time == 'day' else '#2A3A6A', LW)
    for j in range(14):
        for i in range(6): c.drawRect(skia.Rect(720 + i * 84, 170 + j * 48, 790 + i * 84, 205 + j * 48), fp('#BFE3F2' if time == 'day' else ('#F6DE96' if (i + j) % 3 else '#2A3A6A')))
    name = (o.get('sign') or (o.get('logo_art') or {}).get('title') or o.get('logo') or 'HQ').upper()
    _sign(c, name, 960, 80, 600, 120, '#1C1C22', '#FFFFFF', 80, o.get('logo_art'))
    _ground(c, 860, '#C9C2B4')
    for x in (300, 520, 1400, 1620): _tree(c, x, 900, .9, '#3E9A56')
    return _info(time, [('pool', 960, 500, 1000, .9)], [(960, 80, 400, '#FFFFFF', 40)] if time == 'night' else [])


NEW_SETS = dict(
    datacenter=set_datacenter, factory=set_factory, lab=set_lab, cutaway=set_cutaway, openoffice=set_openoffice,
    vault=set_vault, trading=set_trading, mining=set_mining, exchange=set_exchange,
    court=set_court, parliament=set_parliament, hospital=set_hospital, classroom=set_classroom, newsroom=set_newsroom,
    stage=set_stage, press=set_press, prison=set_prison, stadium=set_stadium, market=set_market,
    space=set_space, moon=set_moon, mars=set_mars, launchpad=set_launchpad,
    airport=set_airport, port=set_port, highway=set_highway, station=set_station,
    farm=set_farm, forest=set_forest, ocean=set_ocean, desert=set_desert, mountains=set_mountains,
    kitchen=set_kitchen, bedroom=set_bedroom, hq=set_hq,
)


# ---------------------------------------------------------------- batch 2 (owner 2026-11-21)
def set_casino(c, o):
    """Casino floor: dark red carpet, rows of slot machines with lit screens, a roulette table, gold lights."""
    c.drawRect(skia.Rect(L0, -700, R0, H + 700), fp('#2A0E18'))
    for k in range(-14, 48): c.drawCircle(k * 70, 60, 10, fp('#F2C14E'))
    for i in range(-4, 12):
        if _in_band(i * 230 + 115) and 380 < i * 230 + 115 < 1540: continue
        x = i * 230; rect(c, x + 20, 300, x + 210, 760, '#8A1F2A', LW * .7, r=20)
        rect(c, x + 45, 340, x + 185, 450, '#1A1D2A', LW * .5)
        for q in range(3): label(c, '7', x + 70 + q * 45, 425, 60, ['#F2C14E', '#FF5A5A', '#5FE08A'][q], align='center', skew=0)
        rect(c, x + 60, 500, x + 170, 540, '#F2C14E', LW * .4); line(c, x + 210, 520, x + 240, 420, 6); circ(c, x + 240, 412, 12, RED, LW * .4)
    _ground(c, 760, '#5A1420')
    for k in range(-10, 30):
        for j in range(4): c.drawCircle(k * 120 + (j % 2) * 60, 800 + j * 70, 12, fp('#7A1E2C'))
    oval(c, 700, 860, 1220, 980, '#2F6B45', LW); circ(c, 960, 905, 54, '#3A2A1A', LW * .6)
    for k in range(12): a = k * math.pi / 6; c.drawLine(960, 905, 960 + 50 * math.cos(a), 905 + 20 * math.sin(a), ink(3, RED if k % 2 else INK))
    return dict(floor=FLOOR, ambient='#7A4A5A', lights=[('pool', 960, 500, 1000, .9)], bulbs=[(960, 60, 1000, '#F2C14E', 40)],
                spots=[(520, FLOOR), (960, FLOOR), (1400, FLOOR)])


def set_church(c, o):
    """Church interior: stained-glass arches, pews, an altar with a cross."""
    _room(c, '#E8DCC4', '#9A7A54', 820)
    for x in (300, 1620):
        p = skia.Path(); p.moveTo(x - 110, 620); p.lineTo(x - 110, 260); p.quadTo(x, 120, x + 110, 260); p.lineTo(x + 110, 620); p.close()
        shape(c, p, '#3B6EA8', LW)
        c.save(); c.clipPath(p, doAntiAlias=True)
        for k, colr in enumerate(['#C8242C', '#F2C14E', '#3E9A56', '#8A5AB0', '#FF9A3C']):
            c.drawRect(skia.Rect(x - 110 + k * 44, 120, x - 66 + k * 44, 620), fp(colr, 160))
        c.restore(); c.drawPath(p, ink(LW))
    rect(c, 820, 560, 1100, 700, '#F4F0E6', LW); rect(c, 800, 540, 1120, 570, '#D0A548', LW * .7)
    line(c, 960, 520, 960, 260, 22, '#D0A548'); line(c, 900, 330, 1020, 330, 22, '#D0A548')
    for row, (y, sc) in enumerate(((880, .8), (990, 1.0))):
        for side in (-1, 1):
            x0, x1 = 960 + side * 160, 960 + side * 900
            rect(c, min(x0, x1), y - 40 * sc, max(x0, x1), y, WOOD, LW * .7)
    return _info(o.get('time', 'day'), [('pool', 960, 400, 900, .95), ('pool', 300, 380, 300, .8), ('pool', 1620, 380, 300, .8)],
                 [(960, 380, 400, '#FFF3C8', 50)])


def set_mosque(c, o):
    """A mosque courtyard: a dome, two minarets at the sides, arches, a calm sky."""
    time = o.get('time', 'dusk'); _sky(c, time, 860)
    for x in (140, 1780):
        rect(c, x - 40, 140, x + 40, 860, '#F4F0E6', LW); rect(c, x - 56, 300, x + 56, 330, '#D8D2C2', LW * .6)
        poly(c, [(x - 40, 140), (x + 40, 140), (x, 40)], '#3E9A56', LW * .7)
    p = skia.Path(); p.addArc(skia.Rect(700, 180, 1220, 600), 180, 180); p.close(); shape(c, p, '#3E9A56', LW)
    line(c, 960, 180, 960, 110, 6, '#D0A548'); circ(c, 960, 100, 14, '#D0A548', LW * .4)
    rect(c, 520, 390, 1400, 860, '#F4F0E6', LW)
    for k in range(5):
        x = 600 + k * 180; q = skia.Path(); q.moveTo(x, 860); q.lineTo(x, 600); q.quadTo(x + 60, 520, x + 120, 600); q.lineTo(x + 120, 860); q.close()
        shape(c, q, '#2F6B9A' if time != 'day' else '#8ABBCB', LW * .7)
    _ground(c, 860, '#D8D2C2')
    for k in range(-10, 30): c.drawLine(k * 120, 860, k * 120 - 200, H + 300, ink(3, '#C9C2B4'))
    return _info(time, [('pool', 960, 600, 1000, .95)], spots=[(400, FLOOR), (960, FLOOR), (1500, FLOOR)])


def set_village(c, o):
    """An African village: round huts with thatched roofs, a big shade tree, a dirt yard."""
    time = o.get('time', 'day'); _sky(c, time, 760)
    p = skia.Path(); p.moveTo(L0, 700)
    for k in range(-6, 20): p.quadTo(k * 260 + 130, 640 + (k % 2) * 30, k * 260 + 260, 700)
    p.lineTo(R0, 800); p.lineTo(L0, 800); p.close(); shape(c, p, '#8AAE5A', LW)
    for (x, sc) in ((180, 1.0), (1500, 1.1), (1800, .8)):
        rect(c, x - 140 * sc, 540 + (1 - sc) * 100, x + 140 * sc, 800, '#C98A5A', LW)
        poly(c, [(x - 190 * sc, 560 + (1 - sc) * 100), (x + 190 * sc, 560 + (1 - sc) * 100), (x, 360 + (1 - sc) * 160)], '#D8B064', LW)
        for k in range(6): c.drawLine(x - 160 * sc + k * 64 * sc, 555 + (1 - sc) * 100, x, 380 + (1 - sc) * 160, ink(2, '#B08A40'))
        rect(c, x - 36 * sc, 680, x + 36 * sc, 800, '#5A3A22', LW * .6, r=30 * sc)
    rect(c, 920, 480, 980, 800, '#6A4428', LW * .7)
    for (dx, dy, r) in ((-180, 430, 130), (0, 380, 170), (180, 430, 130)): oval(c, 950 + dx - r * 1.3, dy - r * .6, 950 + dx + r * 1.3, dy + r * .6, '#4F8A4A', LW * .7)
    _ground(c, 800, '#C9A06A')
    return _info(time, spots=[(500, FLOOR), (960, FLOOR), (1300, FLOOR)])


def set_warroom(c, o):
    """A war room: a lit world map wall with red markers, a long table, screens, dark blue light."""
    c.drawRect(skia.Rect(L0, -700, R0, H + 700), fp('#0E1426'))
    rect(c, 260, 100, 1660, 600, '#14203E', LW)
    r = random.Random(6)
    for (cx, cy, rx, ry) in ((560, 330, 230, 150), (1000, 280, 150, 110), (1060, 450, 120, 120), (1400, 320, 230, 140), (1480, 520, 90, 50)):
        oval(c, cx - rx, cy - ry, cx + rx, cy + ry, '#2A4A7A', LW * .5)
    for _ in range(9):
        x, y = r.uniform(340, 1580), r.uniform(160, 540); circ(c, x, y, 12, '#FF3A3A', LW * .4); c.drawCircle(x, y, 30, fp('#FF3A3A', 50))
    for i in range(-2, 4): _screen(c, i * 300 + 60 if i < 0 else 1700 + (i - 1) * 300, 160, (i * 300 + 260) if i < 0 else 1700 + (i - 1) * 300 + 200, 340, 'down' if i % 2 else 'up', i + 9)
    _ground(c, 820, '#1A2238')
    rect(c, 300, 820, 1620, 880, '#3A3F4C', LW); rect(c, 340, 880, 1580, 900, '#262A34', LW * .6)
    return dict(floor=FLOOR, ambient='#4A5AA0', lights=[('pool', 960, 350, 900, .95)], bulbs=[(960, 350, 800, '#7FC8F8', 40)],
                spots=[(520, FLOOR), (960, FLOOR), (1400, FLOOR)])


NEW_SETS.update(casino=set_casino, church=set_church, mosque=set_mosque, village=set_village, warroom=set_warroom)


def set_campus(c, o):
    """Aerial view of a tech campus (owner's model): a huge white flat-roof building with the company's real logo
    on the roof, rows of cooling units, trucks, trees, a far city skyline at dusk."""
    time = o.get('time', 'dusk')
    sky(c, time, 520)
    rr = random.Random(12)
    for k in range(40):
        x = 300 + k * 32 + rr.uniform(-6, 6); h = rr.uniform(60, 190)
        rect(c, x, 470 - h, x + 24, 470, rr.choice(['#5A62A8', '#6A72B8', '#4E569A']), 0)
        for j in range(int(h // 18)): c.drawRect(skia.Rect(x + 4, 470 - h + 6 + j * 18, x + 20, 470 - h + 10 + j * 18), fp('#DCE4FF', 160))
    p = skia.Path(); p.addArc(skia.Rect(-120, 380, 360, 760), 200, 140); c.drawPath(p, ink(14, '#B9BDC6'))
    c.drawRect(skia.Rect(L0, 470, R0, H + 700), fp('#7FA84E'))
    for k in range(9): c.drawRect(skia.Rect(L0, 470 + k * k * 9, R0, 474 + k * k * 9), fp('#76A04A'))
    for _ in range(70):
        x, y = rr.uniform(L0, R0), rr.uniform(500, 1060); s_ = .25 + (y - 470) / 1100
        if 380 < x < 1580 and 600 < y < 940: continue
        c.drawCircle(x + 10 * s_, y + 6 * s_, 26 * s_, fp('#4E7A34')); circ(c, x, y, 24 * s_, '#5E9A42', LW * .4 * s_)
    top = [(470, 640), (1450, 640), (1640, 760), (280, 760)]
    poly(c, top, '#F4F5F8', LW)
    poly(c, [(280, 760), (1640, 760), (1640, 880), (280, 880)], '#E4E6EC', LW)
    for i in range(14): rect(c, 330 + i * 94, 800, 380 + i * 94, 880, '#B9BDC6', LW * .4)
    rect(c, 900, 800, 1020, 880, '#BFE3A0', LW * .5)
    for j in range(4):
        for i in range(16):
            fx = (i + .5) / 16; fy = (j + .5) / 4
            x0 = 470 + (280 - 470) * fy + ((1450 + (1640 - 1450) * fy) - (470 + (280 - 470) * fy)) * fx; y0 = 640 + 120 * fy
            c.drawLine(x0 - 10, y0, x0 + 10, y0, ink(4, '#B9BDC6'))
    art = o.get('logo_art'); name = (o.get('sign') or (art or {}).get('title') or o.get('logo') or '').upper()
    poly(c, [(800, 664), (1120, 664), (1160, 736), (760, 736)], '#1C1C22', LW * .6)
    if not brand(c, art, 960, 700, 62) and name:
        label(c, name, 960, 716, fit_size(name, 44, 330), '#FFFFFF', align='center', skew=0)
    for side in (-1, 1):
        for j in range(3):
            for i in range(6):
                x = (180 if side < 0 else 1680) + i * 34 * side + j * 14; y = 700 + j * 40 + i * 6
                rect(c, x - 14, y - 10, x + 14, y + 10, '#DCE0E8', LW * .3)
    for (x, y) in ((620, 960), (1300, 1000)):
        rect(c, x - 18, y - 60, x + 18, y + 30, '#F4F5F8', LW * .5); rect(c, x - 18, y - 60, x + 18, y - 40, '#3A3F4C', 0)
    return dict(floor=FLOOR, ambient=AMBIENT.get(time), lights=[('pool', 960, 700, 900, .95)], bulbs=[], spots=[(520, FLOOR), (1400, FLOOR)])


NEW_SETS.update(campus=set_campus)


def register(sets_module) -> None:
    from golide_engine.stickman.rm_art import art
    for k, v in NEW_SETS.items():
        sets_module.SETS.setdefault(k, art(v))
