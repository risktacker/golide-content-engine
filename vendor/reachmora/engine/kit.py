"""ReachMora 2D long-form kit: helpers, lighting, grade, puppet characters.
Flat cel-shaded round-head puppets with one uniform ink line, navy night lighting,
bloom, vignette. Everything is drawn with skia-python."""
import math, os, random
import numpy as np, skia

W, H, FPS = 1920, 1080, 30  # design space: everything is drawn in 1920x1080 coordinates
RES = int(os.environ.get("RM_RES", "1080"))  # output height: 1080 (final) or 720 (2.25x faster)
OW, OH = (1280, 720) if RES == 720 else (1920, 1080)
OS = OW / W  # design -> output scale
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = os.environ.get("RM_FONTS", os.path.join(ROOT, "fonts")) + os.sep


def _font(name):
    tf = skia.Typeface.MakeFromFile(FD + name)
    if tf is None: raise SystemExit(f"font missing: {FD + name}")
    return tf


FONT_HAND = _font("CaveatBrush-Regular.ttf")
KALAM = _font("Kalam-Bold.ttf")
MARKER = _font("PermanentMarker-Regular.ttf")
INK = (24, 22, 27); LW = 6.0
GOLD = '#F2C14E'; RED = '#C8242C'; LIME = '#B8F04A'; CREAM = '#FFF6DC'; SKY = '#7FC8F8'; PINK = '#FF6FA0'
NAMED = dict(lime=LIME, cream=CREAM, red=RED, gold=GOLD, sky=SKY, pink=PINK, white='#FFFFFF', green='#5FCB72', orange='#FF9A3C')


# ---------------------------------------------------------------- colour + easing
def C(rgb, a=255): return skia.Color(int(rgb[0]), int(rgb[1]), int(rgb[2]), int(max(0, min(255, a))))
def hx(h, a=255):
    h = NAMED.get(h, h).lstrip('#'); return C((int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)), a)
def col(v, a=255): return hx(v, a) if isinstance(v, str) else C(v, a)
def rgb(h):
    h = NAMED.get(h, h).lstrip('#'); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
def shade(h, k):  # k<1 darker, k>1 lighter
    r, g, b = rgb(h)
    if k <= 1: r, g, b = r * k, g * k, b * k
    else: r, g, b = r + (255 - r) * (k - 1), g + (255 - g) * (k - 1), b + (255 - b) * (k - 1)
    return '#%02X%02X%02X' % (int(min(255, r)), int(min(255, g)), int(min(255, b)))
def radial(cx, cy, r, colors, pos=None): return skia.GradientShader.MakeRadial(center=(cx, cy), radius=r, colors=colors, positions=pos)
def linear(x0, y0, x1, y1, colors, pos=None): return skia.GradientShader.MakeLinear(points=[(x0, y0), (x1, y1)], colors=colors, positions=pos)
def ease(u): u = min(max(u, 0), 1); return 0.5 - 0.5 * math.cos(math.pi * u)
def ease_out(u): u = min(max(u, 0), 1); return 1 - (1 - u) ** 3
def pop(u):  # 0 -> 1.15 -> 1
    if u <= 0: return 0.0
    if u >= 1: return 1.0
    return 1.15 * ease_out(u / 0.6) if u < 0.6 else 1.15 - 0.15 * ease((u - 0.6) / 0.4)
def back(u, k=1.9):  # snappy overshoot for pose changes
    u = min(max(u, 0.0), 1.0) - 1; return 1 + (k + 1) * u ** 3 + k * u ** 2
def lerp(a, b, k): return a + (b - a) * k
def K(t, t0, d): return min(max((t - t0) / d, 0.0), 1.0)
def blink(t, period=2.7, phase=0.0): return ((t + phase) % period) < 0.1


# ---------------------------------------------------------------- paints + shapes
def fp(v, a=255, blur=0, blend=None):
    p = skia.Paint(AntiAlias=True, Color=col(v, a))
    if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if blend: p.setBlendMode(blend)
    return p
def sp(shader, blend=None, blur=0):
    p = skia.Paint(AntiAlias=True); p.setShader(shader)
    if blend: p.setBlendMode(blend)
    if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p
def ink(w=LW, v=INK, a=255):
    p = skia.Paint(AntiAlias=True, Color=col(v, a)); p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(w)
    p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join); return p
def shape(c, path, fill, w=LW, v=INK):
    c.drawPath(path, fill if isinstance(fill, skia.Paint) else fp(fill))
    if w: c.drawPath(path, ink(w, v))
