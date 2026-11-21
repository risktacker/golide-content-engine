"""More things ReachMora can draw (owner 2026-11-21: "some of the stuff was lacking because we didn't have the visual
list"). Drawn in the kit's own ink style with the kit's own helpers (imported from vendor/reachmora/engine, never
copied). They are added to the kit's ICONS when it loads (stickman/rm_hook/sitecustomize.py), in every worker.

Each icon draws centred at 0,0, about 500 units across, like the kit's own (a prop is ~300 px wide at s=1).
"""
from __future__ import annotations

import math

# the kit's helpers, from the kit itself (this module only runs inside the kit's process)
import skia  # noqa: F401
from engine.kit import INK, LW, MARKER, circ, fit_size, fp, ink, label, line, oval, poly, rect, shape  # noqa: F401
from engine.props import bills, textlines

DARK, METAL, SCREEN, GOLD, RED, GREEN = "#454857", "#A0A4B0", "#7FD0FF", "#F2C14E", "#C8242C", "#6FA36A"
BLUE, CREAM, WHITE, BROWN, SKY = "#4C7DBF", "#F4EFE2", "#FFFFFF", "#6A4428", "#BFE3F2"


def _text(c, o, y=220, size=64, w=480):
    if o.get("text"):
        label(c, o["text"], 0, y, fit_size(o["text"], size, w), CREAM, align="center", stroke=12)


# ---------------------------------------------------------------- tech
def ic_chip(c, t, o):
    for i in range(6):
        for s in (-1, 1):
            line(c, -150 + i * 60, s * 150, -150 + i * 60, s * 205, LW * 1.6, METAL)
            line(c, s * 150, -150 + i * 60, s * 205, -150 + i * 60, LW * 1.6, METAL)
    rect(c, -160, -160, 160, 160, DARK, LW, r=18); rect(c, -95, -95, 95, 95, "#3A3A48", LW * .7, r=8)
    label(c, o.get("text", "AI"), 0, 24, fit_size(o.get("text", "AI"), 80, 160), GOLD, align="center", skew=0)


def ic_gpu(c, t, o):
    rect(c, -250, -110, 250, 110, DARK, LW, r=14)
    for x in (-125, 125):
        circ(c, x, 0, 82, "#3A3A48", LW * .8)
        for k in range(7):
            a = math.radians(k * 360 / 7 + t * 300)
            line(c, x, 0, x + 70 * math.cos(a), 70 * math.sin(a), LW * 1.2, METAL)
        circ(c, x, 0, 18, METAL, LW * .6)
    rect(c, -200, 110, 120, 140, GOLD, LW * .7)
    _text(c, o)


def ic_server(c, t, o):
    rect(c, -150, -230, 150, 230, DARK, LW, r=12)
    for i in range(5):
        y = -200 + i * 88
        rect(c, -125, y, 125, y + 66, "#3A3A48", LW * .6, r=6)
        on = (int(t * 4) + i) % 3 != 0
        circ(c, 95, y + 33, 10, "#5BE08A" if on else "#2E5A3C", LW * .4)
        textlines(c, -105, y + 22, 40, 2, gap=20, v=METAL, w=5)


def ic_datacenter(c, t, o):
    for k, x in enumerate((-180, 0, 180)):
        c.save(); c.translate(x, 10 * (k % 2)); c.scale(.55, .55); ic_server(c, t + k * .3, {}); c.restore()
    line(c, -260, 150, 260, 150, LW, INK)
    _text(c, o)


def ic_robot(c, t, o):
    line(c, 0, -230, 0, -180, LW, INK); circ(c, 0, -240, 16, RED, LW * .6)
    rect(c, -130, -180, 130, -20, METAL, LW, r=30)
    for x in (-55, 55):
        circ(c, x, -100, 30, WHITE, LW * .7); circ(c, x + 4 * math.sin(t * 3), -100, 13, DARK, 0)
    rect(c, -60, -60, 60, -45, DARK, 0, r=6)
    rect(c, -150, 0, 150, 200, "#C9CCD6", LW, r=24); rect(c, -60, 50, 60, 130, SCREEN, LW * .6, r=10)


def ic_cloud(c, t, o):
    parts = []
    for x, y, r in ((-120, 30, 90), (0, -40, 120), (130, 30, 90)):
        q = skia.Path(); q.addCircle(x, y, r); parts.append(q)
    q = skia.Path(); q.addRect(skia.Rect(-120, 30, 130, 120)); parts.append(q)
    p = parts[0]
    for q in parts[1:]:
        p = skia.Op(p, q, skia.PathOp.kUnion_PathOp)
    shape(c, p, CREAM, LW)
    _text(c, o)


