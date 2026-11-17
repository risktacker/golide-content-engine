"""Props + icons in the ink style. draw_prop(c, name, x, y, s, t, **opts) draws centred at x,y.
A prop is about 300 px wide at s=1."""
import math, random
import skia
from .kit import *


def soft_shadow(c, x0, y0, x1, y1):
    """Cheap soft drop shadow (three stacked translucent round rects, no blur filter)."""
    for g, a in ((10, 22), (5, 26), (0, 30)):
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x0 - g, y0 - g, x1 + g, y1 + g), 14 + g, 14 + g), fp((40, 28, 8), a))


def textlines(c, x0, y0, x1, n, gap=30, v='#8E8878', w=6):
    r = random.Random(int(x0 * 7 + y0))
    for i in range(n): c.drawLine(x0, y0 + i * gap, x1 - r.uniform(0, (x1 - x0) * .3), y0 + i * gap, ink(w, v))


def bills(c, x, y, rot=0, n=3):
    c.save(); c.translate(x, y); c.rotate(rot)
    for a_ in (-16, -4, 9)[:n]:
        c.save(); c.rotate(a_); rect(c, -130, -70, 130, 70, '#6FA36A', LW); rect(c, -108, -50, 108, 50, '#84B67E', LW * .5)
        circ(c, 0, 0, 26, '#6FA36A', LW * .5); label(c, "$", 0, 14, 40, '#2F5A2E', align='center', skew=0); c.restore()
    c.restore()


def sleeve(c, x0, y0, x1, y1, width, v, cuff='#F4EFE2', skin='#E6BE8E', fingers=True):
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0)); L = math.hypot(x1 - x0, y1 - y0); hr = width * .5
    c.save(); c.translate(x0, y0); c.rotate(ang); circ(c, L + hr * .55, 0, hr, skin, LW)
    if fingers:
        for k in (-.42, 0, .42): c.drawLine(L + hr * 1.2, k * hr, L + hr * 1.52, k * hr * 1.1, ink(LW * .8))
    rect(c, -200, -width / 2, L, width / 2, v, LW); rect(c, L - 34, -width / 2 - 5, L + 6, width / 2 + 5, cuff, LW); c.restore()


# ---------------------------------------------------------------- documents (table items, ~800x600)
def doc_newspaper(c, o, t, ring=0.0):
    soft_shadow(c, -392, -288, 412, 312); rect(c, -400, -300, 400, 300, '#F1EAD6', LW)
    title = o.get('title', 'THE DAILY NEWS'); head = o.get('text', 'BREAKING NEWS')
    label(c, title, 0, -222, fit_size(title, 84, 740, MARKER), INK, font=MARKER, align='center', skew=0)
    c.drawLine(-370, -196, 370, -196, ink(5)); c.drawLine(-370, -184, 370, -184, ink(2.5))
    hs = fit_size(head, 54, 720); label(c, head, 0, -118, hs, INK, align='center', skew=-0.08)
    rect(c, -360, -80, -60, 262, '#E3DAC2', LW * .6)
    poly(c, [(-340, 240), (-260, 60), (-200, 150), (-140, 20), (-80, 240)], '#B9AE90', LW * .5); circ(c, -120, -20, 24, '#D9C27A', LW * .5)
    textlines(c, -20, -62, 360, 11)
    if ring > 0:
        rg = skia.Path(); rg.addArc(skia.Rect(-hs * len(head) * .27 - 40, -176, hs * len(head) * .27 + 40, -92), -170, 356 * ease(ring)); c.drawPath(rg, ink(11, RED))


def doc_letter(c, o, t, ring=0.0):
    soft_shadow(c, -312, -348, 332, 372); rect(c, -320, -360, 320, 360, '#FBFAF2', LW)
    head = o.get('title', 'OFFICIAL LETTER'); blue = o.get('ink', '#2A44A8')
    circ(c, 0, -280, 40, blue, LW * .6); c.drawCircle(0, -280, 22, fp('#FBFAF2'))
    label(c, head, 0, -196, fit_size(head, 46, 560), blue, align='center', skew=0); c.drawLine(-270, -168, 270, -168, ink(3, blue))
    if o.get('text'): label(c, o['text'], -260, -110, fit_size(o['text'], 40, 520), INK, skew=-0.06)
    textlines(c, -260, -60, 270, 8, 38)
    sg = skia.Path(); sg.moveTo(60, 300); sg.cubicTo(100, 240, 130, 330, 170, 280); sg.cubicTo(200, 250, 220, 320, 270, 290); c.drawPath(sg, ink(5, '#1B2A6A'))


