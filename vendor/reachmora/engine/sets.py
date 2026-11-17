"""Reusable sets. Each set draws its static background and returns an info dict:
floor (feet y for s=1 characters), lights (for night()), ambient, bulbs (add_light after night)."""
import math, random
import skia
from .kit import *

AMBIENT = dict(night='#4C5CA0', dusk='#9C7FA6', day='#F2EEE8')
_r = random.Random(7)
STARS = [(_r.uniform(-300, W + 300), _r.uniform(-200, 760), _r.choice((1.6, 2.0, 2.6, 3.2)), _r.uniform(0, 6)) for _ in range(130)]
SPECK = [(_r.uniform(-200, W + 200), _r.uniform(-100, H + 100), _r.uniform(1.5, 4.5), _r.uniform(40, 110)) for _ in range(300)]


def sky(c, time, h=860, x0=-2000, x1=W + 2000):
    top, bot = dict(night=('#0A1136', '#24338A'), dusk=('#3A2A6A', '#F09A6A'), day=('#5FB2EE', '#CDEBFA'))[time]
    c.drawRect(skia.Rect(x0, -1500, x1, H + 1500), sp(linear(0, 0, 0, h, [hx(top), hx(bot)])))


def stars(c):
    for (sx, sy, r, ph) in STARS: c.drawCircle(sx, sy, r, fp('#E8ECFF', 150 + 90 * math.sin(ph)))


def moon(c, x, y, r=50):
    for k, a in ((3.0, 16), (2.2, 22), (1.55, 30)): c.drawCircle(x, y, r * k, fp('#C9D4FF', a))
    c.drawCircle(x, y, r, fp('#F3EDD3')); c.drawCircle(x - r * .3, y - r * .25, r * .16, fp('#D9D2B4')); c.drawCircle(x + r * .25, y + r * .3, r * .22, fp('#DDD6B8'))


def sun(c, x, y, r=60):
    for k, a in ((3.2, 20), (2.2, 34), (1.5, 60)): c.drawCircle(x, y, r * k, fp('#FFF3B0', a))
    circ(c, x, y, r, '#FFE27A', LW * .8)


def cloud(c, x, y, s, v='#2C3B80', a=255):
    p = skia.Path()
    for dx, dy, r in ((-70, 8, 34), (-30, -14, 46), (22, -6, 40), (64, 10, 30)): p.addCircle(x + dx * s, y + dy * s, r * s)
    p.addRect(skia.Rect(x - 100 * s, y + 8 * s, x + 92 * s, y + 40 * s)); c.drawPath(p, fp(v, a))