def ic_wifi(c, t, o):
    for i, r in enumerate((60, 140, 220)):
        a = 255 if (int(t * 3) % 4) > i else 90
        p = skia.Path(); p.addArc(skia.Rect(-r, -r + 120, r, r + 120), -140, 100)
        c.drawPath(p, ink(LW * 3.2, BLUE, a))
    circ(c, 0, 120, 24, BLUE, LW * .6)


def ic_satellite(c, t, o):
    c.save(); c.rotate(-25 + 4 * math.sin(t))
    for s in (-1, 1):
        rect(c, s * 90, -60, s * 250, 60, "#2F4E8A", LW)
        for k in range(3):
            line(c, s * (90 + 53 * (k + 1)), -60, s * (90 + 53 * (k + 1)), 60, LW * .5, SKY)
    rect(c, -80, -80, 80, 80, GOLD, LW, r=10); circ(c, 0, -110, 36, METAL, LW * .7)
    c.restore()


def ic_earth(c, t, o):
    circ(c, 0, 0, 210, "#3B7DD8", LW)
    c.save(); p = skia.Path(); p.addCircle(0, 0, 205); c.clipPath(p, doAntiAlias=True)
    sh = (t * 40) % 420
    for dx in (-420, 0):
        for pts in (((-150, -110), (-40, -150), (0, -60), (-90, 20), (-170, -20)),
                    ((40, 20), (150, -10), (200, 90), (100, 160), (30, 110)),
                    ((-120, 110), (-40, 90), (-30, 170), (-110, 190))):
            poly(c, [(x + sh + dx, y) for x, y in pts], "#5DAE5B", LW * .6)
    c.restore()


def ic_moon(c, t, o):
    circ(c, 0, 0, 190, "#D9D6CC", LW)
    for x, y, r in ((-60, -50, 40), (70, 20, 30), (-10, 90, 25), (90, -90, 18)):
        circ(c, x, y, r, "#BDB9AE", LW * .5)


def ic_sun(c, t, o):
    c.save(); c.rotate(t * 20)
    for k in range(12):
        a = math.radians(k * 30)
        poly(c, [(150 * math.cos(a - .12), 150 * math.sin(a - .12)), (240 * math.cos(a), 240 * math.sin(a)),
                 (150 * math.cos(a + .12), 150 * math.sin(a + .12))], "#F7B733", LW * .6)
    c.restore(); circ(c, 0, 0, 140, GOLD, LW)


def ic_rocket(c, t, o):
    for k in range(3):
        f = 60 + 30 * math.sin(t * 20 + k)
        poly(c, [(-35 + k * 35 - 20, 170), (-35 + k * 35, 170 + f), (-35 + k * 35 + 20, 170)], "#F7B733" if k != 1 else RED, LW * .5)
    p = skia.Path(); p.moveTo(0, -240); p.cubicTo(90, -170, 90, 0, 70, 170); p.lineTo(-70, 170); p.cubicTo(-90, 0, -90, -170, 0, -240); p.close()
    shape(c, p, CREAM, LW)
    for s in (-1, 1):
        poly(c, [(s * 70, 60), (s * 150, 180), (s * 70, 170)], RED, LW)
    circ(c, 0, -60, 40, SKY, LW * .8)


def ic_drone(c, t, o):
    for x in (-180, 180):
        line(c, x * .4, 0, x, -40, LW * 1.4, DARK)
        oval(c, x - 80, -60, x + 80, -40, METAL, LW * .5)
    rect(c, -90, -30, 90, 50, DARK, LW, r=20); circ(c, 0, 60, 26, "#3A3A48", LW * .6)


def ic_battery(c, t, o):
    lvl = float(o.get("level", .75))
    rect(c, -120, -200, 120, 220, DARK, LW, r=24); rect(c, -50, -235, 50, -200, METAL, LW)
    top = 200 - 380 * lvl
    rect(c, -95, top, 95, 195, "#5BE08A" if lvl > .3 else RED, LW * .5, r=12)
    poly(c, [(20, -120), (-40, 10), (5, 10), (-20, 120), (50, -20), (5, -20)], GOLD, LW * .6)


def ic_plug(c, t, o):
    rect(c, -90, -90, 90, 110, "#E8E2D6", LW, r=28)
    for x in (-40, 40):
        rect(c, x - 14, -200, x + 14, -90, METAL, LW * .7)
    line(c, 0, 110, 0, 230, LW * 2.4, DARK)


def ic_solar(c, t, o):
    poly(c, [(-230, 60), (-140, -160), (230, -160), (150, 60)], "#2F4E8A", LW)
    for k in range(1, 4):
        line(c, -230 + 95 * k, 60, -140 + 92 * k, -160, LW * .5, SKY)
    line(c, -186, -50, 190, -50, LW * .5, SKY)
    line(c, 0, 60, 0, 200, LW * 1.6, METAL)