def rect(c, x0, y0, x1, y1, fill, w=LW, r=0, v=INK):
    p = skia.Path()
    if r: p.addRRect(skia.RRect.MakeRectXY(skia.Rect(x0, y0, x1, y1), r, r))
    else: p.addRect(skia.Rect(x0, y0, x1, y1))
    shape(c, p, fill, w, v); return p
def circ(c, x, y, r, fill, w=LW, v=INK): p = skia.Path(); p.addCircle(x, y, r); shape(c, p, fill, w, v); return p
def oval(c, x0, y0, x1, y1, fill, w=LW, v=INK): p = skia.Path(); p.addOval(skia.Rect(x0, y0, x1, y1)); shape(c, p, fill, w, v); return p
def line(c, x0, y0, x1, y1, w=LW, v=INK, a=255): c.drawLine(x0, y0, x1, y1, ink(w, v, a))
def poly(c, pts, fill, w=LW, v=INK):
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    p.close(); shape(c, p, fill, w, v); return p
def text_w(s, size, font=None): return skia.Font(font or KALAM, size).measureText(s)
def label(c, s, x, y, size, color, font=None, align='left', stroke=0, stroke_col=INK, skew=-0.16, alpha=1.0, rot=0.0):
    f = skia.Font(font or KALAM, size); w = f.measureText(s)
    ox = -w / 2 if align == 'center' else -w if align == 'right' else 0
    c.save(); c.translate(x, y); c.rotate(rot); c.skew(skew, 0)
    if stroke: c.drawString(s, ox, 0, f, ink(stroke, stroke_col, 255 * alpha))
    c.drawString(s, ox, 0, f, fp(color, 255 * alpha)); c.restore(); return w
def fit_size(s, size, max_w, font=None):
    w = text_w(s, size, font); return size if w <= max_w else size * max_w / w
def wrap(s, size, max_w, font=None):
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if cur and text_w(t, size, font) > max_w: lines.append(cur); cur = w_
        else: cur = t
    if cur: lines.append(cur)
    return lines


# ---------------------------------------------------------------- lighting + grade
def night(c, lights, ambient='#4C5CA0'):
    """Multiply darkness over everything drawn so far, with soft holes for lights.
    lights: ('pool',x,y,r,a) | ('oval',x,y,rx,ry,a) | ('path',skia.Path,a,blur)"""
    p = skia.Paint(); p.setBlendMode(skia.BlendMode.kMultiply); c.saveLayer(None, p); c.drawPaint(fp(ambient))
    for L in lights:
        if L[0] == 'pool':
            _, x, y, r, a = L
            c.drawCircle(x, y, r, sp(radial(x, y, r, [C((0, 0, 0), 255 * a), C((0, 0, 0), 255 * a * .75), C((0, 0, 0), 0)], [0, .5, 1]), blend=skia.BlendMode.kDstOut))
        elif L[0] == 'oval':
            _, x, y, rx, ry, a = L; c.save(); c.translate(x, y); c.scale(1, ry / rx)
            c.drawCircle(0, 0, rx, sp(radial(0, 0, rx, [C((0, 0, 0), 255 * a), C((0, 0, 0), 255 * a * .7), C((0, 0, 0), 0)], [0, .55, 1]), blend=skia.BlendMode.kDstOut)); c.restore()
        else:
            _, path, a, blur = L; c.drawPath(path, fp((0, 0, 0), 255 * a, blur=blur, blend=skia.BlendMode.kDstOut))
    c.restore()
def add_light(c, x, y, r, v, a):
    c.drawCircle(x, y, r, sp(radial(x, y, r, [col(v, a), col(v, a * .4), col(v, 0)], [0, .5, 1]), blend=skia.BlendMode.kPlus))
def cone_path(x, y, top_w, bot_w, length, lean=0):
    p = skia.Path(); p.moveTo(x - top_w / 2, y); p.lineTo(x + top_w / 2, y); p.lineTo(x + lean + bot_w / 2, y + length); p.lineTo(x + lean - bot_w / 2, y + length); p.close(); return p
def blur_begin(c, sigma):  # depth blur for everything until c.restore()
    p = skia.Paint(); p.setImageFilter(skia.ImageFilters.Blur(sigma, sigma)); c.saveLayer(None, p)
def vignette(c, strength=0.64, inner=.42):
    if strength <= 0: return
    c.drawRect(skia.Rect(0, 0, W, H), sp(radial(W / 2, H / 2, W * .74, [C((0, 0, 0), 0), C((0, 0, 0), 0), C((2, 3, 12), 255 * strength)], [0, inner, 1])))