def doc_contract(c, o, t, ring=0.0):
    o = dict(o); o.setdefault('title', 'CONTRACT'); o['ink'] = INK; doc_letter(c, o, t, ring)
    c.drawLine(-260, 300, 0, 300, ink(3, INK)); label(c, "SIGN HERE", -250, 336, 30, '#8E8878', skew=0)


def doc_receipt(c, o, t, ring=0.0):
    soft_shadow(c, -182, -392, 202, 412)
    p = skia.Path(); p.moveTo(-190, -400); p.lineTo(190, -400)
    for i in range(12): p.lineTo(190 - (i + .5) * 31.6, 400 - (12 if i % 2 == 0 else 0))
    p.lineTo(-190, 400); p.close(); shape(c, p, '#FFFFFF', LW)
    label(c, o.get('title', 'RECEIPT'), 0, -320, 52, INK, font=MARKER, align='center', skew=0)
    rows = o.get('rows', [["ITEM", "$9.99"], ["ITEM", "$4.50"], ["ITEM", "$12.00"]])
    for i, (a, b) in enumerate(rows[:7]):
        label(c, str(a), -160, -230 + i * 62, 36, '#4A4650', skew=0); label(c, str(b), 160, -230 + i * 62, 36, '#4A4650', align='right', skew=0)
    c.drawLine(-160, 230, 160, 230, ink(3, INK, 160)); label(c, "TOTAL", -160, 300, 46, INK, skew=0)
    label(c, o.get('text', '$26.49'), 160, 300, 50, RED, align='right', skew=0)


def doc_photo(c, o, t, ring=0.0):
    soft_shadow(c, -262, -292, 282, 332); rect(c, -270, -300, 270, 320, '#FBFAF2', LW)
    rect(c, -230, -260, 230, 200, '#8FB5D0', LW * .6)
    poly(c, [(-230, 200), (-120, 20), (-40, 120), (60, -40), (230, 200)], '#5A7A5A', LW * .5); circ(c, 140, -170, 34, '#FFE27A', LW * .5)
    if o.get('text'): label(c, o['text'], 0, 280, fit_size(o['text'], 54, 480), INK, font=FONT_HAND, align='center', skew=0)


def doc_cash(c, o, t, ring=0.0):
    bills(c, -120, -60, 8); bills(c, 120, 80, -10)
    if o.get('text'): label(c, o['text'], 0, 300, fit_size(o['text'], 90, 700), LIME, align='center', stroke=14)


def doc_phone(c, o, t, ring=0.0):
    soft_shadow(c, -182, -352, 202, 372); rect(c, -190, -360, 190, 360, '#1E1E26', LW, r=40)
    rect(c, -166, -320, 166, 320, '#EAF2FA', LW * .5, r=18); rect(c, -40, -344, 40, -332, '#3A3A46', 0, r=6)
    msgs = o.get('messages') or [o.get('text', 'New message')]
    for i, m in enumerate(msgs[:4]):
        y = -270 + i * 140; mine = i % 2 == 1; x0, x1 = (-140, 110) if not mine else (-110, 140)
        rect(c, x0, y, x1, y + 110, '#FFFFFF' if not mine else '#7FD07A', LW * .5, r=22)
        lines = wrap(str(m), 34, x1 - x0 - 30)
        for j, ln in enumerate(lines[:2]): label(c, ln, x0 + 16, y + 44 + j * 40, 34, INK, skew=0)


DOCS = dict(newspaper=doc_newspaper, letter=doc_letter, contract=doc_contract, receipt=doc_receipt, photo=doc_photo, cash=doc_cash, phone=doc_phone)


# ---------------------------------------------------------------- icons (centred, ~300 px)
def ic_bulb(c, t, o):
    for k, a in ((260, 20), (190, 30)): c.drawCircle(0, -40, k, fp('#FFE9A0', a))
    circ(c, 0, -40, 120, '#FFE27A', LW); rect(c, -56, 70, 56, 150, '#A0A4B0', LW, r=10)
    for y in (96, 122): c.drawLine(-56, y, 56, y, ink(LW * .6))
    w = skia.Path(); w.moveTo(-36, 70); w.lineTo(-20, -30); w.lineTo(0, 10); w.lineTo(20, -30); w.lineTo(36, 70); c.drawPath(w, ink(LW * .7, '#B8862A'))