def ic_wind(c, t, o):
    line(c, 0, -60, -15, 230, LW * 2, "#E8E2D6"); line(c, 0, -60, 15, 230, LW * 2, "#E8E2D6")
    c.save(); c.translate(0, -60); c.rotate(t * 120)
    for k in range(3):
        c.save(); c.rotate(k * 120); poly(c, [(0, -8), (190, -18), (200, 0), (0, 10)], CREAM, LW * .6); c.restore()
    c.restore(); circ(c, 0, -60, 20, METAL, LW * .6)


def ic_camera(c, t, o):
    rect(c, -220, -110, 220, 150, DARK, LW, r=24); rect(c, -90, -160, 40, -110, DARK, LW, r=10)
    circ(c, 0, 20, 100, "#3A3A48", LW); circ(c, 0, 20, 62, "#1A2A44", LW * .6); circ(c, -20, 0, 16, WHITE, 0)
    circ(c, 160, -60, 16, RED, LW * .4)


def ic_headphones(c, t, o):
    p = skia.Path(); p.addArc(skia.Rect(-190, -190, 190, 190), 180, 180); c.drawPath(p, ink(LW * 4, METAL))
    for s in (-1, 1):
        rect(c, s * 190 - 50, -20, s * 190 + 50, 140, RED, LW, r=30)


def ic_vr(c, t, o):
    rect(c, -230, -90, 230, 90, DARK, LW, r=50)
    for x in (-110, 110):
        oval(c, x - 80, -50, x + 80, 50, "#3A3A48", LW * .6)
    line(c, -230, 0, -280, -40, LW * 2, DARK); line(c, 230, 0, 280, -40, LW * 2, DARK)


def ic_code(c, t, o):
    rect(c, -240, -170, 240, 170, "#1E2230", LW, r=16)
    label(c, "</>", 0, 40, 150, GOLD, align="center", skew=0)


def ic_bug(c, t, o):
    for s in (-1, 1):
        for k in range(3):
            line(c, s * 60, -40 + k * 60, s * 170, -80 + k * 80, LW * 1.2, INK)
    oval(c, -90, -120, 90, 170, RED, LW); circ(c, 0, -150, 55, DARK, LW)
    line(c, 0, -110, 0, 160, LW * .8, INK)


def ic_shield(c, t, o):
    p = skia.Path(); p.moveTo(0, -230); p.lineTo(190, -160); p.cubicTo(190, 40, 110, 160, 0, 230); p.cubicTo(-110, 160, -190, 40, -190, -160); p.close()
    shape(c, p, BLUE, LW)
    c.drawPath(_tick(-70, 0, 1.0), ink(LW * 3.4, WHITE))


def _tick(x, y, s):
    p = skia.Path(); p.moveTo(x, y); p.lineTo(x + 50 * s, y + 55 * s); p.lineTo(x + 150 * s, y - 70 * s)
    return p


def ic_key(c, t, o):
    circ(c, -120, 0, 95, GOLD, LW); circ(c, -120, 0, 38, "#00000000" if False else "#B8862A", LW * .6)
    rect(c, -30, -24, 230, 24, GOLD, LW)
    for x in (150, 200):
        rect(c, x - 16, 24, x + 16, 80, GOLD, LW * .8)


def ic_ai(c, t, o):
    for k, (x, y, r) in enumerate(((0, 0, 1.0), (150, -130, .45), (-150, 120, .35))):
        s = 150 * r * (1 + .08 * math.sin(t * 5 + k))
        p = skia.Path(); p.moveTo(x, y - s); p.quadTo(x, y, x + s, y); p.quadTo(x, y, x, y + s); p.quadTo(x, y, x - s, y); p.quadTo(x, y, x, y - s); p.close()
        shape(c, p, GOLD if k == 0 else SKY, LW * .8)
    _text(c, o)


# ---------------------------------------------------------------- money and business
def ic_bank(c, t, o):
    poly(c, [(-240, -100), (0, -230), (240, -100)], CREAM, LW)
    rect(c, -230, -100, 230, -60, CREAM, LW)
    for x in (-170, -85, 0, 85, 170):
        rect(c, x - 24, -60, x + 24, 150, CREAM, LW * .8)
    rect(c, -250, 150, 250, 200, CREAM, LW)
    label(c, "$", 0, -120, 70, "#8E8878", align="center", skew=0)


def ic_credit_card(c, t, o):
    rect(c, -240, -150, 240, 150, BLUE, LW, r=26); rect(c, -240, -90, 240, -40, DARK, 0)
    rect(c, -190, 0, -110, 60, GOLD, LW * .6, r=8); textlines(c, -190, 110, 200, 1, v=CREAM, w=10)


def ic_wallet(c, t, o):
    c.save(); c.translate(0, -40); bills(c, 0, -60, -4, 2); c.restore()
    rect(c, -230, -90, 230, 170, BROWN, LW, r=30); rect(c, 80, -10, 250, 90, "#8A5A36", LW, r=20); circ(c, 140, 40, 16, GOLD, LW * .5)