def _sat(s, contrast, lift):
    lr, lg, lb = 0.2126, 0.7152, 0.0722
    m = [lr * (1 - s) + s, lg * (1 - s), lb * (1 - s), lr * (1 - s), lg * (1 - s) + s, lb * (1 - s), lr * (1 - s), lg * (1 - s), lb * (1 - s) + s]
    out = []
    for r in range(3): out += [m[r * 3 + i] * contrast for i in range(3)] + [0, lift]
    return out + [0, 0, 0, 1, 0]
# ---------------------------------------------------------------- frame buffers + numpy post (fast on every platform)
# Full-screen gradients, blend modes and colour filters are very slow in CPU skia on some builds, so every
# full-frame pass (lighting multiply, glow add, grade, bloom, vignette, whip blur) runs in numpy instead.
# Surfaces are premultiplied native-format (N32) numpy buffers: drawing is zero-copy and image blits stay fast.
N32 = skia.kN32_ColorType
BGR = N32 == skia.kBGRA_8888_ColorType
PIX_FMT = 'bgra' if BGR else 'rgba'
LUM = np.array([0.0722, 0.7152, 0.2126] if BGR else [0.2126, 0.7152, 0.0722], np.float32)
LINEAR = skia.SamplingOptions(skia.FilterMode.kLinear)


def np_surface(w=None, h=None):
    w = OW if w is None else w; h = OH if h is None else h
    a = np.zeros((h, w, 4), np.uint8); return a, skia.Surface(a, colorType=N32, alphaType=skia.kPremul_AlphaType)


def np_image(a): return skia.Image.fromarray(np.ascontiguousarray(a), colorType=N32, alphaType=skia.kPremul_AlphaType)


def multiply_into(buf, m):
    x = buf[..., :3].astype(np.uint16); x *= m[..., :3]; x += 127; x //= 255; buf[..., :3] = x


def add_into(buf, g):
    x = buf[..., :3].astype(np.uint16); x += g[..., :3]; np.minimum(x, 255, out=x); buf[..., :3] = x


_VIG = {}


def _vig_map(strength, inner=.42):
    k = (round(strength, 3), inner)
    if k not in _VIG:
        yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32); r = np.hypot(xx - OW / 2, yy - OH / 2) / (OW * .74)
        _VIG[k] = (strength * np.clip((r - inner) / (1 - inner), 0, 1))[..., None].astype(np.float32)
    return _VIG[k]


VCOL = (np.array([12, 3, 2] if BGR else [2, 3, 12], np.float32) / 255)
_POST = {}


_LUT = {}


def _lut(contrast, lift):
    k = (contrast, lift)
    if k not in _LUT: _LUT[k] = np.clip((np.arange(256) / 255 * contrast + lift) * 255 + .5, 0, 255).astype(np.uint8)
    return _LUT[k]


def _vig16(strength):
    k = ('v16', round(strength, 3))
    if k not in _VIG: _VIG[k] = np.round((1 - _vig_map(strength)) * 256).astype(np.uint16)
    return _VIG[k]