def ic_brain(c, t, o):
    p = skia.Path()
    for (x, y, r) in ((-80, -40, 80), (0, -80, 90), (80, -40, 80), (-60, 40, 80), (60, 40, 80), (0, 10, 80)): p.addCircle(x, y, r)
    p = skia.Op(p, skia.Path(), skia.PathOp.kUnion_PathOp); shape(c, p, '#F4A0B8', LW)
    for s in ((-90, -60, -30, -10, -70, 40), (20, -110, 60, -40, 10, 20), (90, -20, 60, 30, 110, 70)):
        q = skia.Path(); q.moveTo(s[0], s[1]); q.cubicTo(s[2], s[3], s[4], s[5], s[4] + 20, s[5] + 20); c.drawPath(q, ink(LW * .7, '#B85A78'))
    line(c, 0, -160, 0, 110, LW * .7, '#B85A78')


def ic_clock(c, t, o):
    circ(c, 0, 0, 140, '#F4EFE2', LW * 1.2)
    for i in range(12): a = i * math.pi / 6; c.drawLine(118 * math.cos(a), 118 * math.sin(a), 132 * math.cos(a), 132 * math.sin(a), ink(LW * .7))
    a1 = t * 4; a2 = t * .4
    line(c, 0, 0, 100 * math.sin(a1), -100 * math.cos(a1), LW, RED); line(c, 0, 0, 64 * math.sin(a2), -64 * math.cos(a2), LW * 1.3); c.drawCircle(0, 0, 9, fp(INK))


def ic_moneybag(c, t, o):
    p = skia.Path(); p.moveTo(-50, -90); p.cubicTo(-200, -20, -170, 150, 0, 150); p.cubicTo(170, 150, 200, -20, 50, -90); p.close(); shape(c, p, '#C9A25A', LW)
    poly(c, [(-50, -90), (50, -90), (80, -150), (30, -130), (0, -160), (-30, -130), (-80, -150)], '#C9A25A', LW); rect(c, -60, -102, 60, -82, '#8A6A3A', LW * .8, r=8)
    label(c, "$", 0, 70, 150, '#5E4A20', font=MARKER, align='center', skew=0)


def ic_coins(c, t, o):
    n = int(o.get('n', 5))
    for k in range(3):
        for i in range(n - k * 2):
            x = (k - 1) * 130; y = 120 - i * 26; oval(c, x - 60, y - 22, x + 60, y + 22, '#E8B84A', LW * .8)
    c.drawCircle(-30, 20, 10, fp('#FFFFFF', 200))


def ic_house(c, t, o):
    rect(c, -140, -40, 140, 150, o.get('color', '#E8D6B0'), LW); poly(c, [(-180, -30), (0, -170), (180, -30)], '#C8242C', LW)
    rect(c, -40, 40, 40, 150, '#6A4428', LW); rect(c, 60, 0, 120, 60, '#BFE3F2', LW * .7); rect(c, -120, 0, -60, 60, '#BFE3F2', LW * .7); rect(c, 80, -150, 120, -80, '#8A4A3A', LW * .8)


def ic_trophy(c, t, o):
    p = skia.Path(); p.moveTo(-110, -140); p.lineTo(110, -140); p.cubicTo(110, 0, 50, 40, 0, 40); p.cubicTo(-50, 40, -110, 0, -110, -140); p.close(); shape(c, p, '#F2C14E', LW)
    for sx in (-1, 1):
        h = skia.Path(); h.addArc(skia.Rect(sx * 110 - 50, -130, sx * 110 + 50, -30), -90 if sx > 0 else 90, 180); c.drawPath(h, ink(LW * 1.6))
    rect(c, -20, 40, 20, 100, '#D9A53A', LW); rect(c, -80, 100, 80, 150, '#6A4428', LW, r=8); label(c, "1", 0, -40, 100, '#B8862A', font=MARKER, align='center', skew=0)


