"""Text and graphic effects: pop labels, stamps, lower thirds, location tags, typed cards, bubbles."""
import math
import skia
from .kit import *


def poplabel(c, s, x, y, u, size=120, v=LIME, rot=-5, font=None, stroke=15, max_w=900):
    """u = seconds since the label's cue (<=0 hidden)."""
    if u <= 0: return
    size = fit_size(s, size, max_w, font); pu = pop(min(u / .3, 1))
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(pu, pu)
    label(c, s, 0, 0, size, v, font=font, align='center', stroke=stroke if font is None else 0, skew=-0.14 if font is None else 0); c.restore()


def stamp(c, txt, x, y, u, rot=-10, size=150, v=RED, max_w=1100):
    """u = seconds since the stamp's cue / 0.9."""
    if u <= 0: return
    size = fit_size(txt, size, max_w, MARKER)
    sc = 2.6 - 1.6 * ease_out(min(u * 5, 1)); a = min(u * 8, 1); w = text_w(txt, size, MARKER)
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(sc, sc)
    for inset, wd in ((0, 13), (18, 5)):
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-w / 2 - 50 + inset, -size * .98 + inset, w / 2 + 50 - inset, size * .36 - inset), 16, 16), ink(wd, v, 255 * a))
    label(c, txt, 0, 0, size, v, font=MARKER, align='center', skew=0, alpha=a); c.restore()


def tag(c, s, u, x=70, y=H - 86):
    a = ease_out(u * 3)
    if a <= 0: return
    w = text_w(s, 44); c.save(); c.translate(-50 * (1 - a), 0)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x, y - 52, x + w + 64, y + 18), 10, 10), fp((10, 12, 26), 205 * a))
    c.drawRect(skia.Rect(x, y - 52, x + 10, y + 18), fp(GOLD, 255 * a)); label(c, s, x + 34, y, 44, CREAM, alpha=a, skew=-0.12); c.restore()


def lower_third(c, name, sub, u, x=90, y=930):
    if u <= 0: return
    a = back(min(u * 2.6, 1), 1.4); w = max(text_w(name, 76), text_w(sub or '', 40), 380)
    c.save(); c.translate(x, y); c.scale(a, a); rect(c, 0, -74, w + 84, 74, (12, 14, 28), LW * .8)
    c.drawRect(skia.Rect(3, -71, 19, 71), fp(GOLD)); label(c, name, 44, 4, 76, CREAM, skew=-0.12)
    if sub: label(c, sub, 46, 54, 40, GOLD, skew=-0.12)
    c.restore()


def typed(c, text, t, t0, dur, size=140, color='#FFFFFF', y=None, max_w=1640, font=None):
    """White handwriting typed word by word between t0 and t0+dur, centred, wraps to 2-3 lines."""
    font = font or FONT_HAND; lines = wrap(text, size, max_w, font)
    while len(lines) > 3 and size > 60: size *= .88; lines = wrap(text, size, max_w, font)
    words = text.split(); tot = sum(len(w) + 1 for w in words); acc = 0; k = 0
    for w in words:
        if t >= t0 + dur * acc / tot - .04: k += 1
        acc += len(w) + 1
    f = skia.Font(font, size); lh = size * 1.12; y0 = (H / 2 if y is None else y) - lh * (len(lines) - 1) / 2 + size * .32; shown = 0
    for i, ln in enumerate(lines):
        lw_ = ln.split(); n = max(0, min(len(lw_), k - shown)); shown += len(lw_)
        if n: c.drawString(" ".join(lw_[:n]), W / 2 - f.measureText(ln) / 2, y0 + i * lh, f, fp(color))


def ring(c, x, y, rx, ry, u, v=RED, w=14):
    if u <= 0: return
    p = skia.Path(); p.addArc(skia.Rect(x - rx, y - ry, x + rx, y + ry), -110, 352 * ease(min(u, 1))); c.drawPath(p, ink(w, v))


def bubble(c, x, y, w, h, u, text=None, icon=None, tail=(0, 0), t=0.0, thought=True):
    """Thought/speech bubble centred at x,y; tail points to (tail) in absolute coords."""
    if u <= 0: return
    from .props import draw_prop
    k = back(min(u / .35, 1), 1.5); c.save(); c.translate(x, y); c.scale(k, k)
    if thought:
        for i, r_ in enumerate((14, 22)):
            tx = lerp(tail[0] - x, -w * .2, .35 + i * .3); ty = lerp(tail[1] - y, h * .4, .35 + i * .3); circ(c, tx, ty, r_, '#FFFFFF', LW * .7)
        p = skia.Path()
        for i in range(10):
            a = i * math.pi / 5; p.addOval(skia.Rect(math.cos(a) * w * .42 - w * .18, math.sin(a) * h * .38 - h * .2, math.cos(a) * w * .42 + w * .18, math.sin(a) * h * .38 + h * .2))
        p.addOval(skia.Rect(-w * .44, -h * .4, w * .44, h * .4)); p = skia.Op(p, skia.Path(), skia.PathOp.kUnion_PathOp)
    else:
        p = skia.Path(); p.addRRect(skia.RRect.MakeRectXY(skia.Rect(-w / 2, -h / 2, w / 2, h / 2), 40, 40))
        tl = skia.Path(); tl.moveTo(-30, h / 2 - 10); tl.lineTo(tail[0] - x, tail[1] - y); tl.lineTo(30, h / 2 - 10); tl.close(); p = skia.Op(p, tl, skia.PathOp.kUnion_PathOp)
    shape(c, p, '#FFFFFF', LW)
    if icon: draw_prop(c, icon, 0, -10, min(w, h) / 520, t)
    elif text:
        size = 64; lines = wrap(text, size, w * .72)
        while len(lines) > 3 and size > 34: size *= .88; lines = wrap(text, size, w * .72)
        for i, ln in enumerate(lines): label(c, ln, 0, (i - (len(lines) - 1) / 2) * size * 1.1 + size * .32, size, INK, align='center', skew=-0.08)
    c.restore()


def number_badge(c, n, x, y, u, v=GOLD):
    if u <= 0: return
    k = back(min(u / .35, 1), 1.6); c.save(); c.translate(x, y); c.scale(k, k); c.rotate(-6)
    circ(c, 0, 0, 120, v, LW * 1.2); label(c, f"#{n}", 0, 40, 120, INK, font=MARKER, align='center', skew=0); c.restore()
