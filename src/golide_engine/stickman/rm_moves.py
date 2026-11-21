"""Moving pictures and camera moves for ReachMora shots (owner 2026-11-21: "I don't want it to be boring").

Any shot can carry `"moves": [{"do": "<name>", "at": "<spoken word>", ...}]`. Each move starts on its word and plays
in the kit's ink style on top of the place (after the props, before labels). `"cam"` may also be a preset name
(push, pull, pan_left, pan_right, tilt_up, tilt_down, crane, orbit, shake). Loaded into the kit's engine.shots by
rm_hook/sitecustomize.py; the kit's own files are never edited.
"""
import math
import random

import skia
from engine.kit import *  # noqa: F401,F403
from engine.fx import poplabel, stamp
from golide_engine.stickman.rm_sets import brand

_R = random.Random(11)
BILLS = [(_R.uniform(-300, W + 300), _R.uniform(0, 1), _R.uniform(.6, 1.4), _R.uniform(0, 6.28), _R.uniform(.6, 1.1)) for _ in range(70)]
CONF = [(_R.uniform(0, W), _R.uniform(0, 1), _R.uniform(0, 6.28), _R.choice((RED, GOLD, LIME, SKY, PINK, '#FFFFFF'))) for _ in range(120)]
DIRS = [(_R.uniform(0, 6.28), _R.uniform(.5, 1.2)) for _ in range(28)]

CAM = {
    "push": {"zoom": [1.0, 1.22]},
    "pull": {"zoom": [1.25, 1.0]},
    "pan_left": {"zoom": [1.18, 1.18], "focus": [[1120, 545], [800, 545]]},
    "pan_right": {"zoom": [1.18, 1.18], "focus": [[800, 545], [1120, 545]]},
    "tilt_up": {"zoom": [1.2, 1.2], "focus": [[960, 700], [960, 400]]},
    "tilt_down": {"zoom": [1.2, 1.2], "focus": [[960, 400], [960, 700]]},
    "crane": {"zoom": [1.3, 1.05], "focus": [[960, 760], [960, 500]]},
    "orbit": {"zoom": [1.12, 1.2], "rot": 4},
    "shake": {"zoom": [1.05, 1.1]},
}


def _bill(c, x, y, s, rot):
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(s, s)
    rect(c, -60, -28, 60, 28, '#7DBE7A', LW * .6, r=4); circ(c, 0, 0, 16, '#5FA05A', LW * .4); label(c, '$', 0, 9, 26, '#2F6B45', align='center', skew=0)
    c.restore()


def _stack(c, x, y, s):
    rect(c, x - 80 * s, y - 34 * s, x + 80 * s, y, '#7DBE7A', LW * .6 * s, r=4); rect(c, x - 14 * s, y - 34 * s, x + 14 * s, y, '#F6EED4', 0)


def m_money_rain(c, u, d, t):
    for (x, ph, s, rot, sp) in BILLS:
        y = -120 + ((ph + u * sp * 1.4) % 1.2) * 1400
        _bill(c, x + 40 * math.sin(t * 2 + rot), y, s * d.get("s", 1), rot + t * sp * 2)