def ic_heart(c, t, o):
    b = 1 + .06 * math.sin(t * 7); c.save(); c.scale(b, b)
    p = skia.Path(); p.moveTo(0, 130); p.cubicTo(-220, -10, -130, -190, 0, -80); p.cubicTo(130, -190, 220, -10, 0, 130); p.close(); shape(c, p, o.get('color', '#E8485A'), LW)
    c.drawCircle(-80, -60, 18, fp('#FFFFFF', 200)); c.restore()


def ic_lock(c, t, o):
    sh = skia.Path(); sh.addArc(skia.Rect(-80, -190, 80, -30), 180, 180); c.drawPath(sh, ink(LW * 4)); c.drawPath(sh, ink(LW * 2.4, '#A0A4B0'))
    rect(c, -130, -110, 130, 120, '#F2C14E', LW, r=20); circ(c, 0, -10, 24, INK, 0); rect(c, -9, -10, 9, 50, INK, 0)


def ic_hourglass(c, t, o):
    rect(c, -130, -170, 130, -140, '#8E5C36', LW); rect(c, -130, 140, 130, 170, '#8E5C36', LW)
    g = skia.Path(); g.moveTo(-100, -140); g.lineTo(100, -140); g.lineTo(10, 0); g.lineTo(100, 140); g.lineTo(-100, 140); g.lineTo(-10, 0); g.close(); shape(c, g, '#E8F4FA', LW)
    k = (t * .15) % 1; poly(c, [(-100 + 90 * k, -140 + 140 * k), (100 - 90 * k, -140 + 140 * k), (10, 0), (-10, 0)], '#E8C070', 0)
    poly(c, [(-100, 140), (100, 140), (100 - 90 * (1 - k), 140 - 100 * k), (-100 + 90 * (1 - k), 140 - 100 * k)], '#E8C070', 0); c.drawLine(0, 0, 0, 140, ink(4, '#E8C070'))


def ic_warning(c, t, o):
    poly(c, [(0, -170), (190, 150), (-190, 150)], '#F2C14E', LW * 1.3); label(c, "!", 0, 120, 220, INK, font=MARKER, align='center', skew=0)


def ic_laptop(c, t, o):
    rect(c, -200, -170, 200, 80, '#2A2A34', LW, r=14); rect(c, -176, -148, 176, 58, o.get('screen', '#7FD0FF'), LW * .6)
    poly(c, [(-240, 80), (240, 80), (270, 130), (-270, 130)], '#A0A4B0', LW)
    if o.get('text'): label(c, o['text'], 0, -30, fit_size(o['text'], 70, 320), INK, align='center', skew=0)


def ic_gift(c, t, o):
    rect(c, -150, -60, 150, 150, '#C8242C', LW); rect(c, -170, -110, 170, -50, '#E04A4A', LW); rect(c, -24, -110, 24, 150, '#F2C14E', LW * .8)
    for sx in (-1, 1):
        b = skia.Path(); b.addOval(skia.Rect(sx * 10 - (90 if sx < 0 else 0), -170, sx * 10 + (0 if sx < 0 else 90), -110)); shape(c, b, '#F2C14E', LW * .8)


def ic_book(c, t, o):
    poly(c, [(-220, -120), (0, -90), (0, 150), (-220, 120)], '#F4EFE2', LW); poly(c, [(220, -120), (0, -90), (0, 150), (220, 120)], '#F4EFE2', LW)
    for i in range(5):
        c.drawLine(-190, -70 + i * 38, -30, -50 + i * 38, ink(4, '#8E8878')); c.drawLine(30, -50 + i * 38, 190, -70 + i * 38, ink(4, '#8E8878'))
    if o.get('text'): label(c, o['text'], 0, 220, fit_size(o['text'], 70, 480), CREAM, align='center', stroke=12)


def ic_phone(c, t, o): c.save(); c.scale(.5, .5); doc_phone(c, o, t); c.restore()


def ic_chart(c, t, o, up=True):
    rect(c, -200, -160, 200, 160, '#FBFAF2', LW, r=10)
    for i in range(4): c.drawLine(-170, -110 + i * 70, 170, -110 + i * 70, ink(2, '#C8C4B8'))
    pts = [(-160, 110), (-90, 60), (-30, 80), (40, -10), (100, 10), (160, -110)] if up else [(-160, -110), (-90, -40), (-30, -70), (40, 30), (100, 10), (160, 110)]
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    c.drawPath(p, ink(LW * 1.6, '#3E9A56' if up else RED))
    arrow(c, pts[-2], pts[-1], '#3E9A56' if up else RED, 34)