def ic_bitcoin(c, t, o):
    circ(c, 0, 0, 200, "#F7931A", LW); label(c, "B", 0, 80, 230, WHITE, align="center", skew=0)
    for x in (-25, 25):                       # the two bars through the B (the font has no bitcoin sign)
        line(c, x, -135, x, -95, LW * 1.6, WHITE); line(c, x, 95, x, 135, LW * 1.6, WHITE)


def ic_gold(c, t, o):
    for k, (x, y) in enumerate(((-120, 60), (120, 60), (0, -60))):
        poly(c, [(x - 130, y + 60), (x - 90, y - 40), (x + 90, y - 40), (x + 130, y + 60)], GOLD, LW)
        line(c, x - 70, y - 10, x + 30, y - 10, LW * .6, "#FFF2B8")


def ic_briefcase(c, t, o):
    rect(c, -80, -190, 80, -120, BROWN, LW, r=20); rect(c, -50, -170, 50, -125, "#00000000" if False else "#3E2A1A", 0)
    rect(c, -230, -120, 230, 170, BROWN, LW, r=24); rect(c, -230, -20, 230, 10, "#5A3A22", 0); rect(c, -30, -40, 30, 30, GOLD, LW * .6, r=6)


def ic_handshake(c, t, o):
    for s, col in ((-1, BLUE), (1, "#E6BE8E")):
        rect(c, s * 250 - 70, -60, s * 250 + 70, 60, col, LW, r=20)
    p = skia.Path(); p.addRoundRect(skia.Rect(-150, -70, 150, 70), 60, 60); shape(c, p, "#E6BE8E", LW)
    for k in range(4):
        line(c, -90 + k * 60, -40, -70 + k * 60, 40, LW * .6, INK)


def ic_factory(c, t, o):
    poly(c, [(-250, 180), (-250, -20), (-140, -100), (-140, -20), (-30, -100), (-30, -20), (80, -100), (80, -20), (250, -20), (250, 180)], "#C9B08A", LW)
    rect(c, 140, -230, 200, -20, "#8E8878", LW)
    for k in range(3):
        circ(c, 170 + 20 * math.sin(t * 2 + k), -260 - k * 55 - (t * 30 % 40), 30 + k * 8, "#D9D6CC", LW * .4)
    for x in (-200, -90, 20):
        rect(c, x, 60, x + 60, 120, SKY, LW * .6)


def ic_store(c, t, o):
    rect(c, -230, -40, 230, 190, CREAM, LW)
    for k in range(6):
        poly(c, [(-240 + k * 80, -40), (-240 + k * 80, -130), (-160 + k * 80, -130), (-160 + k * 80, -40)], RED if k % 2 else WHITE, LW * .6)
    rect(c, -60, 60, 60, 190, BROWN, LW); rect(c, -200, 30, -100, 130, SKY, LW * .6); rect(c, 100, 30, 200, 130, SKY, LW * .6)


def ic_truck(c, t, o):
    rect(c, -250, -140, 80, 90, CREAM, LW, r=10)
    poly(c, [(80, -60), (190, -60), (250, 10), (250, 90), (80, 90)], RED, LW); rect(c, 110, -40, 180, 10, SKY, LW * .6)
    for x in (-170, -60, 170):
        circ(c, x, 100, 45, DARK, LW); circ(c, x, 100, 16, METAL, LW * .5)


def ic_ship(c, t, o):
    poly(c, [(-260, 40), (260, 40), (200, 160), (-200, 160)], RED, LW)
    for k, col in enumerate((BLUE, GOLD, GREEN, BLUE)):
        rect(c, -200 + k * 90, -40, -120 + k * 90, 40, col, LW * .7)
    rect(c, 160, -130, 230, 40, CREAM, LW)
    p = skia.Path(); p.moveTo(-280, 180)
    for k in range(8):
        p.quadTo(-245 + k * 70, 160 + 10 * math.sin(t * 3 + k), -210 + k * 70, 180)
    c.drawPath(p, ink(LW * 1.4, BLUE))


def ic_plane(c, t, o):
    c.save(); c.rotate(-15)
    rect(c, -250, -40, 230, 40, CREAM, LW, r=40)
    poly(c, [(-40, 0), (60, 0), (-60, 200), (-120, 200)], METAL, LW); poly(c, [(-40, 0), (60, 0), (-60, -200), (-120, -200)], METAL, LW)
    poly(c, [(-250, 0), (-200, 0), (-240, -120), (-270, -120)], BLUE, LW)
    for k in range(5):
        circ(c, 60 + k * 35, -10, 10, SKY, LW * .3)
    c.restore()


