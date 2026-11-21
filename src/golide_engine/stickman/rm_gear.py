"""Equipment for ReachMora stories (owner 2026-11-21): industrial, home, school, office and organisation gear, smart
devices and glowing LED / neon signs with variants, after @afterhourtheories' worlds but SATURATED (the owner: their
colours are faded; ours are full). Same ink style and size as rm_extra (drawn ~500 units, fitted by rm_extra).
Options: "text" (a label or the sign's words), "color" (a sign's or device's colour).
"""
from __future__ import annotations

import math

import skia  # noqa: F401
from engine.kit import INK, LW, circ, fit_size, fp, ink, label, line, oval, poly, rect, shape  # noqa: F401
from engine.props import textlines

RED, ORANGE, YELLOW, GREEN = "#E8343C", "#FF8A1E", "#FFC928", "#2DBE5A"
BLUE, PURPLE, PINK, CYAN = "#2F7BEA", "#8E4FE0", "#FF4FA0", "#22C8E8"
DARK, METAL, WHITE, CREAM, WOOD = "#3A3D4A", "#A6ABB8", "#FFFFFF", "#F4EFE2", "#B87A44"


def _text(c, o, y=230, size=60, w=480, col=CREAM):
    if o.get("text"):
        label(c, o["text"], 0, y, fit_size(o["text"], size, w), col, align="center", stroke=12)


def _glow(c, path, colr, t, strength=1.0):
    """A neon tube: a soft halo, the bright tube and a white core, flickering a little."""
    k = .85 + .15 * math.sin(t * 9) * math.sin(t * 2.3)
    for w, a in ((46, 40), (28, 70), (16, 150)):
        c.drawPath(path, ink(w, colr, int(a * k * strength)))
    c.drawPath(path, ink(9, colr)); c.drawPath(path, ink(3.5, WHITE, 230))


# ---------------------------------------------------------------- industrial
def ic_forklift(c, t, o):
    rect(c, -200, -60, 90, 120, YELLOW, LW, r=16); rect(c, -150, -200, 40, -60, "#2A2D38", LW * .8)
    c.drawRect(skia.Rect(-135, -185, 25, -75), fp(CYAN, 90)); line(c, -160, -200, 50, -200, LW * 1.6, DARK)
    line(c, 130, -230, 130, 140, LW * 2, DARK); line(c, 160, -230, 160, 140, LW * 2, DARK)
    lift = 60 * (.5 + .5 * math.sin(t * 2))
    rect(c, 160, 60 - lift, 280, 80 - lift, DARK, LW * .7); rect(c, 170, -40 - lift, 270, 60 - lift, WOOD, LW * .8)
    for x in (-130, 40): circ(c, x, 140, 48, "#1E1F26", LW); circ(c, x, 140, 16, METAL, LW * .5)
    _text(c, o)


def ic_robot_arm(c, t, o):
    a = math.sin(t * 2) * 12
    rect(c, -140, 140, 140, 190, DARK, LW, r=10); circ(c, 0, 120, 60, ORANGE, LW)
    c.save(); c.rotate(-20 + a, 0, 120)
    rect(c, -32, -120, 32, 120, ORANGE, LW, r=30); circ(c, 0, -120, 44, DARK, LW * .8)
    c.save(); c.rotate(70 - a * 1.5, 0, -120)
    rect(c, -26, -260, 26, -120, ORANGE, LW, r=24); circ(c, 0, -260, 30, DARK, LW * .7)
    poly(c, [(-40, -270), (-10, -330), (-24, -270)], METAL, LW * .6); poly(c, [(40, -270), (10, -330), (24, -270)], METAL, LW * .6)
    c.restore(); c.restore()
    _text(c, o)


def ic_barrel(c, t, o):
    colr = o.get("color", BLUE)
    rect(c, -130, -190, 130, 190, colr, LW, r=24)
    for y in (-110, 0, 110): line(c, -130, y, 130, y, LW * 1.4, INK)
    oval(c, -130, -210, 130, -170, colr, LW * .8)
    _text(c, o, 60, 60, 220, WHITE)