def arrow(c, a, b, v, size=34):
    ang = math.atan2(b[1] - a[1], b[0] - a[0]); ca, sa = math.cos(ang), math.sin(ang)
    tip = (b[0] + ca * size * .6, b[1] + sa * size * .6)
    poly(c, [tip, (b[0] - sa * size * .7, b[1] + ca * size * .7), (b[0] + sa * size * .7, b[1] - ca * size * .7)], v, LW * .6)


def ic_calendar(c, t, o):
    rect(c, -150, -150, 150, 160, '#F7F3E8', LW); rect(c, -150, -150, 150, -70, '#C8242C', LW)
    top, big = o.get('top', 'DAY'), o.get('text', '1')
    label(c, top, 0, -94, fit_size(top, 56, 260), CREAM, align='center', skew=0); label(c, big, 0, 110, fit_size(big, 150, 260), INK, align='center', skew=0, font=MARKER)


def ic_target(c, t, o):
    for r_, v in ((170, '#E8485A'), (120, '#FFFFFF'), (70, '#E8485A'), (26, '#FFFFFF')): circ(c, 0, 0, r_, v, LW * .8)
    line(c, 0, 0, 160, -160, LW * 1.4); poly(c, [(160, -160), (200, -150), (170, -200)], '#F2C14E', LW * .7)


def ic_car(c, t, o):
    v = o.get('color', '#C8242C'); body = skia.Path(); body.moveTo(-250, 60); body.lineTo(-240, -10); body.lineTo(-120, -30); body.lineTo(-60, -110); body.lineTo(110, -110)
    body.lineTo(180, -30); body.lineTo(250, -10); body.lineTo(250, 60); body.close(); shape(c, body, v, LW)
    poly(c, [(-40, -95), (40, -95), (40, -35), (-95, -35)], '#BFE3F2', LW * .7); poly(c, [(60, -95), (100, -95), (150, -35), (60, -35)], '#BFE3F2', LW * .7)
    for x in (-150, 150): circ(c, x, 60, 50, '#2A2A34', LW); circ(c, x, 60, 20, '#A0A4B0', LW * .6)


def ic_money(c, t, o): bills(c, 0, 0, -6)


def ic_marshmallow(c, t, o):
    n = int(o.get('n', 1)); oval(c, -200, 90, 200, 160, '#F4F4F8', LW)
    for k in range(n):
        x = (k - (n - 1) / 2) * 150; rect(c, x - 70, -40, x + 70, 110, '#FFFDF6', LW, r=34); oval(c, x - 70, -66, x + 70, -14, '#FFFFFF', LW)
        c.drawLine(x - 40, 0, x - 40, 80, ink(5, '#E8E2D6'))


def ic_shopping(c, t, o):
    poly(c, [(-130, -60), (130, -60), (110, 160), (-110, 160)], o.get('color', '#E8485A'), LW)
    for sx in (-1, 1):
        h = skia.Path(); h.addArc(skia.Rect(sx * 50 - 40, -130, sx * 50 + 40, -10), 180, 180); c.drawPath(h, ink(LW * 1.2))
    label(c, o.get('text', 'SALE'), 0, 70, 70, '#FFFFFF', font=MARKER, align='center', skew=0)


ICONS = dict(bulb=ic_bulb, brain=ic_brain, clock=ic_clock, moneybag=ic_moneybag, coins=ic_coins, house=ic_house, trophy=ic_trophy,
             heart=ic_heart, lock=ic_lock, hourglass=ic_hourglass, warning=ic_warning, laptop=ic_laptop, gift=ic_gift, book=ic_book,
             phone=ic_phone, chart_up=lambda c, t, o: ic_chart(c, t, o, True), chart_down=lambda c, t, o: ic_chart(c, t, o, False),
             calendar=ic_calendar, target=ic_target, car=ic_car, money=ic_money, marshmallow=ic_marshmallow, shopping=ic_shopping)


def draw_prop(c, name, x, y, s, t, rot=0, **o):
    if name not in ICONS: raise ValueError(f"unknown icon '{name}'. Options: {', '.join(sorted(ICONS))}")
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(s, s)
    c.drawOval(skia.Rect(-170, 150, 170, 200), fp((0, 0, 0), 40, blur=12)); ICONS[name](c, t, o); c.restore()