def ic_train(c, t, o):
    rect(c, -240, -170, 200, 110, BLUE, LW, r=40); poly(c, [(200, -170), (260, 20), (260, 110), (200, 110)], BLUE, LW)
    for x in (-190, -90, 10, 110):
        rect(c, x, -120, x + 70, -40, SKY, LW * .6)
    rect(c, -240, 30, 260, 60, GOLD, 0)
    for x in (-170, -60, 50, 160):
        circ(c, x, 135, 32, DARK, LW * .8)
    line(c, -280, 170, 290, 170, LW * 1.4, METAL)


def ic_oil(c, t, o):
    rect(c, -130, -190, 130, 190, "#2E3B4E", LW, r=18)
    for y in (-110, 0, 110):
        rect(c, -140, y - 12, 140, y + 12, "#22303F", LW * .6)
    label(c, "OIL", 0, 30, 70, GOLD, align="center", skew=0)


def ic_crown(c, t, o):
    poly(c, [(-210, 120), (-230, -110), (-110, 0), (0, -170), (110, 0), (230, -110), (210, 120)], GOLD, LW)
    for x, y in ((-230, -110), (0, -170), (230, -110)):
        circ(c, x, y, 22, RED, LW * .5)


def ic_flag(c, t, o):
    line(c, -190, -230, -190, 230, LW * 2, METAL)
    p = skia.Path(); p.moveTo(-190, -220)
    for k in range(5):
        p.lineTo(-190 + k * 95, -220 + 18 * math.sin(t * 4 + k))
    for k in range(4, -1, -1):
        p.lineTo(-190 + k * 95, -40 + 18 * math.sin(t * 4 + k))
    p.close(); shape(c, p, o.get("color", RED), LW)


def ic_tower(c, t, o):
    rect(c, -110, -240, 110, 230, "#5A6B88", LW)
    for r in range(9):
        for k in range(3):
            on = (r * 3 + k) % 4 != 1
            rect(c, -80 + k * 60, -210 + r * 48, -50 + k * 60, -180 + r * 48, GOLD if on else "#3A4A64", 0)
    if o.get("text"):
        rect(c, -100, -280, 100, -240, DARK, LW * .6, r=8); label(c, o["text"], 0, -248, fit_size(o["text"], 30, 180), WHITE, align="center", skew=0)


# ---------------------------------------------------------------- institutions and people
def ic_gavel(c, t, o):
    c.save(); c.rotate(-35 + 10 * max(0, math.sin(t * 6)))
    rect(c, -40, -40, 230, 0, BROWN, LW); rect(c, -150, -110, -20, 60, "#8A5A36", LW, r=16)
    c.restore(); rect(c, -230, 140, 30, 190, "#8A5A36", LW, r=10)


def ic_scale(c, t, o):
    line(c, 0, -210, 0, 190, LW * 1.6, GOLD); rect(c, -110, 180, 110, 210, GOLD, LW)
    a = 10 * math.sin(t * 2)
    c.save(); c.rotate(a); line(c, -200, -170, 200, -170, LW * 1.6, GOLD)
    for s in (-1, 1):
        line(c, s * 200, -170, s * 150, -40, LW * .6, GOLD); line(c, s * 200, -170, s * 250, -40, LW * .6, GOLD)
        p = skia.Path(); p.addArc(skia.Rect(s * 200 - 70, -90, s * 200 + 70, 10), 0, 180); p.close(); shape(c, p, GOLD, LW * .8)
    c.restore()


def ic_document(c, t, o):
    poly(c, [(-170, -220), (100, -220), (170, -150), (170, 220), (-170, 220)], CREAM, LW)
    textlines(c, -120, -140, 120, 8, gap=38)
    label(c, "~", 70, 190, 90, BLUE, align="center", skew=0)


def ic_newspaper(c, t, o):
    rect(c, -230, -170, 230, 170, CREAM, LW)
    label(c, o.get("text", "NEWS"), 0, -100, fit_size(o.get("text", "NEWS"), 64, 400), INK, align="center", skew=0)
    rect(c, -200, -70, -20, 50, "#D9D2C0", LW * .5); textlines(c, 10, -60, 200, 4, gap=32); textlines(c, -200, 90, 200, 2, gap=32)


def ic_megaphone(c, t, o):
    poly(c, [(-180, -50), (140, -170), (140, 170), (-180, 50)], RED, LW); rect(c, -230, -60, -170, 60, DARK, LW, r=10)
    rect(c, -150, 50, -90, 150, DARK, LW, r=8)
    for k in range(3):
        a = 255 if int(t * 4) % 3 >= k else 60
        p = skia.Path(); p.addArc(skia.Rect(150 - 40 - k * 40, -60 - k * 40, 150 + 40 + k * 40, 60 + k * 40), -40, 80)
        c.drawPath(p, ink(LW * 1.2, INK, a))


def ic_mail(c, t, o):
    rect(c, -230, -150, 230, 150, CREAM, LW, r=10)
    poly(c, [(-230, -150), (0, 30), (230, -150)], "#E8E2D6", LW * .8)