def block(c, x, w, h, base, seed, time, lit=.4, lw=LW, body=None, roof=None):
    r = random.Random(seed); top = base - h
    pal = dict(night=('#1C2658', '#131A42', '#263272'), dusk=('#5A4070', '#3E2C55', '#6E5288'), day=('#D9C6A5', '#9E6B4A', '#8FB5D0'))[time]
    body = body or [pal[0], '#C7B08F', '#B8C4CF', '#D7A98A'][seed % 4] if time == 'day' else body or pal[0]
    rect(c, x, top, x + w, base + 600, body, lw)
    poly(c, [(x - 8, top), (x + 16, top - 40), (x + w - 16, top - 40), (x + w + 8, top)], roof or pal[1], lw)
    cols = max(2, int((w - 30) // 46)); rows = int((h - 30) // 62); gap = (w - cols * 22) / (cols + 1)
    for j in range(rows):
        for i in range(cols):
            wx, wy = x + gap + i * (22 + gap), top + 26 + j * 62; on = r.random() < lit and time != 'day'
            rect(c, wx, wy, wx + 22, wy + 36, '#F2D88C' if on else pal[2], lw * .5)
            if on: c.drawRect(skia.Rect(wx - 8, wy - 8, wx + 30, wy + 44), fp('#FFD98A', 34, blur=7))


def far_city(c, base, time, seed=3):
    v = dict(night='#1A2560', dusk='#5C4A7E', day='#9DB8D2')[time]; r = random.Random(seed); x = -400
    while x < W + 400:
        w = r.uniform(90, 200); h = r.uniform(120, 260)
        c.drawRect(skia.Rect(x, base - h, x + w, base + 300), fp(v)); c.drawRect(skia.Rect(x + 10, base - h - 26, x + w - 10, base - h), fp(v))
        if time != 'day':
            for j in range(int(h // 50)):
                for i in range(int(w // 40)):
                    if r.random() < .3: c.drawRect(skia.Rect(x + 12 + i * 40, base - h + 16 + j * 50, x + 24 + i * 40, base - h + 36 + j * 50), fp('#E9CF86', 200))
        x += w + r.uniform(-6, 10)


def city_view(c, x0, y0, x1, y1, time, seed=5):
    c.save(); c.clipRect(skia.Rect(x0, y0, x1, y1))
    sky(c, time, y1, x0, x1)
    if time == 'night': stars(c); moon(c, x0 + 100, y0 + 84, 30)
    elif time == 'day': sun(c, x1 - 120, y0 + 100, 40); cloud(c, x0 + 230, y0 + 150, .7, '#FFFFFF', 230)
    blur_begin(c, 1.6); c.save(); c.translate(x0, y0 + 160); c.scale(.5, .5); far_city(c, 800, time, seed); c.restore(); c.restore()
    w = x1 - x0
    for k, (fx, fw, fh) in enumerate(((.0, .23, .28), (.26, .2, .4), (.62, .22, .33), (.86, .2, .46))):
        block(c, x0 + fx * w, fw * w, fh * (y1 - y0), y1, seed * 10 + k, time, lw=LW * .7)
    for k in (0, 1):
        px = x0 + 100 + k * 150
        c.drawPath(skia.Path.Polygon([(px, y0), (px + 60 - k * 30, y0), (px - 190 + 60 - k * 30, y1), (px - 190, y1)], True), fp('#FFFFFF', 15))
    c.restore()


def window(c, x0, y0, x1, y1, time, frame='#3B2416', seed=5, curtains='#93222B'):
    city_view(c, x0, y0, x1, y1, time, seed)
    for (a, b, cc, d) in ((x0 - 22, y0 - 22, x1 + 22, y0), (x0 - 22, y1, x1 + 22, y1 + 22), (x0 - 22, y0, x0, y1), (x1, y0, x1 + 22, y1)):
        rect(c, a, b, cc, d, frame, LW * .8)
    mx = (x0 + x1) / 2; my = y0 + (y1 - y0) * .38
    line(c, mx, y0, mx, y1, 14, INK); line(c, mx, y0, mx, y1, 7, frame); line(c, x0, my, x1, my, 14, INK); line(c, x0, my, x1, my, 7, frame)
    rect(c, x0 - 44, y1 + 22, x1 + 44, y1 + 48, shade(frame, 1.3), LW * .8)
    if curtains:
        line(c, x0 - 110, y0 - 36, x1 + 110, y0 - 36, 12, INK); line(c, x0 - 110, y0 - 36, x1 + 110, y0 - 36, 6, '#C9A04A')
        for (cx0, cx1) in ((x0 - 96, x0 - 14), (x1 + 14, x1 + 96)):
            poly(c, [(cx0, y0 - 36), (cx1, y0 - 36), (cx1 + 8, y1 + 60), (cx0 - 10, y1 + 60)], curtains, LW)
            for k in (1, 2, 3): c.drawLine(cx0 + k * (cx1 - cx0) / 4, y0 - 30, cx0 - 6 + k * (cx1 - cx0 + 14) / 4, y1 + 54, ink(4, shade(curtains, .75)))
    p = skia.Path(); p.addRect(skia.Rect(x0, y0, x1, y1)); return p


# ---------------------------------------------------------------- small set dressing
def wall_clock(c, x, y, r=62):
    circ(c, x, y, r, '#F4EFE2', LW); line(c, x, y, x, y - r * .68, LW * .8); line(c, x, y, x + r * .45, y + r * .2, LW * .8); c.drawCircle(x, y, 5, fp(INK))


def calendar(c, x, y, top='MAY', big='12'):
    rect(c, x, y, x + 140, y + 170, '#F7F3E8', LW); rect(c, x, y, x + 140, y + 48, '#C8242C', LW)
    label(c, top, x + 70, y + 38, fit_size(top, 38, 120), CREAM, align='center', skew=-0.1); label(c, big, x + 70, y + 130, fit_size(big, 64, 120), INK, align='center', skew=-0.1)


def frame_pic(c, x, y, w=170, h=210):
    rect(c, x, y, x + w, y + h, '#C39A45', LW); rect(c, x + 18, y + 18, x + w - 18, y + h - 18, '#EFE6CE', LW * .6)
    poly(c, [(x + 26, y + h - 28), (x + 60, y + h - 100), (x + 86, y + h - 60), (x + 114, y + h - 120), (x + w - 26, y + h - 28)], '#9DB7A6', LW * .5)
    c.drawCircle(x + w - 58, y + 54, 13, fp('#E9B44C'))


def banker_lamp(c, x, y):
    oval(c, x - 58, y - 16, x + 58, y + 6, '#D0A548', LW * .8); line(c, x, y - 8, x, y - 118, 12, INK); line(c, x, y - 8, x, y - 118, 6, '#E3BC5C')
    sh = skia.Path(); sh.moveTo(x - 116, y - 112); sh.cubicTo(x - 96, y - 196, x + 96, y - 196, x + 116, y - 112); sh.close(); shape(c, sh, '#2FA25E', LW)
    hl = skia.Path(); hl.moveTo(x - 82, y - 138); hl.quadTo(x - 50, y - 172, x - 4, y - 174); c.drawPath(hl, ink(7, '#8FE0AE'))
    oval(c, x - 104, y - 122, x + 104, y - 100, '#FFF3B8', LW * .7)
    for i in range(6):
        a = math.radians(60 + i * 12); c.drawLine(x + 70 * math.cos(a), y - 96, x + 150 * math.cos(a), y - 96 + 84 * math.sin(a), ink(2.4, '#FFF6D0', 110))


def old_phone(c, x, y):
    oval(c, x - 44, y - 16, x + 44, y + 6, '#1E1E26', LW * .8); line(c, x, y - 8, x, y - 110, 16, INK); line(c, x, y - 8, x, y - 110, 8, '#2C2C38')
    circ(c, x + 4, y - 122, 20, '#2C2C38', LW * .8); circ(c, x + 12, y - 122, 9, '#14141A', LW * .5)
    line(c, x - 6, y - 76, x - 38, y - 86, LW * .8); rect(c, x - 62, y - 128, x - 36, y - 50, '#2C2C38', LW * .8, r=10)


def monitor(c, x, y, glow='#7FD0FF'):
    rect(c, x - 20, y - 70, x + 20, y, '#3A3A46', LW * .8); rect(c, x - 70, y - 10, x + 70, y + 4, '#3A3A46', LW * .8)
    rect(c, x - 170, y - 260, x + 170, y - 60, '#2A2A34', LW, r=10); rect(c, x - 150, y - 244, x + 150, y - 78, glow, LW * .6, r=4)
    for i in range(5): c.drawRect(skia.Rect(x - 130, y - 220 + i * 28, x - 130 + (180 - i * 23) % 240 + 40, y - 208 + i * 28), fp('#FFFFFF', 150))


def plant(c, x, y, s=1.0):
    poly(c, [(x - 46 * s, y - 90 * s), (x + 46 * s, y - 90 * s), (x + 34 * s, y), (x - 34 * s, y)], '#B5653A', LW)
    for a_ in (-70, -35, 0, 30, 60):
        fr = skia.Path(); fr.moveTo(x, y - 90 * s); fr.quadTo(x + a_ * 1.2 * s, y - 250 * s, x + a_ * 2.6 * s, y - (280 - abs(a_)) * s)
        c.drawPath(fr, ink(24 * s, INK)); c.drawPath(fr, ink(13 * s, '#3E9A56'))


def rug(c, x0, y0, x1, y1, v='#7E2A30'):
    oval(c, x0, y0, x1, y1, v, LW * .8); c.drawOval(skia.Rect(x0 + 40, y0 + 14, x1 - 40, y1 - 14), ink(6, '#C39A45'))


def street_lamp(c, x, y_base, y_top):
    line(c, x, y_base, x, y_top, 22, INK); line(c, x, y_base, x, y_top, 11, '#2B2D3C'); rect(c, x - 22, y_base - 26, x + 22, y_base + 4, '#2B2D3C', LW * .8)
    poly(c, [(x - 40, y_top + 4), (x + 40, y_top + 4), (x + 26, y_top - 72), (x - 26, y_top - 72)], '#FFF0B4', LW)
    poly(c, [(x - 48, y_top - 72), (x + 48, y_top - 72), (x, y_top - 112)], '#2B2D3C', LW); line(c, x - 40, y_top + 4, x + 40, y_top + 4, LW)


# ---------------------------------------------------------------- sets
WALLS = dict(green=('#2F5449', '#2A4C42'), blue=('#2E3E66', '#283759'), plum=('#4A2F52', '#412948'), teal=('#22545A', '#1E4A50'),
             sand=('#C9A97A', '#B9986A'), grey=('#4A4E5A', '#41454F'), cream=('#E8DCC0', '#DACDAE'), brick=('#8A4A3A', '#7A3F31'))


def set_office(c, o):
    time = o.get('time', 'night'); wall, stripe = WALLS.get(o.get('wall', 'green'), WALLS['green'])
    c.drawRect(skia.Rect(-900, -600, W + 900, 820), fp(wall))
    for i in range(-14, 48): c.drawLine(i * 62, -600, i * 62, 650, ink(10, stripe))
    c.drawRect(skia.Rect(-900, 650, W + 900, 820), fp('#4E3020'))
    for i in range(-5, 16): rect(c, i * 190 + 24, 676, i * 190 + 170, 796, '#462A1B', LW * .6)
    line(c, -900, 650, W + 900, 650, LW); c.drawRect(skia.Rect(-900, 820, W + 900, H + 600), fp('#6A4429'))
    for i in range(1, 9): c.drawLine(-900, 820 + i * i * 6.5, W + 900, 820 + i * i * 6.5, ink(3, '#553520'))
    line(c, -900, 820, W + 900, 820, LW)
    win = window(c, 150, 96, 800, 640, time, seed=o.get('seed', 5))
    frame_pic(c, 990, 190); wall_clock(c, 1330, 250); calendar(c, 1500, 170, *(o.get('calendar', 'MAY 12').split(' ', 1) + ['12'])[:2])
    rect(c, 1430, 560, 1610, 800, '#7A2228', LW, r=26)
    c.drawOval(skia.Rect(1160, 1030, 1900, 1090), fp((0, 0, 0), 70, blur=14)); rect(c, 1230, 800, 1850, 1062, '#6E4426', LW)
    for (dx0, dx1) in ((1262, 1520), (1560, 1818)):
        rect(c, dx0, 836, dx1, 930, '#7C4E2C', LW * .7); circ(c, (dx0 + dx1) / 2, 883, 9, '#D0A548', LW * .6)
        rect(c, dx0, 956, dx1, 1040, '#7C4E2C', LW * .7); circ(c, (dx0 + dx1) / 2, 998, 9, '#D0A548', LW * .6)
    rect(c, 1196, 770, 1884, 802, '#8E5C36', LW); c.drawRect(skia.Rect(1250, 773, 1830, 782), fp('#2F6B45'))
    banker_lamp(c, 1740, 770)
    if o.get('era', 'modern') == 'old': old_phone(c, 1320, 770)
    else: monitor(c, 1440, 770)
    for k in range(3): rect(c, 1260 + k * 5, 752 - k * 6, 1380 + k * 5, 764 - k * 6, '#F7F3E8', LW * .6)
    plant(c, 60, 1000, .9); rug(c, 560, 930, 1360, 1070)
    spill = skia.Path.Polygon([(190, 700), (760, 700), (1040, 1090), (330, 1090)], True)
    return dict(floor=1024, ambient=AMBIENT[time],
                lights=[('pool', 1740, 720, 600, .95), ('pool', 1000, 560, 430, .92), ('oval', 1000, 1000, 380, 110, .7), ('path', win, .82, 10), ('path', spill, .36, 34)],
                bulbs=[(1740, 690, 430, '#FFD98A', 70), (1740, 664, 120, '#FFF3C8', 150)], spots=[(520, 1024), (1000, 1024), (1300, 1024)])


def set_home(c, o):
    time = o.get('time', 'night'); wall, stripe = WALLS.get(o.get('wall', 'plum'), WALLS['plum'])
    c.drawRect(skia.Rect(-900, -600, W + 900, 840), fp(wall))
    for i in range(-14, 48):
        for j in range(-6, 14): c.drawCircle(i * 70 + (j % 2) * 35, j * 70, 7, fp(stripe))
    c.drawRect(skia.Rect(-900, 760, W + 900, 840), fp(shade(wall, .7))); line(c, -900, 760, W + 900, 760, LW)
    c.drawRect(skia.Rect(-900, 840, W + 900, H + 600), fp('#8A5A36'))
    for i in range(-10, 40): c.drawLine(i * 120, 840, i * 120 - 260, H + 300, ink(3, '#764C2C'))
    line(c, -900, 840, W + 900, 840, LW)
    win = window(c, 1180, 130, 1700, 600, time, frame='#E8E0D0', seed=o.get('seed', 8), curtains='#3F7A8C')
    # bookshelf
    rect(c, 120, 200, 520, 820, '#6A4428', LW)
    r = random.Random(3)
    for k in range(4):
        y = 230 + k * 150; rect(c, 140, y + 128, 500, y + 142, '#5A3824', LW * .6); x = 152
        while x < 480:
            w = r.uniform(22, 40); h = r.uniform(80, 120); rect(c, x, y + 128 - h, x + w, y + 128, r.choice(['#C8242C', '#2F6B9A', '#D0A548', '#3E9A56', '#E8E0D0', '#7A4A8A']), LW * .5); x += w + 4
    # sofa
    c.drawOval(skia.Rect(620, 1020, 1300, 1080), fp((0, 0, 0), 70, blur=14))
    rect(c, 640, 760, 1280, 900, '#C2563A', LW, r=30); rect(c, 610, 840, 700, 1040, '#C2563A', LW, r=26); rect(c, 1220, 840, 1310, 1040, '#C2563A', LW, r=26)
    rect(c, 690, 880, 1230, 1000, '#D8694A', LW, r=20); line(c, 960, 885, 960, 995, LW * .7)
    # floor lamp
    line(c, 1500, 1040, 1500, 640, 14, INK); line(c, 1500, 1040, 1500, 640, 7, '#D0A548'); oval(c, 1440, 1030, 1560, 1052, '#2B2D3C', LW * .7)
    poly(c, [(1430, 640), (1570, 640), (1540, 540), (1460, 540)], '#FFF0C8', LW)
    plant(c, 1800, 1010, 1.0); rug(c, 520, 980, 1420, 1120, '#3F6E8C')
    return dict(floor=1030, ambient=AMBIENT[time],
                lights=[('pool', 1500, 640, 640, .95), ('pool', 960, 640, 520, .8), ('path', win, .8, 10), ('oval', 960, 1030, 520, 120, .6)],
                bulbs=[(1500, 600, 360, '#FFD98A', 80)], spots=[(800, 1030), (1120, 1030), (1450, 1030)])


def set_street(c, o):
    time = o.get('time', 'night'); sky(c, time, 760)
    if time == 'night': stars(c); moon(c, 1500, 150, 36); cloud(c, 700, 220, 1.0)
    elif time == 'day': sun(c, 1560, 160); cloud(c, 500, 210, 1.2, '#FFFFFF', 235); cloud(c, 1200, 300, .9, '#FFFFFF', 220)
    else: cloud(c, 700, 260, 1.1, '#E58A7A')
    blur_begin(c, 2.0); far_city(c, 660, time, 8); c.restore()
    for (x, w, h, sd) in ((-90, 300, 500, 21), (210, 240, 410, 22), (1660, 250, 400, 24), (1900, 260, 470, 25)):
        block(c, x, w, h, 760, sd, time, lit=.34)
    shop = o.get('shop', 'CAFE'); awn = o.get('awning', '#C8242C')
    rect(c, 1090, 470, 1660, 760, '#4A3550' if time != 'day' else '#B9876A', LW)
    rect(c, 1140, 560, 1380, 720, '#F6DE96' if time != 'day' else '#BFE3F2', LW); line(c, 1260, 560, 1260, 720, LW * .7)
    rect(c, 1440, 540, 1580, 760, '#6A4428', LW); circ(c, 1558, 660, 7, '#D0A548', LW * .5)
    aw = poly(c, [(1070, 470), (1680, 470), (1710, 540), (1040, 540)], awn, LW)
    c.save(); c.clipPath(aw, doAntiAlias=True)
    for i in range(0, 14, 2): c.drawPath(skia.Path.Polygon([(1070 + i * 46, 470), (1116 + i * 46, 470), (1092 + i * 48, 540), (1044 + i * 48, 540)], True), fp('#F4EFE2'))
    c.restore(); c.drawPath(aw, ink(LW)); label(c, shop, 1375, 452, fit_size(shop, 60, 520), '#F6DE96', align='center', stroke=8, skew=-0.1)
    pav, road = ('#444B70', '#30365A') if time != 'day' else ('#B8B2A8', '#8C8A90')
    c.drawRect(skia.Rect(-900, 760, W + 900, 840), fp(pav)); line(c, -900, 760, W + 900, 760, LW); line(c, -900, 840, W + 900, 840, LW)
    c.drawRect(skia.Rect(-900, 840, W + 900, H + 600), fp(road)); r = random.Random(4)
    for row in range(7):
        yy = 856 + row * 36 + row * row * 1.5; wd = 84 + row * 8
        for kx in range(-6, 32):
            xx = kx * (wd + 10) + (row % 2) * wd / 2 - 100
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(xx, yy, xx + wd, yy + 24 + row * 2), 10, 10), fp(shade(road, 1.12) if r.random() < .7 else shade(road, 1.25)))
    street_lamp(c, 560, 842, 330); cone = cone_path(560, 300, 80, 760, 780, lean=110)
    return dict(floor=1000, ambient=dict(night='#5A69B6', dusk=AMBIENT['dusk'], day=AMBIENT['day'])[time],
                lights=[('path', cone, .92, 24), ('oval', 690, 1000, 520, 120, .85), ('pool', 1260, 640, 380, .9), ('pool', 960, 560, 420, .5)],
                bulbs=[(560, 290, 130, '#FFF0B4', 170), (1260, 640, 360, '#FFD98A', 44)], cone=cone, spots=[(400, 1000), (860, 1000), (1300, 1000)])


def set_skyline(c, o):
    time = o.get('time', 'night'); sky(c, time, 900)
    if time == 'night': stars(c); moon(c, 1570, 190)
    elif time == 'day': sun(c, 1560, 180, 70)
    for (x, y, s_) in ((380, 250, 1.5), (1250, 360, 1.1), (1760, 470, .9)):
        cloud(c, x, y, s_, dict(night='#2C3B80', dusk='#E58A7A', day='#FFFFFF')[time], 230)
    blur_begin(c, 2.2); far_city(c, 800, time, o.get('seed', 3)); c.restore()
    for (x, w, h, sd) in ((-60, 250, 300, 1), (190, 210, 380, 2), (400, 250, 250, 3), (650, 170, 460, 9), (840, 230, 560, 6), (1090, 190, 420, 7),
                          (1330, 190, 260, 8), (1500, 240, 330, 4), (1740, 230, 400, 5)):
        block(c, x, w, h, 866, sd, time)
    water = dict(night=('#16215A', '#0A1034'), dusk=('#6A4A7A', '#3A2A55'), day=('#7FB8DA', '#4F8FB8'))[time]
    c.drawRect(skia.Rect(-900, 866, W + 900, H + 500), sp(linear(0, 866, 0, 1080, [hx(water[0]), hx(water[1])]))); c.drawLine(-900, 866, W + 900, 866, ink(LW))
    for i in range(30):
        yy = 884 + i * 7.5 + (i % 3) * 2; xx = (i * 211) % (W + 500) - 250
        c.drawLine(xx, yy, xx + 50 + (i % 4) * 26, yy, ink(3.5, '#F2D88C' if time != 'day' else '#FFFFFF', 120 - i * 2))
    return dict(floor=1000, ambient=AMBIENT[time] if time != 'night' else '#6A78C0',
                lights=[('pool', 960, 600, 900, .55)], bulbs=[], spots=[(960, 1000)])


def set_board(c, o):
    time = o.get('time', 'day'); wall, stripe = WALLS.get(o.get('wall', 'cream'), WALLS['cream'])
    c.drawRect(skia.Rect(-900, -600, W + 900, 900), fp(wall))
    for i in range(-14, 48): c.drawLine(i * 62, -600, i * 62, 900, ink(8, stripe))
    c.drawRect(skia.Rect(-900, 900, W + 900, H + 600), fp('#7A5236')); line(c, -900, 900, W + 900, 900, LW)
    kind = o.get('board', 'chalk'); bc = '#2F5A46' if kind == 'chalk' else '#F8F8F2'
    rect(c, 240, 110, 1680, 800, '#8E5C36', LW, r=8); rect(c, 270, 140, 1650, 770, bc, LW * .7)
    if kind == 'chalk':
        r = random.Random(2)
        for _ in range(40): c.drawCircle(r.uniform(290, 1630), r.uniform(160, 750), r.uniform(20, 70), fp('#FFFFFF', 6))
    rect(c, 300, 800, 1620, 824, '#A87A50', LW * .7)
    return dict(floor=1060, ambient=AMBIENT[time], lights=[('pool', 960, 460, 1100, .9)], bulbs=[], board=(270, 140, 1650, 770),
                chalk=(kind == 'chalk'), spots=[(160, 1060), (1780, 1060)])


def set_table(c, o):
    paper = o.get('paper', '#F6EED4'); felt = o.get('felt', '#2F6B45')
    c.drawRect(skia.Rect(-900, -700, W + 900, H + 700), sp(radial(960, 520, 1300, [hx(paper), hx(shade(paper, .94)), hx(shade(paper, .84))], [0, .6, 1])))
    for (sx, sy, r, a) in SPECK: c.drawCircle(sx, sy, r, fp('#9A8F6E', a))
    for (ya, yb) in ((-700, 64), (1016, H + 700)): c.drawRect(skia.Rect(-900, ya, W + 900, yb), fp(felt))
    for yy in (64, 1016): line(c, -900, yy, W + 900, yy, LW)
    return dict(floor=None, ambient=None, lights=[], bulbs=[])


def set_void(c, o):
    v = o.get('color', '#F3E6C8'); c.drawRect(skia.Rect(-900, -700, W + 900, H + 700), sp(radial(960, 520, 1400, [hx(shade(v, 1.08)), hx(v), hx(shade(v, .8))], [0, .55, 1])))
    for (sx, sy, r, a) in SPECK[::2]: c.drawCircle(sx, sy, r, fp(shade(v, .7), a * .6))
    if o.get('floor', True):
        c.drawRect(skia.Rect(-900, 1010, W + 900, H + 700), fp(shade(v, .82))); line(c, -900, 1010, W + 900, 1010, LW)
    return dict(floor=1010, ambient=None, lights=[], bulbs=[], spots=[(560, 1010), (960, 1010), (1360, 1010)])


def set_black(c, o):
    c.drawRect(skia.Rect(-W, -H, 2 * W, 2 * H), fp(o.get('color', '#000000'))); return dict(floor=None, ambient=None, lights=[], bulbs=[])


def set_map(c, o):
    c.drawRect(skia.Rect(-900, -700, W + 900, H + 700), fp('#0E1840'))
    for i in range(-8, 30): c.drawLine(i * 120, -700, i * 120, H + 700, ink(2, '#1A2658')); c.drawLine(-900, i * 120, W + 900, i * 120, ink(2, '#1A2658'))
    r = random.Random(o.get('seed', 1))

    def blob(cx, cy, rx, ry, n=14, jag=.22):
        p = skia.Path(); pts = []
        for i in range(n):
            a = i * 2 * math.pi / n; k = 1 + r.uniform(-jag, jag); pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
        p.moveTo((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]; p.quadTo(a[0], a[1], (a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        p.close(); return p
    for (cx, cy, rx, ry) in ((380, 640, 620, 520), (1560, 560, 560, 480), (1000, 120, 300, 140)):
        land = blob(cx, cy, rx, ry); c.drawPath(land, fp('#2A3A80')); c.drawPath(land, ink(LW))
        c.save(); c.clipPath(land, doAntiAlias=True)
        for i in range(-6, 26): c.drawLine(i * 120, -700, i * 120, H + 700, ink(2, '#34468E'))
        c.restore()
    for _ in range(4):
        x, y = r.uniform(700, 1250), r.uniform(700, 1000); isl = blob(x, y, r.uniform(30, 70), r.uniform(20, 45), 8); shape(c, isl, '#2A3A80', LW * .7)
    for k in range(18):  # waves
        x, y = r.uniform(820, 1150), r.uniform(250, 1000); w = skia.Path(); w.moveTo(x, y); w.quadTo(x + 14, y - 10, x + 28, y); w.quadTo(x + 42, y + 10, x + 56, y); c.drawPath(w, ink(3, '#2C3C86'))
    return dict(floor=None, ambient=None, lights=[], bulbs=[])


SETS = dict(office=set_office, home=set_home, street=set_street, skyline=set_skyline, board=set_board, table=set_table,
            void=set_void, black=set_black, map=set_map)