def finish(buf, bloom=0.40, vig=0.64, contrast=0.97, lift=0.012):
    """Grade (contrast/lift LUT) + quarter-res bloom (screen blend) + vignette, in place, integer math (~90 ms at 1080p)."""
    from scipy.ndimage import gaussian_filter
    if 'small' not in _POST: _POST['small'] = np_surface(OW // 4, OH // 4); _POST['up'] = np_surface(OW, OH)
    if bloom > 0:
        sa, ss = _POST['small']; sc_ = ss.getCanvas(); sc_.save(); sc_.scale(.25, .25); sc_.drawImage(np_image(buf), 0, 0, LINEAR); sc_.restore()
        s = sa[..., :3].astype(np.float32) * (1.7 / 255) - .78; np.clip(s, 0, 1, out=s); s = gaussian_filter(s, (5 * OS, 5 * OS, 0))
        sa[..., :3] = (s * (255 * bloom)).astype(np.uint8); sa[..., 3] = 255
        ua, us = _POST['up']; uc = us.getCanvas(); uc.save(); uc.scale(4, 4); uc.drawImage(np_image(sa), 0, 0, LINEAR); uc.restore()
    x = _lut(contrast, lift)[buf[..., :3]].astype(np.uint16)
    if bloom > 0:
        b = ua[..., :3].astype(np.uint16); xb = x * b; xb += 255; xb >>= 8; x += b; x -= xb  # screen: x + b - x*b/255
    if vig > 0: x *= _vig16(vig); x >>= 8
    np.minimum(x, 255, out=x); buf[..., :3] = x


def hblur(buf, sig):
    """Fast horizontal motion blur for whip pans (box blur ~ gaussian sigma)."""
    k = max(1, int(sig * 1.2 * OS)); x = buf[..., :3].astype(np.float32); w = buf.shape[1]
    pad = np.concatenate([np.repeat(x[:, :1], k + 1, 1), x, np.repeat(x[:, -1:], k, 1)], 1)
    cs = np.cumsum(pad, axis=1); out = (cs[:, 2 * k + 1:] - cs[:, :-2 * k - 1]) / (2 * k + 1)
    buf[..., :3] = np.clip(out[:, :w], 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- puppet character
BODY_TOP, BODY_BOT, HEAD_R = -345, -128, 100
HEAD_CY = BODY_TOP - 74
SHOULDER = (-56, BODY_TOP + 54)
ARM = {  # left arm: (elbow, hand, show_hand); the right arm is mirrored
    'down': ((-90, -235), (-96, -168), True), 'pocket': ((-96, -232), (-70, -176), False),
    'hip': ((-128, -238), (-84, -190), True), 'present': ((-128, -306), (-208, -338), True),
    'gesture': ((-136, -262), (-152, -352), True), 'chin': ((-128, -262), (-62, -322), True),
    'hat': ((-140, -400), (-104, -482), True), 'hold': ((-96, -236), (-44, -214), True),
    'push': ((-120, -270), (-190, -262), True), 'up': ((-138, -392), (-150, -500), True),
    'shrug': ((-132, -246), (-184, -312), True), 'cross': ((-70, -236), (40, -262), True),
    'wave': ((-150, -330), (-176, -446), True), 'head': ((-150, -380), (-86, -470), True),
    'point': ((-150, -300), (-236, -306), True)}
POSES = dict(idle=('down', 'down'), present=('down', 'present'), explain=('gesture', 'down'), think=('down', 'chin'),
             pockets=('pocket', 'pocket'), celebrate=('up', 'up'), shrug=('shrug', 'shrug'), point=('down', 'point'),
             hips=('hip', 'hip'), hold=('hold', 'hold'), tiphat=('down', 'hat'), wave=('down', 'wave'), arms_crossed=('cross', 'cross'),
             facepalm=('down', 'head'), stressed=('head', 'head'), push=('down', 'push'), present_left=('present', 'down'))
EMOTIONS = {  # eyes, mouth, brow, brow_tilt, extras
    'neutral': ('dot', 'smile', 0.0, 0.0, {}), 'calm': ('dot', 'flat', 0.0, 0.0, {}),
    'happy': ('closed', 'open', 0.3, 0.0, {}), 'smile': ('dot', 'smile', 0.2, 0.0, {}),
    'smug': ('half', 'smirk', 0.9, 0.0, {}), 'shocked': ('wide', 'o', 1.0, 0.0, {}),
    'nervous': ('wide', 'flat', 1.0, -0.8, {'sweat': True}), 'sad': ('half', 'flat', 0.0, -0.9, {}),
    'angry': ('dot', 'flat', 0.2, 0.9, {}), 'thinking': ('dot', 'flat', 0.5, -0.3, {'pupil': -1}),
    'excited': ('wide', 'open', 1.0, 0.0, {'sparkle': True}), 'tired': ('half', 'flat', -0.2, -0.5, {}),
    'confident': ('half', 'smile', 0.5, 0.0, {}), 'worried': ('dot', 'o', 0.8, -0.8, {}),
    'embarrassed': ('half', 'flat', 0.0, -0.9, {'sweat': True}), 'greedy': ('half', 'smirk', 0.9, 0.3, {'sparkle': True})}
SKINS = dict(light=('#F1CFA8', '#D6AE84'), fair=('#EBC79C', '#CFA677'), tan=('#E6BE8E', '#C99F70'),
             olive=('#C99C6E', '#A97E52'), brown=('#A8754D', '#8A5C38'), dark=('#7A4E32', '#603B24'))


def make_look(d):
    """Fill a cast look with defaults. Keys: skin (preset or hex), outfit suit|hoodie|tshirt|dress|sweater,
    color, shirt, tie, bowtie, hair slick|short|bun|long|curly|bald|none, hair_col, glasses, moustache,
    beard, hat fedora|cap|none, hat_col."""
    d = dict(d or {}); sk = d.get('skin', 'tan')
    if sk in SKINS:
        d.setdefault('skin_d', SKINS[sk][1]); d['skin'] = SKINS[sk][0]
    else:
        d['skin'] = sk; d.setdefault('skin_d', shade(sk, .84))
    d.setdefault('outfit', 'suit'); d.setdefault('color', d.get('suit', '#3B4660'))
    d['suit'] = d['color']; d.setdefault('suit_d', shade(d['color'], .74))
    d.setdefault('shirt', '#F4EFE2'); d.setdefault('tie', '#A8232B'); d.setdefault('hair', 'short')
    d.setdefault('hair_col', '#1C1B22'); d.setdefault('hat_col', '#2E2E38'); d.setdefault('hat_band', '#7E1C24')
    if d.get('hat') is True: d['hat'] = 'fedora'
    return d


def _arm(spec):  # 'name' or ('from', 'to', k) blended with overshoot
    if isinstance(spec, str): return ARM[spec]
    a, b, k = spec; k = back(k, 1.6); ea, ha, sa = ARM[a]; eb, hb, sb = ARM[b]
    return (lerp(ea[0], eb[0], k), lerp(ea[1], eb[1], k)), (lerp(ha[0], hb[0], k), lerp(ha[1], hb[1], k)), (sb if k > .5 else sa)


def _hair_cap(c, R, face, colr, lw, fringe=-62):
    fs = face * 14; hp = skia.Path(); hp.moveTo(-R - 4, -14)
    hp.arcTo(skia.Rect(-R - 4, -R - 6, R + 4, R + 4), 188, 164, False)
    hp.cubicTo(R - 8, -44, 46 + fs, fringe - 8, fs, fringe); hp.cubicTo(-44 + fs, fringe + 4, -R + 6, -40, -R - 4, -14); hp.close()
    shape(c, hp, colr, lw); return hp


def draw_char(c, x, y, s, spec, face=0.0, eyes='dot', mouth='smile', brow=0.0, brow_tilt=0.0, arms=('down', 'down'),
              tilt=0.0, bob=0.0, squash=0.0, sweat=-1.0, light=-1, rim=None, hat=None, legs=None, pupil=0.0, sparkle=0.0):
    """x,y = feet. s=1 -> head radius 100 px (s=1 wide shot, s~2.15 close-up with feet at y~1390).
    face -1..1 = 3/4 turn. light -1 = key from left. eyes: dot/half/wide/closed. mouth: smile/smirk/flat/o/mid/open."""
    lw = max(5.2, 4.0 / s); R = HEAD_R; outfit = spec.get('outfit', 'suit')
    hat = spec.get('hat') if hat is None else hat
    c.save(); c.translate(x, y); c.scale(s, s)
    for (hx0, fx, lift) in (legs or ((-24, 0, 0), (24, 0, 0))):
        c.drawLine(hx0, BODY_BOT - 8, hx0 + fx, -lift, ink(lw))
    c.translate(0, -bob); c.scale(1 + squash * .6, 1 - squash)
    if outfit == 'dress':
        sk = skia.Path(); sk.moveTo(-70, BODY_BOT - 70); sk.lineTo(70, BODY_BOT - 70); sk.lineTo(104, BODY_BOT + 30); sk.quadTo(0, BODY_BOT + 46, -104, BODY_BOT + 30); sk.close()
        shape(c, sk, spec['suit'], lw)
    if spec.get('hair') == 'long':
        lh = skia.Path(); lh.addRRect(skia.RRect.MakeRectXY(skia.Rect(-R - 14, HEAD_CY - 40, R + 14, HEAD_CY + 150), 60, 60)); shape(c, lh, spec['hair_col'], lw)
    body = skia.Path(); body.addRRect(skia.RRect.MakeRectXY(skia.Rect(-84, BODY_TOP, 84, BODY_BOT), 66, 72))
    c.drawPath(body, fp(spec['suit'])); c.save(); c.clipPath(body, doAntiAlias=True)
    sh = skia.Path(body); sh.offset(light * 16, -5); c.drawPath(skia.Op(body, sh, skia.PathOp.kDifference_PathOp), fp(spec['suit_d']))
    if outfit == 'suit':
        v = skia.Path(); v.moveTo(-34, BODY_TOP - 4); v.lineTo(0, BODY_TOP + 96); v.lineTo(34, BODY_TOP - 4); v.close(); c.drawPath(v, fp(spec['shirt']))
        if spec.get('bowtie'):
            by = BODY_TOP + 40; bt = skia.Path(); bt.moveTo(0, by); bt.lineTo(-24, by - 14); bt.lineTo(-24, by + 14); bt.close()
            bt.moveTo(0, by); bt.lineTo(24, by - 14); bt.lineTo(24, by + 14); bt.close(); shape(c, bt, spec['tie'], lw * .75); circ(c, 0, by, 5, spec['tie'], lw * .7)
        elif spec.get('tie') not in (None, 'none'):
            poly(c, [(-9, BODY_TOP + 24), (9, BODY_TOP + 24), (13, BODY_TOP + 82), (0, BODY_TOP + 98), (-13, BODY_TOP + 82)], spec['tie'], lw * .75)
        for sx in (-1, 1):
            lp = skia.Path(); lp.moveTo(sx * 36, BODY_TOP - 2); lp.lineTo(sx * 2, BODY_TOP + 98); lp.lineTo(sx * 2, BODY_BOT); c.drawPath(lp, ink(lw * .75))
            c.drawLine(sx * 22, BODY_TOP + 58, sx * 40, BODY_TOP + 44, ink(lw * .6))
    elif outfit == 'hoodie':
        hood = skia.Path(); hood.moveTo(-60, BODY_TOP - 2); hood.quadTo(0, BODY_TOP + 44, 60, BODY_TOP - 2); c.drawPath(hood, ink(lw * .8))
        for sx in (-1, 1): c.drawLine(sx * 16, BODY_TOP + 20, sx * 18, BODY_TOP + 84, ink(lw * .55, spec['shirt']))
        pk = skia.Path(); pk.moveTo(-48, BODY_BOT - 6); pk.lineTo(-38, BODY_BOT - 66); pk.lineTo(38, BODY_BOT - 66); pk.lineTo(48, BODY_BOT - 6); c.drawPath(pk, ink(lw * .6))
    elif outfit in ('tshirt', 'dress', 'sweater'):
        nk = skia.Path(); nk.addArc(skia.Rect(-34, BODY_TOP - 30, 34, BODY_TOP + 26), 20, 140); c.drawPath(nk, ink(lw * .7))
        if outfit == 'sweater':
            for yy in (BODY_BOT - 22,): c.drawLine(-84, yy, 84, yy, ink(lw * .6))
    if spec.get('hanky'): poly(c, [(30, BODY_TOP + 96), (52, BODY_TOP + 92), (48, BODY_TOP + 76), (40, BODY_TOP + 86), (33, BODY_TOP + 76)], spec['hanky'], lw * .55)
    c.restore(); c.drawPath(body, ink(lw))
    for side, a in ((-1, arms[0]), (1, arms[1])):
        e, h, show = _arm(a); m = 1 if side < 0 else -1
        sx, sy = SHOULDER[0] * m, SHOULDER[1]; ex, ey, hx_, hy_ = e[0] * m, e[1], h[0] * m, h[1]
        ap = skia.Path(); ap.moveTo(sx, sy); ap.quadTo(1.35 * ex - .175 * (sx + hx_), 1.35 * ey - .175 * (sy + hy_), hx_, hy_); c.drawPath(ap, ink(lw))
        if show: circ(c, hx_, hy_, 13, spec['skin'], lw * .8)
    c.save(); c.translate(0, HEAD_CY); c.rotate(tilt)
    head = skia.Path(); head.addCircle(0, 0, R); hair = spec.get('hair', 'short')
    if hair == 'bald':
        for sx in (-1, 1):
            tf = skia.Path(); tf.moveTo(sx * 84, -44)
            for (px, py) in ((112, -34), (98, -18), (118, -4), (100, 10), (112, 26), (86, 34)): tf.lineTo(sx * px, py)
            tf.close(); shape(c, tf, spec.get('hair_col', '#8A8A92'), lw * .8)
    if hair == 'curly':
        for i in range(11):
            a = math.radians(165 + i * 21); circ(c, (R + 4) * math.cos(a), (R + 4) * math.sin(a) + 6, 34, spec['hair_col'], lw * .8)
    if hair == 'bun': circ(c, 0, -R - 26, 44, spec['hair_col'], lw)
    c.drawPath(head, fp(spec['skin'])); c.save(); c.clipPath(head, doAntiAlias=True)
    lit = skia.Path(head); lit.offset(light * 7, -17); c.drawPath(skia.Op(head, lit, skia.PathOp.kDifference_PathOp), fp(spec['skin_d']))
    if rim: rm = skia.Path(head); rm.offset(-light * 11, 4); c.drawPath(skia.Op(head, rm, skia.PathOp.kDifference_PathOp), fp(rim, 215))
    c.restore()
    if hair == 'slick':
        hp = skia.Path(); hp.moveTo(-R - 4, -4); hp.arcTo(skia.Rect(-R - 4, -R - 5, R + 4, R + 3), 181, 178, False); fs = face * 14
        hp.cubicTo(R - 6, -40, 56 + fs, -70, 4 + fs, -62); hp.cubicTo(-36 + fs, -58, -78, -44, -R - 4, -4); hp.close()
        shape(c, hp, spec['hair_col'], lw)
        shn = skia.Path(); shn.addArc(skia.Rect(-R + 20, -R + 14, R - 20, R - 14), 208 if light < 0 else 282, 50); c.drawPath(shn, ink(lw * 1.3, (92, 96, 122)))
    elif hair in ('short', 'bun', 'long', 'curly'):
        _hair_cap(c, R, face, spec['hair_col'], lw, -58 if hair != 'curly' else -66)
    c.drawPath(head, ink(lw))
    if hat == 'fedora':
        crown = skia.Path(); crown.moveTo(-R + 6, -56); crown.cubicTo(-R - 2, -R - 82, R + 2, -R - 82, R - 6, -56); crown.close()
        shape(c, crown, spec['hat_col'], lw); c.save(); c.clipPath(crown, doAntiAlias=True)
        c.drawRect(skia.Rect(-R, -86, R, -56), fp(spec['hat_band'])); c.drawLine(-R, -86, R, -86, ink(lw * .7)); c.restore()
        c.drawPath(crown, ink(lw)); oval(c, -R - 40, -70, R + 40, -40, spec['hat_col'], lw)
    elif hat == 'cap':
        cp = skia.Path(); cp.moveTo(-R - 2, -40); cp.arcTo(skia.Rect(-R - 2, -R - 10, R + 2, R), 182, 176, False); cp.close(); shape(c, cp, spec['hat_col'], lw)
        d = 1 if face >= 0 else -1; br = skia.Path(); br.moveTo(d * 10, -44); br.quadTo(d * (R + 70), -52, d * (R + 76), -30); br.lineTo(d * 10, -34); br.close(); shape(c, br, spec['hat_col'], lw)
    fx = face * 40; eyy = -6
    for ex0 in (-30, 30):
        ex = ex0 + fx; far = (face > 0 and ex0 > 0) or (face < 0 and ex0 < 0); sq = 1 - .3 * abs(face) if far else 1.0
        if eyes == 'wide':
            oval(c, ex - 17 * sq, eyy - 17, ex + 17 * sq, eyy + 17, '#FBFBF7', lw * .7)
            c.drawOval(skia.Rect(ex - 5.5 * sq + pupil * 6, eyy - 5.5, ex + 5.5 * sq + pupil * 6, eyy + 5.5), fp(INK))
        elif eyes == 'closed':
            e = skia.Path(); e.moveTo(ex - 11 * sq, eyy); e.quadTo(ex, eyy + 9, ex + 11 * sq, eyy); c.drawPath(e, ink(lw * .8))
        elif eyes == 'half':
            c.save(); c.clipRect(skia.Rect(ex - 20, eyy - 3, ex + 20, eyy + 20)); c.drawOval(skia.Rect(ex - 6.5 * sq, eyy - 9, ex + 6.5 * sq, eyy + 9), fp(INK)); c.restore()
            c.drawLine(ex - 13 * sq, eyy - 4, ex + 13 * sq, eyy - 4, ink(lw * .8))
        else:
            py = -4 if pupil < 0 and eyes == 'dot' and abs(pupil) > .5 else 0
            c.drawOval(skia.Rect(ex - 5.5 * sq, eyy - 8 + py, ex + 5.5 * sq, eyy + 8 + py), fp(INK)); c.drawCircle(ex + 1.5, eyy - 3 + py, 1.8, fp((255, 255, 255), 220))
        inner = 1 if ex0 < 0 else -1; by = eyy - 29 - brow * 9
        c.drawLine(ex - 13 * sq, by + (brow_tilt * 7 if inner < 0 else -brow_tilt * 7), ex + 13 * sq, by + (brow_tilt * 7 if inner > 0 else -brow_tilt * 7), ink(lw * .78))
    if spec.get('glasses'):
        for ex0 in (-30, 30):
            ex = ex0 + fx; far = (face > 0 and ex0 > 0) or (face < 0 and ex0 < 0); sq = 1 - .3 * abs(face) if far else 1.0
            g = skia.Path(); g.addOval(skia.Rect(ex - 24 * sq, eyy - 24, ex + 24 * sq, eyy + 24)); c.drawPath(g, fp((225, 240, 255), 55)); c.drawPath(g, ink(lw * .7))
        c.drawLine(fx - 7, eyy - 3, fx + 7, eyy - 3, ink(lw * .7))
    mx, my = face * 34, 42
    if spec.get('beard'):
        bd = skia.Path(); bd.moveTo(-R + 6, 6); bd.quadTo(-R + 4, R - 4, mx, R + 18); bd.quadTo(R - 4, R - 4, R - 6, 6)
        bd.quadTo(R * .5, 40, mx + 26, 30); bd.quadTo(mx, 22, mx - 26, 30); bd.quadTo(-R * .5, 40, -R + 6, 6); bd.close()
        shape(c, bd, spec['hair_col'], lw * .8)
    if spec.get('moustache'):
        mu = skia.Path(); mu.moveTo(mx, my - 20)
        mu.cubicTo(mx - 12, my - 28, mx - 30, my - 22, mx - 40, my - 30); mu.cubicTo(mx - 30, my - 10, mx - 12, my - 12, mx, my - 15)
        mu.cubicTo(mx + 12, my - 12, mx + 30, my - 10, mx + 40, my - 30); mu.cubicTo(mx + 30, my - 22, mx + 12, my - 28, mx, my - 20); mu.close()
        c.drawPath(mu, fp(spec['hair_col']))
    if mouth == 'smile': m = skia.Path(); m.moveTo(mx - 17, my - 2); m.quadTo(mx, my + 13, mx + 17, my - 2); c.drawPath(m, ink(lw * .8))
    elif mouth == 'smirk':
        d = 1 if face >= 0 else -1; m = skia.Path(); m.moveTo(mx - 15 * d, my + 3); m.quadTo(mx + 4 * d, my + 12, mx + 20 * d, my - 6); c.drawPath(m, ink(lw * .8))
    elif mouth == 'flat': c.drawLine(mx - 12, my + 2, mx + 12, my + 2, ink(lw * .8))
    elif mouth == 'o': oval(c, mx - 8, my - 9, mx + 8, my + 11, '#5A1A1E', lw * .7)
    elif mouth == 'mid': oval(c, mx - 12, my - 4, mx + 12, my + 10, '#5A1A1E', lw * .7)
    elif mouth == 'open':
        mp = skia.Path(); mp.moveTo(mx - 20, my - 5); mp.lineTo(mx + 20, my - 5); mp.cubicTo(mx + 19, my + 24, mx - 19, my + 24, mx - 20, my - 5); mp.close()
        c.drawPath(mp, fp('#5A1A1E')); c.save(); c.clipPath(mp, doAntiAlias=True)
        c.drawRect(skia.Rect(mx - 22, my - 6, mx + 22, my + 2), fp('#FAFAF4')); c.drawOval(skia.Rect(mx - 11, my + 9, mx + 11, my + 26), fp('#D05860')); c.restore()
        c.drawPath(mp, ink(lw * .7))
    if sparkle > 0:
        k = pop(sparkle) * (1 if sparkle < 1 else max(0, 2 - sparkle)); sx_, sy_ = mx + 26 * (1 if face >= 0 else -1), my - 8; st = skia.Path()
        for i in range(8):
            r_ = (20 if i % 2 == 0 else 5) * k; a = i * math.pi / 4; (st.moveTo if i == 0 else st.lineTo)(sx_ + r_ * math.cos(a), sy_ + r_ * math.sin(a))
        st.close(); c.drawPath(st, fp('#FFFFFF'))
    if sweat >= 0:
        sx0, sy0 = (-1 if face > 0 else 1) * 62, -66 + 30 * (sweat % 1.0)
        d = skia.Path(); d.moveTo(sx0, sy0 - 19); d.cubicTo(sx0 + 12, sy0 - 3, sx0 + 11, sy0 + 10, sx0, sy0 + 10); d.cubicTo(sx0 - 11, sy0 + 10, sx0 - 12, sy0 - 3, sx0, sy0 - 19); d.close()
        shape(c, d, '#8FC8EE', lw * .7)
    c.restore(); c.restore()


def walk_legs(phase, stride=46, lift=20):  # legs=walk_legs((t-t0)*11) with bob=7*abs(sin(phase))
    a = math.sin(phase)
    return ((-10, a * stride, max(0, math.cos(phase)) * lift), (10, -a * stride, max(0, -math.cos(phase)) * lift))