def ic_hospital(c, t, o):
    rect(c, -220, -150, 220, 190, CREAM, LW)
    rect(c, -40, -230, 40, -70, RED, LW * .6); rect(c, -100, -170, 100, -110, RED, LW * .6)
    for x in (-180, -90, 50, 140):
        rect(c, x, -40, x + 50, 20, SKY, LW * .5); rect(c, x, 70, x + 50, 130, SKY, LW * .5)
    rect(c, -40, 90, 40, 190, BROWN, LW * .7)


def ic_pill(c, t, o):
    c.save(); c.rotate(-35)
    p = skia.Path(); p.addRoundRect(skia.Rect(-220, -80, 0, 80), 80, 80); shape(c, p, RED, LW)
    p = skia.Path(); p.addRoundRect(skia.Rect(0, -80, 220, 80), 80, 80); shape(c, p, CREAM, LW)
    c.restore()


def ic_syringe(c, t, o):
    c.save(); c.rotate(-40)
    rect(c, -160, -45, 120, 45, SKY, LW); rect(c, -40, -45, 120, 45, "#7FB3E0", 0)
    rect(c, -230, -10, -160, 10, METAL, LW * .6); rect(c, -250, -50, -230, 50, DARK, LW * .6)
    rect(c, 120, -6, 250, 6, METAL, LW * .5)
    c.restore()


def ic_dna(c, t, o):
    for k in range(13):
        y = -230 + k * 38
        x = 110 * math.sin(k * .55 + t * 2)
        line(c, -x, y, x, y, LW * .7, METAL)
        circ(c, x, y, 16, BLUE, LW * .4); circ(c, -x, y, 16, RED, LW * .4)


def ic_microscope(c, t, o):
    rect(c, -170, 170, 170, 210, DARK, LW, r=10); line(c, 80, 170, 80, -20, LW * 2.2, DARK)
    c.save(); c.rotate(25); rect(c, -40, -230, 40, 0, METAL, LW, r=14); c.restore()
    rect(c, -60, 40, 140, 70, DARK, LW, r=6)


def ic_gradcap(c, t, o):
    poly(c, [(-250, -40), (0, -150), (250, -40), (0, 70)], DARK, LW)
    p = skia.Path(); p.moveTo(-150, 0); p.lineTo(-150, 110); p.cubicTo(-80, 170, 80, 170, 150, 110); p.lineTo(150, 0); shape(c, p, DARK, LW)
    line(c, 0, -40, 200, 40, LW * .6, GOLD); line(c, 200, 40, 200, 150, LW * .8, GOLD); circ(c, 200, 160, 16, GOLD, LW * .4)


def ic_people(c, t, o):
    for x, s, col in ((-150, .8, BLUE), (150, .8, GREEN), (0, 1.0, RED)):
        circ(c, x, -90 * s - 40, 60 * s, "#E6BE8E", LW)
        p = skia.Path(); p.addRoundRect(skia.Rect(x - 100 * s, -20 * s, x + 100 * s, 180), 70 * s, 70 * s); shape(c, p, col, LW)


def ic_podium(c, t, o):
    poly(c, [(-160, -40), (160, -40), (120, 200), (-120, 200)], BROWN, LW)
    rect(c, -200, -80, 200, -40, "#8A5A36", LW, r=8)
    for x in (-50, 50):
        line(c, x, -80, x * 1.6, -190, LW * .9, DARK); circ(c, x * 1.6, -200, 18, DARK, LW * .4)
    circ(c, 0, 60, 46, GOLD, LW * .6)


# ---------------------------------------------------------------- life, nature, effects
def ic_fire(c, t, o):
    for s, col in ((1.0, "#E8462F"), (.68, "#F7B733"), (.38, "#FFF0A8")):
        f = 1 + .06 * math.sin(t * 9 + s * 4)
        p = skia.Path(); p.moveTo(0, 200 * s); p.cubicTo(-200 * s, 160 * s, -170 * s, -60 * s, 0, -230 * s * f)
        p.cubicTo(30 * s, -90 * s, 190 * s, -40 * s, 140 * s, 120 * s); p.cubicTo(110 * s, 180 * s, 60 * s, 200 * s, 0, 200 * s); p.close()
        shape(c, p, col, LW * (s if s < 1 else 1))


def ic_lightning(c, t, o):
    poly(c, [(40, -240), (-150, 30), (-20, 30), (-60, 240), (150, -40), (20, -40)], GOLD, LW)


def ic_explosion(c, t, o):
    for r, col in ((230, "#E8462F"), (160, "#F7B733"), (90, "#FFF0A8")):
        pts = []
        for k in range(16):
            a = math.radians(k * 22.5)
            rr = r * (1 if k % 2 else .62) * (1 + .05 * math.sin(t * 12 + k))
            pts.append((rr * math.cos(a), rr * math.sin(a)))
        poly(c, pts, col, LW * .8)