def m_cash_pile(c, u, d, t):
    x, y, s = d.get("x", 960), d.get("y", 1000), d.get("s", 1)
    n = int(1 + ease_out(min(1, u * 1.2)) * d.get("n", 12))
    for k in range(n):
        col_, row = k % 4, k // 4
        _stack(c, x + (col_ - 1.5) * 170 * s + row * 20 * s, y - row * 36 * s, s)
    if d.get("text") and u > .6: poplabel(c, d["text"], x, y - (n // 4 + 2) * 40 * s - 60, (u - .6) * 3, 90, GOLD, -4)


def m_rocket_launch(c, u, d, t):
    x, y0 = d.get("x", 1400), d.get("y", 860); rise = 1700 * ease(max(0, u - .15) / .85) ** 1.6
    y = y0 - rise
    for k in range(14):
        a = k / 14 * math.pi; r = 40 + 160 * min(1, u * 2)
        circ(c, x + math.cos(a) * r * 1.8 - r * .0, y0 + 40 - math.sin(a) * r * .25, 40 + 40 * min(1, u * 2), '#E8E4DA', LW * .4)
    fl = 90 + 30 * math.sin(t * 40)
    poly(c, [(x - 34, y), (x + 34, y), (x, y + fl + 60)], '#FF9A3C', LW * .5); poly(c, [(x - 18, y), (x + 18, y), (x, y + fl)], '#FFE26A', 0)
    rect(c, x - 44, y - 300, x + 44, y, '#F4F4F2', LW); poly(c, [(x - 44, y - 300), (x + 44, y - 300), (x, y - 400)], RED, LW)
    poly(c, [(x - 44, y - 90), (x - 90, y), (x - 44, y)], RED, LW * .7); poly(c, [(x + 44, y - 90), (x + 90, y), (x + 44, y)], RED, LW * .7)
    circ(c, x, y - 200, 20, SKY, LW * .5)
    if d.get("text"): label(c, d["text"], x, y - 130, fit_size(d["text"], 30, 70), INK, align='center', rot=-90, skew=0)


def m_earth_spin(c, u, d, t):
    x, y, r = d.get("x", 960), d.get("y", 520), d.get("r", 300) * back(min(1, u * 3), 1.3)
    if r <= 1: return
    circ(c, x, y, r, '#3B7CC8', LW)
    c.save(); p = skia.Path(); p.addCircle(x, y, r); c.clipPath(p, doAntiAlias=True)
    off = (t * 120) % (4 * r)
    for k in range(-2, 3):
        for (dx, dy, w, h) in ((.2, -.3, .5, .3), (1.1, .2, .6, .4), (.6, .5, .3, .2), (1.6, -.4, .4, .25)):
            cx = x - 2 * r + k * 2 * r + dx * r + off
            c.drawOval(skia.Rect(cx - w * r, y + dy * r - h * r, cx + w * r, y + dy * r + h * r), fp('#5FAE5A'))
    c.drawCircle(x + r * .4, y + r * .4, r, fp((0, 0, 30), 60)); c.restore()
    for k in range(d.get("satellites", 4)):
        a = t * (1.1 + k * .25) + k * 1.6; ox, oy = math.cos(a) * r * 1.45, math.sin(a) * r * .5 * (1 if k % 2 else -1)
        if math.sin(a) < 0 and k % 2: continue
        sx, sy = x + ox, y + oy - k * 10
        rect(c, sx - 14, sy - 10, sx + 14, sy + 10, GOLD, LW * .4); rect(c, sx - 50, sy - 6, sx - 16, sy + 6, '#2F4E8A', LW * .3); rect(c, sx + 16, sy - 6, sx + 50, sy + 6, '#2F4E8A', LW * .3)


def m_kart_race(c, u, d, t):
    names = d.get("names") or d.get("text", "A,B,C").split(",")
    lead = d.get("leader", 0); cols = [RED, '#3B6EA8', '#3E9A56', '#F2A13C', '#8A5AB0']
    for i, nm in enumerate(names[:5]):
        y = d.get("y", 760) + i * 110; sp_ = (1.0 if i == lead else .78 - i * .05)
        x = -300 + ease(min(1, u)) * 2300 * sp_ + 6 * math.sin(t * 30 + i)
        rect(c, x - 110, y - 40, x + 110, y + 10, cols[i % 5], LW * .7, r=16)
        circ(c, x - 70, y + 16, 22, '#1C1C22', LW * .4); circ(c, x + 70, y + 16, 22, '#1C1C22', LW * .4)
        circ(c, x + 10, y - 66, 26, '#F4F4F2', LW * .5)
        arts = d.get("logo_art") or []
        art = arts[i] if i < len(arts) else None
        if art:
            circ(c, x - 50, y - 15, 30, '#FFFFFF', LW * .4); brand(c, art, x - 50, y - 15, 44, dark_bg=False)
            label(c, nm.strip().upper(), x + 30, y - 6, fit_size(nm.strip().upper(), 32, 130), '#FFFFFF', align='center', skew=0)
        else:
            label(c, nm.strip().upper(), x, y - 6, fit_size(nm.strip().upper(), 36, 190), '#FFFFFF', align='center', skew=0)
        for k in range(3): c.drawLine(x - 130 - k * 40, y - 20 + k * 12, x - 170 - k * 40, y - 20 + k * 12, ink(4, '#FFFFFF', 140))


def m_podium(c, u, d, t):
    names = d.get("names") or d.get("text", "1,2,3").split(","); x = d.get("x", 960); base = d.get("y", 1000)
    spots = [(0, 300, GOLD, '1'), (-300, 210, '#C9CFD8', '2'), (300, 150, '#D08A4A', '3')]
    for i, (dx, h, colr, num) in enumerate(spots[:len(names)]):
        hh = h * back(K(u, i * .12, .35), 1.4)
        rect(c, x + dx - 140, base - hh, x + dx + 140, base, colr, LW)
        if hh > 60: label(c, num, x + dx, base - hh + 70, 70, INK, align='center', skew=0)
        if K(u, .4 + i * .1, .3) > 0:
            arts = d.get("logo_art") or []
            art = arts[i] if i < len(arts) else None
            nm = names[i].strip().upper(); label(c, nm, x + dx, base - hh - 30, fit_size(nm, 54, 280), INK, align='center', stroke=6, stroke_col='#FFFFFF', skew=0)
            if art:
                sz = 110 * back(K(u, .4 + i * .1, .3), 1.5); circ(c, x + dx, base - hh - 150, sz * .62, '#FFFFFF', LW * .6)
                brand(c, art, x + dx, base - hh - 150, sz * .8, dark_bg=False)


def m_dominoes(c, u, d, t):
    n = d.get("n", 8); x0 = d.get("x", 360); y = d.get("y", 1000); gap = d.get("gap", 150)
    names = d.get("names") or []
    for k in range(n):
        a = min(70, max(0, (u * (n + 2) - k) * 70)); x = x0 + k * gap
        c.save(); c.translate(x, y); c.rotate(a); rect(c, -24, -200, 24, 0, '#F4F4F2' if k % 2 else '#E8E0D0', LW * .7, r=6)
        circ(c, 0, -150, 8, INK, 0); circ(c, 0, -60, 8, INK, 0)
        if k < len(names): label(c, names[k].upper(), 0, -100, fit_size(names[k].upper(), 22, 170), INK, align='center', rot=-90, skew=0)
        c.restore()


def m_signpost(c, u, d, t):
    x, y = d.get("x", 1400), d.get("y", 1000); a, b = (d.get("text", "OLD WAY,NEW WAY").split(",") + ["", ""])[:2]
    line(c, x, y, x, y - 560, 16, '#6A4428')
    flip = ease(K(u, .3, .4)); w = 340 * abs(math.cos(flip * math.pi)); side = 1 if flip < .5 else -1
    txt = a if flip < .5 else b
    p = [(x, y - 520), (x + side * w, y - 520), (x + side * (w + 60 * (w > 30)), y - 470), (x + side * w, y - 420), (x, y - 420)]
    poly(c, p, '#E8D6A8', LW * .8)
    if w > 120: label(c, txt.strip().upper(), x + side * w / 2, y - 455, fit_size(txt.strip().upper(), 44, w - 30), INK, align='center', skew=0)
    poly(c, [(x, y - 400), (x - 300, y - 400), (x - 350, y - 350), (x - 300, y - 300), (x, y - 300)], '#C9B48A', LW * .7)


def _chart(c, u, d, up):
    x0, y0, x1, y1 = d.get("box", [460, 220, 1460, 820])
    rect(c, x0, y0, x1, y1, '#FFFFFF', LW, r=16)
    for k in range(1, 5): c.drawLine(x0 + 20, y0 + k * (y1 - y0) / 5, x1 - 20, y0 + k * (y1 - y0) / 5, ink(2, '#E2DED2'))
    r = random.Random(d.get("seed", 3)); n = 12; pts = []; v = .7 if not up else .2
    for i in range(n):
        v = min(.92, max(.06, v + (.07 if up else -.07) + r.uniform(-.06, .06)))
        if not up and i == n - 3: v = max(.05, v - .25)
        pts.append((x0 + 40 + i * (x1 - x0 - 80) / (n - 1), y1 - 30 - v * (y1 - y0 - 60)))
    m = max(1, int(ease(u) * (n - 1) * 1.0) + 1); fr = ease(u) * (n - 1) - (m - 1)
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:m]: p.lineTo(*q)
    if m < n: q0, q1 = pts[m - 1], pts[m]; tip = (lerp(q0[0], q1[0], fr), lerp(q0[1], q1[1], fr)); p.lineTo(*tip)
    else: tip = pts[-1]
    colr = '#3E9A56' if up else RED; c.drawPath(p, ink(12, colr)); circ(c, tip[0], tip[1], 16, colr, LW * .5)
    if d.get("text") and u > .85: poplabel(c, d["text"], tip[0] - 120, tip[1] - 90 if up else tip[1] + 90, (u - .85) * 6, 90, colr, -6)


def m_chart_up(c, u, d, t): _chart(c, u, d, True)
def m_chart_down(c, u, d, t): _chart(c, u, d, False)


def m_explosion(c, u, d, t):
    x, y, s = d.get("x", 960), d.get("y", 600), d.get("s", 1)
    r = 420 * s * ease_out(min(1, u * 1.6)); a = max(0, 1 - u * .9)
    if r < 2: return
    for (rr, colr) in ((1, '#FF5A2A'), (.72, '#FF9A3C'), (.45, '#FFE26A')):
        pts = []
        for k in range(24):
            ang = k * math.pi / 12; q = r * rr * (1 if k % 2 else .62); pts.append((x + q * math.cos(ang), y + q * math.sin(ang)))
        c.save(); c.translate(0, 0); p = skia.Path.Polygon(pts, True); c.drawPath(p, fp(colr, 255 * a)); c.drawPath(p, ink(LW * .7, INK, 255 * a)); c.restore()
    for (ang, sp_) in DIRS:
        q = r * 1.3 * sp_; rect(c, x + q * math.cos(ang) - 10, y + q * math.sin(ang) - 10 + 400 * u * u, x + q * math.cos(ang) + 10, y + q * math.sin(ang) + 10 + 400 * u * u, '#3A3F4C', 0)


def m_smoke(c, u, d, t):
    x, y = d.get("x", 960), d.get("y", 800)
    for k in range(10):
        ph = (t * .5 + k / 10) % 1; r = 40 + ph * 160
        c.drawCircle(x + 60 * math.sin(k * 2.1 + t) * ph, y - ph * 600, r, fp('#B9BDC6', 200 * (1 - ph) * min(1, u * 3)))


def m_sparks(c, u, d, t):
    x, y = d.get("x", 960), d.get("y", 700)
    for (ang, sp_) in DIRS:
        ph = (t * 1.6 * sp_ + ang) % 1; q = ph * 260 * sp_
        px, py = x + q * math.cos(ang), y + q * math.sin(ang) + 200 * ph * ph
        c.drawLine(px, py, px - 18 * math.cos(ang), py - 18 * math.sin(ang), ink(5, '#FFE26A', 255 * (1 - ph)))


def m_confetti(c, u, d, t):
    for (x, ph, rot, colr) in CONF:
        y = -60 + ((ph + u * 1.3) % 1.2) * 1300
        c.save(); c.translate(x + 30 * math.sin(t * 3 + rot), y); c.rotate(math.degrees(rot + t * 4)); c.drawRect(skia.Rect(-9, -5, 9, 5), fp(colr)); c.restore()


def m_spotlight(c, u, d, t):
    x = d.get("x", 960) + 260 * math.sin(t * 1.4) * (1 - ease(min(1, u * 1.2))); y = d.get("y", 1000)
    c.drawPath(cone_path(x, -120, 160, 640, y + 120), fp('#FFF3C8', 70)); c.drawOval(skia.Rect(x - 320, y - 40, x + 320, y + 40), fp('#FFF3C8', 90))


def m_alarm(c, u, d, t):
    on = (t * 3) % 1 < .5
    c.drawRect(skia.Rect(-900, -700, W + 900, H + 700), fp(RED, 70 if on else 0))
    x, y = d.get("x", 960), d.get("y", 140)
    rect(c, x - 70, y, x + 70, y + 40, '#3A3F4C', LW * .6); p = skia.Path(); p.addArc(skia.Rect(x - 60, y - 60, x + 60, y + 60), 180, 180); p.close()
    shape(c, p, '#FF3A3A' if on else '#9A1F2A', LW * .7)
    if on: add_light(c, x, y - 10, 260, '#FF3A3A', 90)
    if d.get("text"): stamp(c, d["text"], x, y + 280, u / .35, -6, 120, RED)


def m_data_flow(c, u, d, t):
    x0, y0, x1, y1 = d.get("from", [200, 700]) + d.get("to", [1720, 400])
    cx, cy = (x0 + x1) / 2, min(y0, y1) - 200
    p = skia.Path(); p.moveTo(x0, y0); p.quadTo(cx, cy, x1, y1); c.drawPath(p, ink(22, INK)); c.drawPath(p, ink(12, '#3B6EA8'))
    for k in range(10):
        s = (t * .6 + k / 10) % 1
        if s > u * 1.5: continue
        bx = (1 - s) ** 2 * x0 + 2 * (1 - s) * s * cx + s * s * x1; by = (1 - s) ** 2 * y0 + 2 * (1 - s) * s * cy + s * s * y1
        circ(c, bx, by, 12, '#7FE0FF', LW * .3)


def m_car_drive(c, u, d, t):
    y = d.get("y", 960); x = -400 + ease(u) * (W + 800) * d.get("dir", 1) if d.get("dir", 1) > 0 else W + 400 - ease(u) * (W + 800)
    colr = colr_ = d.get("color", '#C8242C')
    rect(c, x - 170, y - 80, x + 170, y, colr, LW, r=20); poly(c, [(x - 100, y - 80), (x - 60, y - 140), (x + 70, y - 140), (x + 110, y - 80)], colr_, LW)
    poly(c, [(x - 80, y - 84), (x - 52, y - 128), (x + 60, y - 128), (x + 90, y - 84)], '#BFE3F2', LW * .5)
    for wx in (-100, 100): circ(c, x + wx, y + 6, 34, '#1C1C22', LW * .5); circ(c, x + wx, y + 6, 12, '#B9BDC6', 0)
    if d.get("text"): label(c, d["text"].upper(), x, y - 26, fit_size(d["text"].upper(), 40, 260), '#FFFFFF', align='center', skew=0)


def m_plane_fly(c, u, d, t):
    x = -300 + ease(u) * (W + 600); y = d.get("y", 260) - 120 * u
    c.save(); c.translate(x, y); c.rotate(-6)
    rect(c, -200, -30, 200, 30, '#F4F4F2', LW, r=30); poly(c, [(-40, 0), (60, 0), (-60, 130)], '#D9DDE4', LW * .7); poly(c, [(-190, -20), (-140, -20), (-200, -100)], '#3B6EA8', LW * .7)
    for k in range(6): c.drawCircle(-90 + k * 44, -6, 8, fp('#3B6EA8'))
    c.restore()
    for k in range(3): c.drawLine(x - 230 - k * 90, y + 10 + k * 9, x - 300 - k * 90, y + 10 + k * 9, ink(10, '#FFFFFF', 160 - k * 40))


def m_ship_sail(c, u, d, t):
    x = -500 + ease(u) * (W + 900); y = d.get("y", 720) + 8 * math.sin(t * 2)
    poly(c, [(x - 300, y - 60), (x + 300, y - 60), (x + 250, y + 30), (x - 260, y + 30)], RED, LW)
    cols = ['#3B6EA8', '#F2A13C', '#3E9A56', '#8A5AB0']
    for j in range(2):
        for i in range(6): rect(c, x - 250 + i * 70, y - 110 - j * 50, x - 186 + i * 70, y - 62 - j * 50, cols[(i + j) % 4], LW * .4)
    rect(c, x + 190, y - 170, x + 270, y - 60, '#F4F4F2', LW * .6)


def m_crowd_cheer(c, u, d, t):
    r = random.Random(4)
    for k in range(26):
        x = -40 + k * 80; h = 30 * abs(math.sin(t * 7 + k)) * min(1, u * 3); sk = r.choice(['#E6BE8E', '#C99F70', '#8A5A3A', '#F1CFA8'])
        y = 1060 - h
        rect(c, x - 34, y - 20, x + 34, y + 120, r.choice(['#3B4660', '#C8242C', '#3E9A56', '#F2A13C']), LW * .5, r=20)
        circ(c, x, y - 50, 32, sk, LW * .5)
        if k % 3 == 0: line(c, x + 30, y - 10, x + 50, y - 110 - h, 12, sk)


def m_lightning(c, u, d, t):
    if u > .5: return
    x = d.get("x", 1200); flash = (u * 10) % 1 < .5
    if flash: c.drawRect(skia.Rect(-900, -700, W + 900, H + 700), fp('#FFFFFF', 120))
    pts = [(x, -100), (x - 60, 200), (x + 30, 220), (x - 80, 520), (x + 10, 540), (x - 90, 860)]
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    c.drawPath(p, ink(26, '#FFE26A')); c.drawPath(p, ink(8, '#FFFFFF'))


def m_planet_zoom(c, u, d, t):
    x, y = d.get("x", 960), d.get("y", 540); r = 40 + ease(u) * d.get("r", 380)
    colr = {"mars": '#C8643A', "moon": '#D9D6CC', "earth": '#3B7CC8', "sun": '#FFC94A', "jupiter": '#D8A878'}.get(d.get("planet", "mars"), '#C8643A')
    circ(c, x, y, r, colr, LW)
    c.save(); p = skia.Path(); p.addCircle(x, y, r); c.clipPath(p, doAntiAlias=True)
    for k in range(5): c.drawOval(skia.Rect(x - r * .9 + k * r * .3, y - r * .5 + k * r * .2, x - r * .5 + k * r * .3, y - r * .3 + k * r * .2), fp(shade(colr, .82)))
    c.drawCircle(x + r * .35, y + r * .35, r, fp((0, 0, 30), 60)); c.restore()
    if d.get("text") and u > .7: label(c, d["text"].upper(), x, y + r + 90, fit_size(d["text"].upper(), 80, 900), '#FFFFFF', align='center', stroke=8)


def m_price_tag(c, u, d, t):
    x, y = d.get("x", 1400), d.get("y", 360); sw = 18 * math.sin(t * 4) * (1 - min(1, u)); s = back(min(1, u * 2.5), 1.6)
    if s <= .01: return
    c.save(); c.translate(x, y); c.rotate(sw - 10); c.scale(s, s)
    line(c, 0, -160, 0, -60, 4); poly(c, [(-170, -60), (170, -60), (170, 90), (-170, 90), (-220, 15)], GOLD, LW)
    circ(c, -170, 15, 14, '#FFFFFF', LW * .5); txt = d.get("text", "$99"); label(c, txt, 10, 45, fit_size(txt, 96, 300), INK, align='center', skew=0)
    c.restore()


def m_door_slam(c, u, d, t):
    x, y = d.get("x", 960), d.get("y", 1000); a = 1 - ease_out(min(1, u * 2.2)); w = 320 * (1 - .9 * a)
    rect(c, x - 180, y - 560, x + 180, y, '#3A3F4C', LW); rect(c, x - 160, y - 540, x - 160 + w, y, '#8E5C36', LW)
    circ(c, x - 160 + w - 40, y - 280, 12, GOLD, LW * .4)
    if d.get("text") and u > .45: _txt = d["text"].upper(); rect(c, x - 140, y - 420, x + 120, y - 340, '#FFFFFF', LW * .6); label(c, _txt, x - 10, y - 365, fit_size(_txt, 44, 240), RED, align='center', skew=0)


def m_logo_pop(c, u, d, t):
    """A company's real mark pops in big (its name under it); the move for 'Nvidia', 'Tesla', 'OpenAI'..."""
    x, y, sz = d.get("x", 960), d.get("y", 470), d.get("size", 360) * back(min(1, u * 2.5), 1.6)
    if sz <= 1: return
    art = d.get("logo_art"); name = (d.get("text") or (art or {}).get("title") or d.get("logo") or "").upper()
    circ(c, x, y, sz * .66, '#FFFFFF', LW); 
    if not brand(c, art, x, y, sz * .82, dark_bg=False):
        label(c, name, x, y + sz * .12, fit_size(name, sz * .3, sz * 1.1), INK, align='center', skew=0)
    elif name and u > .3:
        label(c, name, x, y + sz * .66 + 90, fit_size(name, 80, 900), '#FFFFFF', align='center', stroke=8, skew=0)


MOVES = {k[2:]: v for k, v in dict(globals()).items() if k.startswith("m_") and callable(v)}
LENGTH = dict(money_rain=3.0, rocket_launch=2.6, cash_pile=1.4, kart_race=2.8, podium=1.4, dominoes=1.8, signpost=1.2,
              chart_up=1.6, chart_down=1.6, explosion=1.1, alarm=1.0, plane_fly=2.4, ship_sail=4.0, car_drive=1.8,
              planet_zoom=1.6, logo_pop=1.0, door_slam=.8, lightning=.8, data_flow=1.2, price_tag=1.0, earth_spin=1.0)
DAY_SETS = {"factory", "lab", "openoffice", "exchange", "court", "parliament", "hospital", "classroom", "press", "prison",
            "market", "airport", "port", "highway", "station", "farm", "forest", "ocean", "desert", "mountains", "kitchen", "hq",
            "church", "mosque", "village"}
HEAVY = {"explosion", "door_slam", "lightning", "rocket_launch"}     # get a camera shake on their word


def register(shots_module) -> None:
    from golide_engine.stickman import rm_roles
    rm_roles.install(shots_module)              # characters dressed for their role
    Shot = shots_module.Shot
    init = Shot.__init__

    def __init__(self, sh, tl, cast, env):
        if "time" not in sh["spec"] and sh["spec"].get("set") in DAY_SETS:
            sh["spec"]["time"] = "day"        # the kit's default is night; outdoor and bright places read as day
        cam = sh["spec"].get("cam")
        if isinstance(cam, str):
            sh["spec"]["cam"] = dict(CAM.get(cam, {}))
        init(self, sh, tl, cast, env)
        if cam == "shake":
            self.shakes.append(self.t0 + .1)
        self.moves = []
        for m in self.spec.get("moves", []):
            if m.get("do") not in MOVES:
                continue
            tt = self.cue(m.get("at"), .1)
            self.moves.append((m, tt))
            if m["do"] in HEAVY:
                self.shakes.append(tt + (.5 if m["do"] == "rocket_launch" else 0)); self.events.append(("thud", tt))
            else:
                self.events.append(("pop", tt))

    def with_moves(world):
        def run(self, c, t):
            depth = getattr(self, "_mv_depth", 0); self._mv_depth = depth + 1
            try:
                world(self, c, t)          # a kind that calls super().world() must not draw the moves twice
            finally:
                self._mv_depth = depth
            if depth:
                return
            for m, tt in getattr(self, "moves", []):
                if t >= tt:
                    MOVES[m["do"]](c, (t - tt) / LENGTH.get(m["do"], 1.4), m, t)
        return run

    Shot.__init__ = __init__
    for cls in {Shot, *shots_module.KINDS.values()}:      # every kind, including the ones with their own world()
        if "world" in cls.__dict__:
            cls.world = with_moves(cls.__dict__["world"])