def ic_crates(c, t, o):
    for (x, y, colr) in ((-140, 40, WOOD), (40, 40, WOOD), (-50, -140, "#C98A4A")):
        rect(c, x - 90, y - 90, x + 90, y + 90, colr, LW)
        line(c, x - 90, y - 90, x + 90, y + 90, LW * .7); line(c, x + 90, y - 90, x - 90, y + 90, LW * .7)
    rect(c, -250, 130, 150, 170, "#8A5A30", LW * .8)
    _text(c, o)


def ic_toolbox(c, t, o):
    rect(c, -220, -60, 220, 150, RED, LW, r=16); rect(c, -230, -80, 230, -40, "#B8242C", LW * .8, r=8)
    p = skia.Path(); p.moveTo(-80, -80); p.lineTo(-80, -150); p.lineTo(80, -150); p.lineTo(80, -80); c.drawPath(p, ink(LW * 2.4, DARK))
    rect(c, -30, 20, 30, 60, METAL, LW * .6, r=6)
    line(c, 120, -60, 180, -230, LW * 2, METAL); rect(c, 150, -280, 220, -220, METAL, LW * .7, r=6)
    _text(c, o)


def ic_gear(c, t, o):
    colr = o.get("color", ORANGE)
    c.save(); c.rotate(t * 40)
    p = skia.Path()
    for k in range(24):
        a = k * math.pi / 12; r = 200 if (k // 2) % 2 == 0 else 160
        (p.moveTo if k == 0 else p.lineTo)(r * math.cos(a), r * math.sin(a))
    p.close(); shape(c, p, colr, LW); circ(c, 0, 0, 70, DARK, LW * .8); circ(c, 0, 0, 26, METAL, LW * .5)
    c.restore(); _text(c, o)


def ic_drill(c, t, o):
    rect(c, -200, -120, 120, 0, YELLOW, LW, r=40); rect(c, -150, 0, -60, 190, DARK, LW, r=20)
    rect(c, 120, -80, 170, -40, DARK, LW * .7); c.save(); c.translate(170, -60); c.rotate(t * 900)
    rect(c, 0, -10, 130, 10, METAL, LW * .6); c.restore()
    rect(c, -170, 150, -40, 210, "#1E1F26", LW * .8, r=10)
    _text(c, o)


def ic_generator(c, t, o):
    rect(c, -240, -150, 240, 140, GREEN, LW, r=18)
    for k in range(6): line(c, -180 + k * 40, -100, -180 + k * 40, 60, LW * 1.2, "#1E7A3A")
    rect(c, 60, -100, 200, 30, DARK, LW * .7, r=8); circ(c, 130, -35, 36, YELLOW if math.sin(t * 6) > 0 else "#8A7020", LW * .6)
    label(c, "kW", 130, -20, 30, DARK, align="center", skew=0)
    for x in (-180, 180): rect(c, x - 30, 140, x + 30, 180, DARK, LW * .7)
    _text(c, o)


def ic_cone(c, t, o):
    poly(c, [(-40, -230), (40, -230), (130, 150), (-130, 150)], ORANGE, LW)
    poly(c, [(-64, -110), (64, -110), (84, -30), (-84, -30)], WHITE, 0); poly(c, [(-100, 40), (100, 40), (116, 100), (-116, 100)], WHITE, 0)
    rect(c, -190, 150, 190, 190, ORANGE, LW, r=8)
    _text(c, o)


def ic_hard_hat(c, t, o):
    p = skia.Path(); p.addArc(skia.Rect(-190, -170, 190, 190), 180, 180); p.close(); shape(c, p, o.get("color", YELLOW), LW)
    rect(c, -260, 0, 260, 50, o.get("color", YELLOW), LW, r=20); line(c, 0, -170, 0, 0, LW * 2.4, "#C99A10")
    _text(c, o)


def ic_tower_crane(c, t, o):
    line(c, -60, 230, -60, -200, LW * 2.4, YELLOW)
    for k in range(8): line(c, -80, 220 - k * 54, -40, 196 - k * 54, LW * .7, "#C99A10")
    line(c, -260, -200, 280, -200, LW * 2.4, YELLOW); poly(c, [(-60, -200), (-60, -280), (-20, -200)], YELLOW, LW * .7)
    rect(c, -260, -190, -160, -130, DARK, LW * .7)
    x = 80 + 140 * math.sin(t * .8); line(c, x, -200, x, 40, LW * .7, DARK)
    rect(c, x - 60, 40, x + 60, 110, BLUE, LW * .8)
    _text(c, o)


def ic_printer3d(c, t, o):
    rect(c, -210, -230, 210, 190, DARK, LW, r=14); c.drawRect(skia.Rect(-180, -200, 180, 150), fp(CYAN, 70))
    line(c, -180, -150, 180, -150, LW * 1.4, METAL); hx = 120 * math.sin(t * 3)
    rect(c, hx - 40, -170, hx + 40, -120, ORANGE, LW * .7); line(c, hx, -120, hx, -60, LW * .7, METAL)
    h = 30 + 50 * ((t * .3) % 1)
    poly(c, [(-80, 120), (80, 120), (40, 120 - h), (-40, 120 - h)], PURPLE, LW * .7)
    rect(c, -160, 120, 160, 140, METAL, LW * .6)
    _text(c, o)


# ---------------------------------------------------------------- home
def ic_sofa(c, t, o):
    colr = o.get("color", PURPLE)
    rect(c, -260, -120, 260, 40, colr, LW, r=40); rect(c, -290, -40, -190, 120, colr, LW, r=30); rect(c, 190, -40, 290, 120, colr, LW, r=30)
    rect(c, -200, 0, 200, 110, colr, LW, r=24); line(c, 0, 0, 0, 110, LW * .7)
    for x in (-250, 250): line(c, x, 120, x, 170, LW * 1.6, DARK)
    _text(c, o)


def ic_tv(c, t, o):
    rect(c, -280, -190, 280, 130, "#1E1F26", LW, r=14)
    c.drawRect(skia.Rect(-255, -168, 255, 108), fp(o.get("color", BLUE)))
    for k in range(4): c.drawRect(skia.Rect(-255 + k * 127, -168, -150 + k * 127, 108), fp([BLUE, PINK, YELLOW, GREEN][(k + int(t)) % 4], 120))
    line(c, -80, 130, -120, 190, LW * 1.4, DARK); line(c, 80, 130, 120, 190, LW * 1.4, DARK)
    _text(c, o, -20, 70, 460, WHITE)


def ic_fridge(c, t, o):
    rect(c, -150, -250, 150, 220, o.get("color", "#E8ECF2"), LW, r=22); line(c, -150, -60, 150, -60, LW)
    for y in (-200, -10): rect(c, 100, y, 116, y + 90, METAL, LW * .5, r=6)
    rect(c, -110, 40, -30, 100, YELLOW, LW * .4, r=4); rect(c, -20, 60, 50, 110, PINK, LW * .4, r=4)
    _text(c, o)


def ic_washer(c, t, o):
    rect(c, -190, -230, 190, 210, "#F4F6FA", LW, r=20); rect(c, -190, -230, 190, -150, "#DCE0E8", LW * .7, r=20)
    circ(c, 0, 20, 130, METAL, LW); circ(c, 0, 20, 100, "#8AD0F8", LW * .7)
    c.save(); c.rotate(t * 300, 0, 20)
    for k in range(3): c.drawOval(skia.Rect(-60 + k * 40, -20, -20 + k * 40, 40), fp([RED, YELLOW, PURPLE][k]))
    c.restore()
    for x in (90, 130): circ(c, x, -190, 14, BLUE, LW * .4)
    _text(c, o)


def ic_lamp(c, t, o):
    c.drawCircle(0, -120, 230, fp("#FFE9A0", 60))
    poly(c, [(-130, -60), (130, -60), (80, -220), (-80, -220)], o.get("color", YELLOW), LW)
    line(c, 0, -60, 0, 170, LW * 1.6, DARK); oval(c, -110, 150, 110, 200, DARK, LW)
    _text(c, o)


def ic_door(c, t, o):
    rect(c, -160, -260, 160, 220, WOOD, LW, r=10); rect(c, -120, -220, 120, -40, "#C98A4A", LW * .7); rect(c, -120, 0, 120, 180, "#C98A4A", LW * .7)
    circ(c, 110, -10, 16, YELLOW, LW * .5)
    _text(c, o)


def ic_bed(c, t, o):
    rect(c, -280, -160, -220, 130, WOOD, LW); rect(c, -230, 0, 280, 90, o.get("color", BLUE), LW, r=12)
    rect(c, -210, -50, -60, 10, WHITE, LW * .8, r=20); rect(c, -40, -20, 280, 20, "#6FA8F0", LW * .7, r=10)
    for x in (-250, 260): line(c, x, 90, x, 150, LW * 1.6, DARK)
    _text(c, o)


def ic_microwave(c, t, o):
    rect(c, -230, -140, 230, 140, "#E8ECF2", LW, r=16); rect(c, -200, -110, 90, 110, "#1E1F26", LW * .7, r=8)
    c.drawRect(skia.Rect(-190, -100, 80, 100), fp("#FFC060", 90 + int(60 * math.sin(t * 5))))
    for k in range(4): circ(c, 160, -80 + k * 50, 14, METAL, LW * .4)
    _text(c, o)


def ic_plant_pot(c, t, o):
    poly(c, [(-110, 60), (110, 60), (80, 200), (-80, 200)], ORANGE, LW)
    for k in range(7):
        a = math.radians(-160 + k * 23) + .05 * math.sin(t * 2 + k)
        p = skia.Path(); p.moveTo(0, 60); p.quadTo(150 * math.cos(a) * .6, 60 + 230 * math.sin(a) * .6, 200 * math.cos(a), 60 + 260 * math.sin(a))
        c.drawPath(p, ink(LW * 4, GREEN)); c.drawPath(p, ink(LW * .7))
    _text(c, o)


# ---------------------------------------------------------------- school and office
def ic_school_desk(c, t, o):
    rect(c, -240, -40, 240, 0, WOOD, LW, r=8); line(c, -200, 0, -200, 190, LW * 1.6, DARK); line(c, 200, 0, 200, 190, LW * 1.6, DARK)
    rect(c, -60, -110, 120, -40, BLUE, LW * .8, r=6); line(c, -150, -60, -60, -100, LW * 1.4, YELLOW)
    _text(c, o)


def ic_chalkboard(c, t, o):
    rect(c, -280, -210, 280, 170, WOOD, LW, r=10); rect(c, -250, -180, 250, 140, "#2E5A46", LW * .7)
    txt = o.get("text", "")
    if txt: label(c, txt, 0, -10, fit_size(txt, 80, 440), CREAM, align="center", skew=0)
    else: textlines(c, -200, -120, 400, 4, gap=60, v="#E8F0E8", w=6)
    for x in (-200, 200): line(c, x, 170, x + (40 if x > 0 else -40), 230, LW * 1.4, DARK)


def ic_backpack(c, t, o):
    colr = o.get("color", RED)
    rect(c, -160, -200, 160, 200, colr, LW, r=70); rect(c, -110, 40, 110, 170, "#B8242C" if colr == RED else colr, LW * .8, r=30)
    p = skia.Path(); p.addArc(skia.Rect(-70, -280, 70, -150), 180, 180); c.drawPath(p, ink(LW * 2.4, DARK))
    rect(c, -20, 60, 20, 90, YELLOW, LW * .5, r=6)
    _text(c, o)


def ic_pencil(c, t, o):
    c.save(); c.rotate(-35)
    rect(c, -60, -230, 60, 150, YELLOW, LW); rect(c, -60, -260, 60, -210, PINK, LW * .8, r=12); rect(c, -60, -215, 60, -195, METAL, LW * .6)
    poly(c, [(-60, 150), (60, 150), (0, 260)], "#F0C890", LW); poly(c, [(-18, 226), (18, 226), (0, 260)], DARK, 0)
    c.restore()


def ic_globe(c, t, o):
    line(c, 0, 200, 0, 150, LW * 2, DARK); rect(c, -110, 190, 110, 220, DARK, LW * .8, r=8)
    p = skia.Path(); p.addArc(skia.Rect(-210, -230, 210, 190), 110, 140); c.drawPath(p, ink(LW * 1.4, YELLOW))
    circ(c, 0, -20, 170, BLUE, LW); c.save(); pp = skia.Path(); pp.addCircle(0, -20, 170); c.clipPath(pp, doAntiAlias=True)
    off = (t * 60) % 340
    for k in (-1, 0):
        for (dx, dy, w, h) in ((-60, -80, 90, 50), (40, 20, 80, 60), (-90, 60, 50, 40)):
            cx = dx + off + k * 340; c.drawOval(skia.Rect(cx - w, -20 + dy - h, cx + w, -20 + dy + h), fp(GREEN))
    c.restore(); c.drawCircle(0, -20, 170, ink(LW))


def ic_calculator(c, t, o):
    rect(c, -150, -230, 150, 220, DARK, LW, r=22); rect(c, -115, -195, 115, -90, "#BFE8C0", LW * .6, r=6)
    label(c, o.get("text", "1,024"), 100, -120, 60, "#1E3A20", align="right", skew=0)
    for j in range(4):
        for i in range(4):
            rect(c, -110 + i * 58, -60 + j * 64, -66 + i * 58, -16 + j * 64, ORANGE if i == 3 else METAL, LW * .4, r=8)


def ic_school_bus(c, t, o):
    rect(c, -280, -150, 260, 100, YELLOW, LW, r=24); poly(c, [(260, -60), (300, -60), (300, 100), (260, 100)], YELLOW, LW)
    for k in range(5): rect(c, -250 + k * 95, -120, -180 + k * 95, -40, "#BFE3F2", LW * .6, r=6)
    line(c, -280, 10, 300, 10, LW * 1.4, DARK); label(c, o.get("text", "SCHOOL BUS"), -10, 70, 40, DARK, align="center", skew=0)
    for x in (-170, 170): circ(c, x, 110, 46, "#1E1F26", LW); circ(c, x, 110, 14, METAL, LW * .4)


def ic_printer(c, t, o):
    rect(c, -220, -60, 220, 120, "#E8ECF2", LW, r=16); rect(c, -150, -160, 150, -60, "#DCE0E8", LW * .8)
    out = 60 * ((t * .5) % 1); rect(c, -120, 100, 120, 160 + out, WHITE, LW * .7); textlines(c, -90, 120, 180, 2, gap=20, v=METAL, w=4)
    circ(c, 170, -20, 12, GREEN, LW * .4)
    _text(c, o, 250)


def ic_water_cooler(c, t, o):
    rect(c, -110, -40, 110, 220, "#E8ECF2", LW, r=12); rect(c, -90, -250, 90, -40, "#8AD0F8", LW, r=40)
    for k in range(3):
        u = (t * .7 + k / 3) % 1; c.drawCircle(-20 + k * 20, -60 - u * 160, 8 + 4 * k, fp(WHITE, int(200 * (1 - u))))
    rect(c, -40, 40, -10, 70, BLUE, LW * .4); rect(c, 10, 40, 40, 70, RED, LW * .4)
    _text(c, o)


def ic_cabinet(c, t, o):
    rect(c, -140, -250, 140, 220, "#8A93A6", LW, r=10)
    for k in range(4):
        y = -230 + k * 112; rect(c, -120, y, 120, y + 96, "#A6AEC0", LW * .6, r=6); rect(c, -40, y + 36, 40, y + 54, DARK, LW * .4, r=6)
    _text(c, o)


def ic_whiteboard(c, t, o):
    rect(c, -280, -200, 280, 150, WHITE, LW, r=8)
    txt = o.get("text", "")
    if txt: label(c, txt, 0, -10, fit_size(txt, 80, 460), BLUE, align="center", skew=0)
    else:
        p = skia.Path(); p.moveTo(-220, 100)
        for k, y in enumerate((60, 80, 20, 0, -60, -120)): p.lineTo(-160 + k * 70, y)
        c.drawPath(p, ink(LW * 1.2, RED)); textlines(c, 60, -160, 180, 3, gap=40, v=BLUE, w=6)
    for x in (-220, 220): line(c, x, 150, x, 230, LW * 1.4, METAL)


def ic_office_chair(c, t, o):
    rect(c, -110, -240, 110, -20, o.get("color", DARK), LW, r=40); rect(c, -140, -20, 140, 30, o.get("color", DARK), LW, r=20)
    line(c, 0, 30, 0, 140, LW * 1.8, METAL)
    for a in (-60, -20, 20, 60): line(c, 0, 140, a * 2.4, 180, LW * 1.4, METAL); circ(c, a * 2.4, 190, 14, "#1E1F26", LW * .4)


def ic_projector(c, t, o):
    c.drawPath(skia.Path.Polygon([(150, -40), (300, -200), (300, 160)], True), fp("#FFF6C8", 90))
    rect(c, -220, -100, 150, 60, "#E8ECF2", LW, r=20); circ(c, 110, -20, 50, DARK, LW * .8); circ(c, 110, -20, 24, CYAN, LW * .5)
    for x in (-170, 60): line(c, x, 60, x, 110, LW * 1.6, DARK)
    _text(c, o)


def ic_desktop(c, t, o):
    rect(c, -260, -230, 260, 90, "#1E1F26", LW, r=14); c.drawRect(skia.Rect(-235, -205, 235, 65), fp(o.get("color", BLUE)))
    textlines(c, -200, -170, 300, 4, gap=46, v=WHITE, w=6)
    rect(c, -40, 90, 40, 150, DARK, LW * .7); rect(c, -140, 150, 140, 170, DARK, LW * .7)
    rect(c, -230, 190, 230, 230, "#E8ECF2", LW * .8, r=8)
    _text(c, o, -60, 60, 420, WHITE)


def ic_retro_pc(c, t, o):
    rect(c, -220, -250, 220, 120, "#F0E6CC", LW, r=26); rect(c, -180, -210, 180, 40, "#3A3D4A", LW * .8, r=14)
    c.drawRect(skia.Rect(-165, -195, 165, 25), fp(o.get("color", PINK)))
    circ(c, 0, -85, 46, YELLOW, LW * .5); c.drawRect(skia.Rect(-165, -60, 165, 25), fp(PURPLE, 160))
    rect(c, 60, 70, 180, 90, DARK, LW * .4); rect(c, -260, 140, 260, 220, "#F0E6CC", LW, r=12)
    _text(c, o, -100, 50, 300, WHITE)


# ---------------------------------------------------------------- smart devices
def ic_tablet(c, t, o):
    rect(c, -190, -260, 190, 240, "#1E1F26", LW, r=30); rect(c, -165, -230, 165, 205, o.get("color", PURPLE), LW * .5, r=12)
    for k in range(3): rect(c, -130, -190 + k * 120, 130, -100 + k * 120, WHITE, LW * .4, r=10)
    _text(c, o, 0, 60, 300, WHITE)


def ic_smartwatch(c, t, o):
    rect(c, -70, -280, 70, 280, DARK, LW, r=40); rect(c, -130, -140, 130, 140, "#1E1F26", LW, r=50)
    p = skia.Path(); p.addArc(skia.Rect(-90, -90, 90, 90), -90, 300 * ((t * .3) % 1) + 20); c.drawPath(p, ink(LW * 2.6, GREEN))
    label(c, o.get("text", "72"), 0, 20, 64, WHITE, align="center", skew=0)


def ic_smart_speaker(c, t, o):
    rect(c, -120, -200, 120, 200, "#2A2D38", LW, r=60)
    for k in range(5): line(c, -80, -130 + k * 60, 80, -130 + k * 60, LW * .6, "#454857")
    k = .5 + .5 * math.sin(t * 6); oval(c, -100, -230, 100, -170, "#1E1F26", LW)
    c.drawOval(skia.Rect(-90, -220, 90, -180), ink(LW * 1.6, CYAN, int(120 + 135 * k)))
    _text(c, o)


def ic_router(c, t, o):
    rect(c, -230, 20, 230, 130, "#E8ECF2", LW, r=24)
    for x in (-150, 150): line(c, x, 20, x - 30 if x < 0 else x + 30, -200, LW * 1.6, DARK)
    for k in range(5): circ(c, -150 + k * 60, 75, 12, GREEN if (int(t * 6) + k) % 3 else "#1E7A3A", LW * .3)
    for r in (60, 110, 160):
        p = skia.Path(); p.addArc(skia.Rect(-r, -100 - r, r, -100 + r), 225, 90); c.drawPath(p, ink(LW * 1.4, BLUE, 120 + int(100 * math.sin(t * 5 + r))))


def ic_earbuds(c, t, o):
    rect(c, -200, -40, 200, 170, WHITE, LW, r=80); line(c, -200, 40, 200, 40, LW * .7)
    for x in (-80, 80):
        circ(c, x, -100, 60, WHITE, LW); rect(c, x - 18, -60, x + 18, 40, WHITE, LW * .8, r=16)
    circ(c, 0, 100, 12, GREEN, LW * .3)


def ic_console(c, t, o):
    rect(c, -270, -60, 270, 120, "#1E1F26", LW, r=30)
    circ(c, -170, 30, 44, DARK, LW * .7); circ(c, 170, 30, 44, DARK, LW * .7)
    for (x, y, colr) in ((150, -10, RED), (190, 30, BLUE), (150, 70, GREEN), (110, 30, YELLOW)): circ(c, x, y, 14, colr, LW * .3)
    rect(c, -200, 15, -140, 45, METAL, LW * .3); rect(c, -185, 0, -155, 60, METAL, LW * .3)
    _text(c, o)


def ic_smart_bulb(c, t, o):
    hue = [PINK, CYAN, YELLOW, PURPLE, GREEN][int(t * 1.5) % 5] if not o.get("color") else o["color"]
    c.drawCircle(0, -60, 240, fp(hue, 60))
    circ(c, 0, -60, 160, hue, LW); rect(c, -70, 90, 70, 190, METAL, LW * .8, r=10)
    for y in (120, 150): line(c, -70, y, 70, y, LW * .6)


def ic_keyboard(c, t, o):
    rect(c, -280, -80, 280, 100, DARK, LW, r=18)
    for j in range(3):
        for i in range(9):
            pressed = (int(t * 8) + i * 3 + j) % 11 == 0
            rect(c, -250 + i * 56, -54 + j * 50 + (4 if pressed else 0), -206 + i * 56, -14 + j * 50 + (4 if pressed else 0),
                 CYAN if pressed else "#5A5E6E", LW * .3, r=6)


# ---------------------------------------------------------------- LED and neon signs
def ic_neon(c, t, o):
    """A neon sign with its words; "color": the tube's colour (pink default); "frame": false for no box."""
    txt = (o.get("text") or "OPEN").upper(); colr = o.get("color", PINK)
    rect(c, -290, -170, 290, 170, "#14121C", LW, r=24)
    fr = skia.Path(); fr.addRRect(skia.RRect.MakeRectXY(skia.Rect(-255, -135, 255, 135), 30, 30))
    if o.get("frame", True): _glow(c, fr, CYAN if colr != CYAN else PINK, t, .8)
    size = fit_size(txt, 120, 430)
    for w, a in ((22, 60), (10, 120)):
        label(c, txt, 0, size * .34, size, colr, align="center", stroke=w, stroke_col=colr, skew=0, alpha=a / 255)
    label(c, txt, 0, size * .34, size, WHITE, align="center", stroke=6, stroke_col=colr, skew=0)


def ic_led_board(c, t, o):
    """A scrolling LED board: amber dots carrying the words across."""
    txt = (o.get("text") or "BREAKING NEWS").upper() + "   "
    rect(c, -300, -110, 300, 110, "#0E0E14", LW, r=12)
    for y in range(-90, 100, 18):
        for x in range(-285, 290, 18): c.drawCircle(x, y, 4, fp("#2A2418"))
    c.save(); c.clipRect(skia.Rect(-290, -100, 290, 100))
    from engine.kit import text_w
    w = text_w(txt, 110); x0 = 290 - (t * 260) % (w + 580)
    label(c, txt, x0, 40, 110, o.get("color", "#FFB020"), skew=0); c.restore()
    for x in (-220, 220): line(c, x, 110, x, 220, LW * 1.4, DARK)


def ic_exit_sign(c, t, o):
    rect(c, -230, -110, 230, 110, "#1E9A4A", LW, r=12); c.drawRect(skia.Rect(-230, -110, 230, 110), fp("#5FFF9A", 40))
    label(c, o.get("text", "EXIT").upper(), 40, 40, 110, WHITE, align="center", skew=0)
    circ(c, -160, -40, 16, WHITE, 0); line(c, -160, -24, -150, 30, 12, WHITE); line(c, -150, 30, -180, 80, 10, WHITE)


def ic_neon_heart(c, t, o):
    p = skia.Path(); p.moveTo(0, 180); p.cubicTo(-330, -20, -180, -270, 0, -110); p.cubicTo(180, -270, 330, -20, 0, 180); p.close()
    _glow(c, p, o.get("color", PINK), t)


def ic_neon_arrow(c, t, o):
    p = skia.Path(); p.moveTo(-250, 0); p.lineTo(180, 0); p.moveTo(90, -100); p.lineTo(200, 0); p.lineTo(90, 100)
    c.save(); c.translate(20 * math.sin(t * 5), 0); _glow(c, p, o.get("color", YELLOW), t); c.restore()
    _text(c, o, 210, 60, 480)


def ic_tombstone(c, t, o):
    p = skia.Path(); p.moveTo(-170, 200); p.lineTo(-170, -80); p.quadTo(-170, -260, 0, -260); p.quadTo(170, -260, 170, -80); p.lineTo(170, 200); p.close()
    shape(c, p, "#E8ECF2", LW); label(c, "R.I.P.", 0, -110, 70, DARK, align="center", skew=0)
    txt = o.get("text", "")
    if txt: label(c, txt.upper(), 0, -10, fit_size(txt.upper(), 50, 280), DARK, align="center", skew=0)
    for k in range(5): circ(c, -150 + k * 75, 200, 30, [PINK, YELLOW, PURPLE, RED, CYAN][k], LW * .4)
    rect(c, -230, 200, 230, 230, GREEN, LW * .7)


ICONS = {
    "forklift": ic_forklift, "robot_arm": ic_robot_arm, "barrel": ic_barrel, "crates": ic_crates, "toolbox": ic_toolbox,
    "gear": ic_gear, "drill": ic_drill, "generator": ic_generator, "cone": ic_cone, "hard_hat": ic_hard_hat,
    "tower_crane": ic_tower_crane, "printer3d": ic_printer3d,
    "sofa": ic_sofa, "tv": ic_tv, "fridge": ic_fridge, "washer": ic_washer, "lamp": ic_lamp, "door": ic_door, "bed": ic_bed,
    "microwave": ic_microwave, "plant_pot": ic_plant_pot,
    "school_desk": ic_school_desk, "chalkboard": ic_chalkboard, "backpack": ic_backpack, "pencil": ic_pencil,
    "globe": ic_globe, "calculator": ic_calculator, "school_bus": ic_school_bus,
    "printer": ic_printer, "water_cooler": ic_water_cooler, "cabinet": ic_cabinet, "whiteboard": ic_whiteboard,
    "office_chair": ic_office_chair, "projector": ic_projector, "desktop": ic_desktop, "retro_pc": ic_retro_pc,
    "tablet": ic_tablet, "smartwatch": ic_smartwatch, "smart_speaker": ic_smart_speaker, "router": ic_router,
    "earbuds": ic_earbuds, "console": ic_console, "smart_bulb": ic_smart_bulb, "keyboard": ic_keyboard,
    "neon": ic_neon, "led_board": ic_led_board, "exit_sign": ic_exit_sign, "neon_heart": ic_neon_heart,
    "neon_arrow": ic_neon_arrow, "tombstone": ic_tombstone,
}