def ic_water(c, t, o):
    p = skia.Path(); p.moveTo(0, -220); p.cubicTo(60, -100, 170, 0, 170, 80); p.cubicTo(170, 180, 90, 230, 0, 230)
    p.cubicTo(-90, 230, -170, 180, -170, 80); p.cubicTo(-170, 0, -60, -100, 0, -220); p.close(); shape(c, p, "#4FA3E8", LW)
    circ(c, -70, 80, 22, WHITE, 0)


def ic_tree(c, t, o):
    rect(c, -30, 40, 30, 220, BROWN, LW)
    for x, y, r in ((0, -100, 150), (-110, -10, 100), (110, -10, 100)):
        circ(c, x, y, r, "#4F9A4C", LW)


def ic_mountain(c, t, o):
    poly(c, [(-260, 180), (-60, -170), (60, 0), (130, -90), (260, 180)], "#7A8AA6", LW)
    poly(c, [(-60, -170), (-120, -70), (-80, -90), (-40, -60), (-10, -100)], WHITE, LW * .5)


def ic_food(c, t, o):
    p = skia.Path(); p.addArc(skia.Rect(-220, -200, 220, 40), 180, 180); p.close(); shape(c, p, "#E0A04A", LW)
    rect(c, -230, -10, 230, 30, GREEN, LW * .7, r=10); rect(c, -220, 30, 220, 80, "#7A3B1E", LW, r=16)
    rect(c, -230, 80, 230, 110, GOLD, LW * .6, r=8); rect(c, -220, 110, 220, 170, "#E0A04A", LW, r=30)


def ic_coffee(c, t, o):
    for k in range(3):
        a = int(110 + 60 * math.sin(t * 3 + k))
        line(c, -60 + k * 60, -150 - 20 * math.sin(t * 2 + k), -50 + k * 60, -230, LW * 1.4, (235, 235, 235))
    rect(c, -140, -110, 120, 180, CREAM, LW, r=26)
    p = skia.Path(); p.addArc(skia.Rect(80, -60, 220, 100), -90, 180); c.drawPath(p, ink(LW * 3, CREAM)); c.drawPath(p, ink(LW, INK))


def ic_gamepad(c, t, o):
    p = skia.Path(); p.addRoundRect(skia.Rect(-240, -110, 240, 120), 110, 110); shape(c, p, DARK, LW)
    rect(c, -170, -20, -70, 20, "#5A5A6A", 0); rect(c, -140, -50, -100, 50, "#5A5A6A", 0)
    for x, y, col in ((120, -40, RED), (170, 0, BLUE), (120, 40, GREEN), (70, 0, GOLD)):
        circ(c, x, y, 20, col, LW * .4)


def ic_play(c, t, o):
    rect(c, -240, -170, 240, 170, RED, LW, r=50); poly(c, [(-50, -80), (90, 0), (-50, 80)], WHITE, LW * .6)


def ic_music(c, t, o):
    line(c, -50, 125, -50, -190, LW * 1.4, INK); line(c, 150, 85, 150, -230, LW * 1.4, INK)
    poly(c, [(-50, -190), (150, -230), (150, -170), (-50, -130)], INK, LW * .6)
    oval(c, -160, 90, -40, 165, INK, LW * .6); oval(c, 40, 50, 160, 125, INK, LW * .6)


def ic_ticket(c, t, o):
    rect(c, -230, -110, 230, 110, GOLD, LW, r=16)
    for s in (-1, 1):
        circ(c, s * 230, 0, 40, "#1A1D26", 0)
    for k in range(6):
        line(c, 110, -90 + k * 34, 110, -70 + k * 34, LW * .6, INK)
    label(c, o.get("text", "TICKET"), -50, 22, fit_size(o.get("text", "TICKET"), 56, 280), INK, align="center", skew=0)


def ic_thumbs_up(c, t, o):
    rect(c, -200, -40, -110, 190, BLUE, LW, r=14)
    p = skia.Path(); p.moveTo(-110, -30); p.lineTo(-30, -60); p.lineTo(20, -230); p.cubicTo(80, -230, 90, -160, 70, -70)
    p.lineTo(190, -70); p.cubicTo(240, -60, 230, 0, 200, 10); p.cubicTo(240, 30, 230, 80, 190, 90); p.cubicTo(220, 110, 210, 170, 160, 180)
    p.lineTo(-110, 190); p.close(); shape(c, p, "#E6BE8E", LW)


def ic_check(c, t, o):
    circ(c, 0, 0, 210, "#3FA45B", LW); c.drawPath(_tick(-110, 10, 1.4), ink(LW * 5, WHITE))


def ic_cross(c, t, o):
    circ(c, 0, 0, 210, RED, LW)
    line(c, -90, -90, 90, 90, LW * 5, WHITE); line(c, 90, -90, -90, 90, LW * 5, WHITE)


def ic_question(c, t, o):
    circ(c, 0, 0, 210, BLUE, LW); label(c, "?", 0, 90, 260, WHITE, align="center", skew=0)


def ic_search(c, t, o):
    line(c, 70, 70, 210, 210, LW * 6, METAL); circ(c, -40, -40, 150, SKY, LW * 1.4)


def ic_pin(c, t, o):
    p = skia.Path(); p.moveTo(0, 230); p.cubicTo(-120, 60, -170, -20, -170, -80); p.cubicTo(-170, -180, -90, -240, 0, -240)
    p.cubicTo(90, -240, 170, -180, 170, -80); p.cubicTo(170, -20, 120, 60, 0, 230); p.close(); shape(c, p, RED, LW)
    circ(c, 0, -80, 60, WHITE, LW * .6)


def ic_signpost(c, t, o):
    line(c, 0, -230, 0, 230, LW * 2.2, BROWN)
    for k, (s, txt) in enumerate(((1, o.get("text", "")), (-1, o.get("text2", "")))):
        y = -170 + k * 130
        poly(c, [(s * -30, y), (s * 200, y), (s * 250, y + 45), (s * 200, y + 90), (s * -30, y + 90)], CREAM, LW)
        if txt:
            label(c, txt, s * 110, y + 62, fit_size(txt, 44, 200), INK, align="center", skew=0)


def ic_dominoes(c, t, o):
    for k in range(5):
        c.save(); c.translate(-200 + k * 100, 120); c.rotate(min(70, max(0, (t * 120) - k * 25)))
        rect(c, -26, -200, 26, 0, CREAM, LW, r=8); circ(c, 0, -150, 10, INK, 0); circ(c, 0, -60, 10, INK, 0)
        c.restore()


def ic_label(c, t, o):
    """An honest stand-in for a thing not in the list: a card with its name (never dropped, never a look-alike)."""
    txt = str(o.get("text") or o.get("name") or "?").upper()
    size = fit_size(txt, 90, 420)
    rect(c, -240, -100, 240, 100, CREAM, LW, r=24)
    label(c, txt, 0, size * .35, size, INK, align="center", skew=0)


ICONS = {
    # tech
    "chip": ic_chip, "gpu": ic_gpu, "server": ic_server, "datacenter": ic_datacenter, "robot": ic_robot, "cloud": ic_cloud,
    "wifi": ic_wifi, "satellite": ic_satellite, "earth": ic_earth, "moon": ic_moon, "sun": ic_sun, "rocket": ic_rocket,
    "drone": ic_drone, "battery": ic_battery, "plug": ic_plug, "solar": ic_solar, "wind_turbine": ic_wind, "camera": ic_camera,
    "headphones": ic_headphones, "vr_headset": ic_vr, "code": ic_code, "bug": ic_bug, "shield": ic_shield, "key": ic_key,
    "ai": ic_ai,
    # money and business
    "bank": ic_bank, "credit_card": ic_credit_card, "wallet": ic_wallet, "bitcoin": ic_bitcoin, "gold": ic_gold,
    "briefcase": ic_briefcase, "handshake": ic_handshake, "factory": ic_factory, "store": ic_store, "truck": ic_truck,
    "ship": ic_ship, "plane": ic_plane, "train": ic_train, "oil": ic_oil, "crown": ic_crown, "flag": ic_flag, "tower": ic_tower,
    # institutions and people
    "gavel": ic_gavel, "scale": ic_scale, "document": ic_document, "newspaper": ic_newspaper, "megaphone": ic_megaphone,
    "mail": ic_mail, "hospital": ic_hospital, "pill": ic_pill, "syringe": ic_syringe, "dna": ic_dna, "microscope": ic_microscope,
    "gradcap": ic_gradcap, "people": ic_people, "podium": ic_podium,
    # life, nature, effects
    "fire": ic_fire, "lightning": ic_lightning, "explosion": ic_explosion, "water": ic_water, "tree": ic_tree,
    "mountain": ic_mountain, "food": ic_food, "coffee": ic_coffee, "gamepad": ic_gamepad, "play": ic_play, "music": ic_music,
    "ticket": ic_ticket, "thumbs_up": ic_thumbs_up, "check": ic_check, "cross": ic_cross, "question": ic_question,
    "search": ic_search, "pin": ic_pin, "signpost": ic_signpost, "dominoes": ic_dominoes, "label": ic_label,
}


FIT = 0.68   # our icons are drawn about 500 units tall; the kit's own stay within about 340, so labels never touch them


def _fitted(fn):
    def draw(c, t, o):
        c.save(); c.scale(FIT, FIT); fn(c, t, o); c.restore()
    return draw


def register(props_module) -> None:
    """Add our icons to the kit's ICONS at the kit's own size (theirs win on a name clash)."""
    for k, v in ICONS.items():
        props_module.ICONS.setdefault(k, _fitted(v))
