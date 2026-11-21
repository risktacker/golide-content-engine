"""Stickman thumbnails (owner 2026-11-17): the thumbnail of a Stickman video is drawn in the video's own look, with
the ReachMora kit's own puppets (vendor/reachmora/engine/kit.py draw_char, unchanged) dressed like the people in
the story (hair, glasses, clothes; never a drawn face), the story's real logos (Simple Icons, vector/logos.py) and
the main person's name on a red banner. Modelled on the thumbnails of the Stickman videos that work (the
investigation board of "Jensen Huang Scandal Explained Like You're 5"). Drawn in code: no image model, $0.

Designs: "board" (an investigation board: the main person's big card in the middle, the other people and the
logos pinned round it, joined by red strings, a detective in front) for stories about people and what they did;
"versus" (two people face to face over a big word or number) for comparisons; "reaction" (one shocked person and
one huge number or object) for a single event. Every piece of text is measured: none touches another or leaves
the frame (owner 2026-11-17: no collision in anything).
"""

from __future__ import annotations

import io
import math
import random
import sys
from pathlib import Path
from typing import Any

KIT = Path(__file__).resolve().parents[3] / "vendor" / "reachmora"
W, H = 1920, 1080

# the detective in front of the board: an original puppet of ours
DETECTIVE = {"skin": "fair", "outfit": "suit", "color": "#7A5534", "hair": "short", "hair_col": "#6B4A2E",
             "glasses": True, "bowtie": True, "tie": "#C8242C", "shirt": "#F4EFE2"}


def _kit():
    if str(KIT) not in sys.path:
        sys.path.insert(0, str(KIT))
    from engine import kit  # noqa: WPS433 - the kit's own module, imported not copied
    return kit


def _rgb(hexs: str) -> tuple[int, int, int]:
    h = hexs.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Board:
    """One drawing: skia canvas in the kit's 1920x1080 design space; text boxes recorded for the collision check."""

    def __init__(self):
        import skia
        self.skia = skia
        self.kit = _kit()
        self.surface = skia.Surface(W, H)
        self.c = self.surface.getCanvas()
        self.boxes: list[tuple[str, tuple[float, float, float, float]]] = []

    def fill(self, rect, colour, radius=0.0, alpha=255):
        sk = self.skia
        p = sk.Paint(AntiAlias=True, Color=sk.Color(*_rgb(colour), alpha))
        r = sk.Rect(*rect)
        self.c.drawRRect(sk.RRect.MakeRectXY(r, radius, radius), p) if radius else self.c.drawRect(r, p)

    def cork(self):
        sk = self.skia
        shader = sk.GradientShader.MakeRadial((W * .5, H * .45), W * .75, [sk.Color(150, 104, 60), sk.Color(92, 60, 32)])
        self.c.drawRect(sk.Rect(0, 0, W, H), sk.Paint(Shader=shader))
        r = random.Random(7)
        for _ in range(2600):                                # cork grain
            x, y, s = r.uniform(0, W), r.uniform(0, H), r.uniform(1.5, 4.5)
            tone = r.choice([(120, 80, 42), (170, 124, 74), (84, 54, 28)])
            self.c.drawCircle(x, y, s, sk.Paint(AntiAlias=True, Color=sk.Color(*tone, 90)))

    def card(self, rect, tilt=0.0, paper="#F6F1E6", inner="#DDE3E8"):
        """A pinned photo card: white border, inner picture area. Returns the inner rect (drawn rotated by tilt)."""
        sk = self.skia
        x0, y0, x1, y1 = rect
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.c.save()
        self.c.rotate(tilt, cx, cy)
        shadow = sk.Paint(AntiAlias=True, Color=sk.Color(0, 0, 0, 110),
                          MaskFilter=sk.MaskFilter.MakeBlur(sk.kNormal_BlurStyle, 14))
        self.c.drawRect(sk.Rect(x0 + 10, y0 + 16, x1 + 10, y1 + 16), shadow)
        self.fill(rect, paper)
        sheen = sk.GradientShader.MakeLinear([(x0, y0), (x1, y1)], [sk.Color(255, 255, 255, 70), sk.Color(0, 0, 0, 38)])
        self.c.drawRect(sk.Rect(*rect), sk.Paint(Shader=sheen))
        pad = max(14, (x1 - x0) * .045)
        inner_rect = (x0 + pad, y0 + pad, x1 - pad, y1 - pad)
        self.fill(inner_rect, inner)
        return (cx, cy, inner_rect)

    def end_card(self):
        self.c.restore()

    def puppet_in(self, inner_rect, spec, emotion="neutral", face=0.0, scale=None):
        """Head and shoulders of a kit puppet filling the card's picture area, dressed like the person: the kit's
        puppet, then our costume on top (a hairstyle and clothes the kit does not have: COSTUME_HAIR, COSTUME_WEAR)."""
        kit = self.kit
        x0, y0, x1, y1 = inner_rect
        s = scale or (x1 - x0) / 330
        cx = (x0 + x1) / 2
        head_y = y0 + (y1 - y0) * .44
        feet = head_y - kit.HEAD_CY * s
        eyes, mouth, brow, tilt, extra = kit.EMOTIONS.get(emotion, kit.EMOTIONS["neutral"])
        look = dict(spec)
        hair = look.get("hair") if look.get("hair") in COSTUME_HAIR else None
        wear = look.get("wear") if look.get("wear") in COSTUME_WEAR else None
        if hair:
            look["hair"] = "long" if hair == "wavy_long" else "none"
        self.c.save()
        self.c.clipRect(self.skia.Rect(*inner_rect), doAntiAlias=True)
        kit.draw_char(self.c, cx, feet, s, kit.make_look(look), face=face, eyes=eyes, mouth=mouth, brow=brow,
                      brow_tilt=tilt, sweat=1.0 if extra.get("sweat") else -1.0)
        self.c.save()
        self.c.translate(cx, feet)
        self.c.scale(s, s)
        if wear:
            COSTUME_WEAR[wear](self, kit.make_look(look))
        if hair:
            self.c.save()
            self.c.translate(0, kit.HEAD_CY)
            COSTUME_HAIR[hair](self, look.get("hair_col", "#1C1B22"), kit.HEAD_R)
            self.c.restore()
        self.c.restore()
        self.c.restore()

    # ---- costume pieces, drawn in the kit's puppet space (feet at 0,0; head centre at 0,HEAD_CY; ink line 6)
    def _shape(self, path, colour, lw=6.0, alpha=255):
        sk = self.skia
        self.c.drawPath(path, sk.Paint(AntiAlias=True, Color=sk.Color(*_rgb(colour), alpha)))
        self.c.drawPath(path, sk.Paint(AntiAlias=True, Color=sk.Color(24, 22, 27), StrokeWidth=lw,
                                       Style=sk.Paint.kStroke_Style, StrokeJoin=sk.Paint.kRound_Join))

    def _line(self, a, b, colour, width, alpha=255):
        sk = self.skia
        self.c.drawLine(*a, *b, sk.Paint(AntiAlias=True, Color=sk.Color(*_rgb(colour), alpha), StrokeWidth=width,
                                          StrokeCap=sk.Paint.kRound_Cap))

    def _curve(self, pts, colour, width, alpha=255):
        sk = self.skia
        path = sk.Path()
        path.moveTo(*pts[0])
        path.quadTo(*pts[1], *pts[2])
        self.c.drawPath(path, sk.Paint(AntiAlias=True, Color=sk.Color(*_rgb(colour), alpha), StrokeWidth=width,
                                       Style=sk.Paint.kStroke_Style, StrokeCap=sk.Paint.kRound_Cap))

    def logo_in(self, inner_rect, name: str) -> bool:
        from ..vector import logos
        icon = logos.find(name)
        if not icon:
            return False
        x0, y0, x1, y1 = inner_rect
        size = int(min(x1 - x0, y1 - y0) * .78)
        glyph = logos._glyph(icon["svg"], size, _rgb(icon.get("hex", "000000")) if sum(_rgb(icon.get("hex", "000000"))) < 600 else (20, 20, 24))
        self.fill(inner_rect, "#FFFFFF")
        buf = io.BytesIO()
        glyph.save(buf, "PNG")
        img = self.skia.Image.MakeFromEncoded(buf.getvalue())
        self.c.drawImage(img, (x0 + x1) / 2 - size / 2, (y0 + y1) / 2 - size / 2)
        return True

    def flag_in(self, inner_rect, country: str) -> bool:
        """Two simple flags drawn in code (no flag images): China and the United States."""
        sk = self.skia
        x0, y0, x1, y1 = inner_rect
        if country == "china":
            self.fill(inner_rect, "#DE2910")
            r = (y1 - y0) * .17
            for k, (fx, fy, rr) in enumerate([(.17, .3, r), (.34, .12, r * .35), (.41, .24, r * .35), (.41, .4, r * .35), (.34, .52, r * .35)]):
                self._star(x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy, rr, "#FFDE00")
            return True
        if country == "usa":
            for i in range(13):
                self.fill((x0, y0 + (y1 - y0) * i / 13, x1, y0 + (y1 - y0) * (i + 1) / 13), "#B22234" if i % 2 == 0 else "#FFFFFF")
            self.fill((x0, y0, x0 + (x1 - x0) * .42, y0 + (y1 - y0) * 7 / 13), "#3C3B6E")
            return True
        return False

    def _star(self, cx, cy, r, colour):
        sk = self.skia
        path = sk.Path()
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * .42
            (path.moveTo if i == 0 else path.lineTo)(cx + rr * math.cos(a), cy + rr * math.sin(a))
        path.close()
        self.c.drawPath(path, sk.Paint(AntiAlias=True, Color=sk.Color(*_rgb(colour))))

    def pin(self, x, y):
        sk = self.skia
        self.c.drawCircle(x + 3, y + 5, 15, sk.Paint(AntiAlias=True, Color=sk.Color(0, 0, 0, 90)))
        self.c.drawCircle(x, y, 15, sk.Paint(AntiAlias=True, Color=sk.Color(200, 30, 40)))
        self.c.drawCircle(x - 5, y - 5, 5, sk.Paint(AntiAlias=True, Color=sk.Color(255, 160, 160)))

    def string(self, a, b):
        sk = self.skia
        shadow = sk.Paint(AntiAlias=True, Color=sk.Color(0, 0, 0, 80), StrokeWidth=7, Style=sk.Paint.kStroke_Style,
                          MaskFilter=sk.MaskFilter.MakeBlur(sk.kNormal_BlurStyle, 3))
        self.c.drawLine(a[0] + 4, a[1] + 7, b[0] + 4, b[1] + 7, shadow)
        p = sk.Paint(AntiAlias=True, Color=sk.Color(206, 22, 34), StrokeWidth=7, Style=sk.Paint.kStroke_Style)
        self.c.drawLine(*a, *b, p)

    def banner(self, text: str, cx: float, top: float, max_w: float, size: int = 92):
        """The name on a red banner, the kit's marker lettering, measured."""
        sk = self.skia
        kit = self.kit
        text = text.upper()
        face = self.bold()
        size = kit.fit_size(text, size, max_w - 80, face)
        tw = kit.text_w(text, size, face)
        w, h = tw + 80, size * 1.35
        rect = (cx - w / 2, top, cx + w / 2, top + h)
        shadow = sk.Paint(AntiAlias=True, Color=sk.Color(0, 0, 0, 120), MaskFilter=sk.MaskFilter.MakeBlur(sk.kNormal_BlurStyle, 10))
        self.c.drawRect(sk.Rect(rect[0] + 8, rect[1] + 12, rect[2] + 8, rect[3] + 12), shadow)
        self.fill(rect, "#C8242C")
        self.c.drawRect(sk.Rect(*rect), sk.Paint(AntiAlias=True, Color=sk.Color(255, 255, 255), StrokeWidth=6,
                                                 Style=sk.Paint.kStroke_Style))
        font = sk.Font(face, size)
        base = top + h / 2 + size * .36
        self.c.drawString(text, cx - tw / 2, base, font, sk.Paint(AntiAlias=True, Color=sk.Color(10, 10, 12), StrokeWidth=size * .14,
                                                                    Style=sk.Paint.kStroke_Style, StrokeJoin=sk.Paint.kRound_Join))
        self.c.drawString(text, cx - tw / 2, base, font, sk.Paint(AntiAlias=True, Color=sk.Color(255, 255, 255)))
        self.boxes.append((text, rect))

    def bold(self):
        """Anton (OFL, assets/fonts/thumb): the bold condensed lettering of the thumbnails that work."""
        root = Path(__file__).resolve().parents[3] / "assets" / "fonts" / "thumb"
        face = self.skia.Typeface.MakeFromFile(str(root / "anton-latin-400-normal.woff"))
        return face if face is not None and face.getFamilyName() else self.skia.Typeface.MakeFromFile(str(root / "InterDisplay-Black.otf"))

    def detective(self, x, feet, s=2.6, emotion="angry", face=.55):
        kit = self.kit
        eyes, mouth, brow, tilt, extra = kit.EMOTIONS.get(emotion, kit.EMOTIONS["neutral"])
        kit.draw_char(self.c, x, feet, s, kit.make_look(DETECTIVE), face=face, eyes=eyes, mouth=mouth, brow=brow,
                      brow_tilt=tilt, arms=kit.POSES["think"])

    def light(self):
        """The finish of the video's own look (kit.py lighting): a warm key light on the board's centre, a soft
        glow, darker edges."""
        kit = self.kit
        kit.add_light(self.c, 1130, 360, 1050, (255, 200, 140), .22)
        kit.add_light(self.c, 1150, 400, 560, (255, 236, 205), .14)
        kit.vignette(self.c, .85, .30)

    def goli(self, x, y, height, pose="think", outfit="royal", mirror=True):
        """Goli reacting, for the Stickman + Goli videos: the real 3D Goli from the render library (2026-11-21)."""
        import io

        from ..vector.thumb_styles import goli as goli_cut
        cut = goli_cut(pose, outfit, "E", None, int(height), upper=1.0)
        buf = io.BytesIO()
        cut.save(buf, "PNG")
        width = cut.width
        img = self.skia.Image.MakeFromEncoded(buf.getvalue())
        shadow = self.skia.Paint(AntiAlias=True, Color=self.skia.Color(0, 0, 0, 120),
                                 MaskFilter=self.skia.MaskFilter.MakeBlur(self.skia.kNormal_BlurStyle, 24))
        self.c.save()
        if mirror:                                  # he faces the board
            self.c.translate(2 * x + width, 0)
            self.c.scale(-1, 1)
        self.c.drawImage(img, x, y)
        self.c.restore()

    def save(self, out: Path, size=(1280, 720)) -> Path:
        from PIL import Image
        img = self.surface.makeImageSnapshot()
        from PIL import ImageEnhance
        png = Image.open(io.BytesIO(bytes(img.encodeToData()))).convert("RGB").resize(size, Image.LANCZOS)
        # the grade of the Stickman thumbnails that work: richer colour, a little more contrast
        png = ImageEnhance.Contrast(ImageEnhance.Color(png).enhance(1.22)).enhance(1.10)
        out.parent.mkdir(parents=True, exist_ok=True)
        png.save(out, quality=92)
        return out


def collisions(boxes, margin=0.02) -> list[str]:
    out = []
    for i, (ta, a) in enumerate(boxes):
        if a[0] < W * margin or a[1] < H * margin or a[2] > W * (1 - margin) or a[3] > H * (1 - margin):
            out.append(f'"{ta}" leaves the frame')
        for tb, b in boxes[i + 1:]:
            if min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1]):
                out.append(f'"{ta}" touches "{tb}"')
    return out


def board(main: dict[str, Any], others: list[dict[str, Any]], logos_: list[str], flags: list[str], out: Path,
          reactor: str = "detective", outfit: str = "royal") -> Path:
    """main / others: {"name", "look" (a kit cast look), "emotion"}. The main person's big card in the middle with
    the name banner; up to 5 pinned cards round it (people, logos, flags), joined by red strings; the detective in
    front on the left."""
    b = Board()
    b.cork()
    # packed like the thumbnails that work: the main card nearly full height, the others crowding round it
    slots = [((470, 30, 760, 290), -6), ((1380, 40, 1780, 300), 5), ((1400, 330, 1720, 700), -4),
             ((480, 330, 760, 640), 5), ((1560, 690, 1850, 1030), 4), ((490, 680, 760, 960), -5)]
    main_rect = (760, 40, 1380, 850)
    main_pin = ((main_rect[0] + main_rect[2]) / 2, main_rect[1] + 8)
    items: list[tuple[str, Any]] = [("logo", n) for n in logos_][:2] + [("flag", f) for f in flags][:1] + \
        [("person", p) for p in others][:3]
    from ..vector import logos as logo_book
    items = [(k, w) for k, w in items if k != "logo" or logo_book.find(w)]
    placed = list(zip(slots, items))
    pins = [((rect[0] + rect[2]) / 2, rect[1] + 8) for (rect, _), _ in placed]
    for (rect, tilt), (kind, what) in placed:
        cx, cy, inner = b.card(rect, tilt, inner="#FFFFFF" if kind == "logo" else "#DDE3E8")
        if kind == "logo":
            b.logo_in(inner, what)
        elif kind == "flag":
            b.flag_in(inner, what)
        else:
            b.puppet_in(inner, what["look"], what.get("emotion", "neutral"))
        b.end_card()
    cx, cy, inner = b.card(main_rect, 0)
    b.puppet_in(inner, main["look"], main.get("emotion", "smug"), scale=(inner[2] - inner[0]) / 270)
    b.end_card()
    # the red strings run over the cards and off the frame, like the boards that work; each runs from a card's pin
    # to the main card's pin or off the near edge, never across the middle of a face
    for p in pins:
        b.string(p, main_pin)
    for p in pins:
        b.string(p, (0, p[1] - 60) if p[0] < main_pin[0] else (1920, p[1] - 60))
    for p in pins + [main_pin]:
        b.pin(*p)
    b.banner(main["name"], (main_rect[0] + main_rect[2]) / 2, main_rect[3] - 70, 900, size=130)
    if reactor == "goli":        # Stickman + Goli videos: Goli in front, surprised at the board
        b.goli(-260, 170, 1500, pose=main.get("goli_pose", "think"), outfit=outfit)
    else:
        b.detective(200, 1900, s=3.4, emotion=main.get("detective", "angry"))
    b.light()
    problems = collisions(b.boxes)
    if problems:
        raise ValueError("; ".join(problems))
    return b.save(out)


# ---------------------------------------------------------------- costumes (thumbnail only; the kit stays unchanged)
def _shade(hexs: str, k: float) -> str:
    r, g, b = _rgb(hexs)
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v * k))) for v in (r, g, b))


def _hair_swept(b: Board, colour: str, R: float) -> None:
    """Full hair swept back, close to the head, with strands: the grey hair of a tech founder."""
    sk = b.skia
    p = sk.Path()
    p.moveTo(-R - 6, -16)
    p.cubicTo(-R - 14, -R + 6, -R * .6, -R - 30, -R * .05, -R - 26)
    p.cubicTo(R * .4, -R - 34, R + 6, -R * .7, R + 8, -34)
    p.cubicTo(R + 10, -20, R + 2, -12, R - 6, -18)
    p.cubicTo(R * .7, -50, R * .3, -58, -R * .1, -56)
    p.cubicTo(-R * .5, -52, -R * .85, -40, -R - 6, -16)
    p.close()
    b._shape(p, colour)
    dark, light = _shade(colour, .7), _shade(colour, 1.2)
    for i, (sx, sy, ex, ey) in enumerate([(-78, -56, 10, -112), (-46, -58, 46, -112), (-14, -58, 76, -94),
                                          (18, -56, 94, -62), (-92, -36, -46, -96)]):
        b._curve([(sx, sy), ((sx + ex) / 2 - 8, (sy + ey) / 2 - 14), (ex, ey)], dark if i % 2 else light, 5, 220)


def _hair_swept_forward(b: Board, colour: str, R: float) -> None:
    """Hair combed up and forward over the forehead, a big front wave."""
    sk = b.skia
    p = sk.Path()
    p.moveTo(-R - 6, -6)
    p.cubicTo(-R - 18, -R - 20, R * .2, -R - 56, R + 12, -R * .55)
    p.cubicTo(R + 30, -40, R + 4, -26, R * .6, -46)
    p.cubicTo(R * .2, -30, -R * .45, -44, -R * .6, -38)
    p.cubicTo(-R * .8, -32, -R - 2, -20, -R - 6, -6)
    p.close()
    b._shape(p, colour)
    for sx, sy, ex, ey in [(-70, -60, 60, -96), (-40, -50, 90, -70), (-90, -30, 10, -110)]:
        b._curve([(sx, sy), ((sx + ex) / 2, (sy + ey) / 2 - 18), (ex, ey)], _shade(colour, .78), 5, 220)


def _hair_wavy_long(b: Board, colour: str, R: float) -> None:
    """Long wavy hair falling past the shoulders (drawn over the kit's long hair), parted, with waves."""
    sk = b.skia
    for side in (-1, 1):
        p = sk.Path()
        p.moveTo(side * 10, -R - 6)
        p.cubicTo(side * (R + 30), -R - 4, side * (R + 26), -10, side * (R + 6), 40)
        for k in range(3):
            y = 40 + k * 46
            p.cubicTo(side * (R + 34), y + 16, side * (R - 8), y + 30, side * (R + 20), y + 46)
        p.lineTo(side * (R - 30), 170)
        p.cubicTo(side * (R - 20), 60, side * (R - 2), -20, side * (R * .55), -66)
        p.cubicTo(side * R * .3, -84, side * 20, -80, side * 10, -R - 6)
        p.close()
        b._shape(p, colour)
        for k in range(3):
            y = 0 + k * 52
            b._curve([(side * (R - 6), y), (side * (R + 18), y + 22), (side * (R + 2), y + 48)], _shade(colour, 1.6), 4, 170)


def _wear_leather(b: Board, look: dict) -> None:
    """A black leather jacket: lapels, a zip, quilted shoulder seams, a sheen."""
    sk, top, bot = b.skia, -345, -128
    body = sk.Path()
    body.addRRect(sk.RRect.MakeRectXY(sk.Rect(-84, top, 84, bot), 66, 72))
    b.c.save()
    b.c.clipPath(body, doAntiAlias=True)
    b.c.drawPath(body, sk.Paint(AntiAlias=True, Color=sk.Color(28, 28, 32)))
    shine = sk.GradientShader.MakeLinear([(-84, top), (40, bot)], [sk.Color(255, 255, 255, 60), sk.Color(255, 255, 255, 0)])
    b.c.drawPath(body, sk.Paint(Shader=shine))
    for y in (top + 44, top + 70):                                   # quilted shoulder seams
        b._line((-84, y), (-36, y + 10), "#55555E", 3, 200)
        b._line((84, y), (36, y + 10), "#55555E", 3, 200)
    for side in (-1, 1):                                             # lapels
        lap = sk.Path()
        lap.moveTo(side * 6, top - 2)
        lap.lineTo(side * 54, top + 4)
        lap.lineTo(side * 40, top + 70)
        lap.lineTo(side * 10, top + 96)
        lap.close()
        b._shape(lap, "#3A3A42", 4)
    b._line((0, top + 90), (0, bot), "#9A9AA4", 4)                   # the zip
    for y in range(int(top) + 100, int(bot), 14):
        b._line((-4, y), (4, y), "#9A9AA4", 2, 220)
    b.c.restore()
    b.c.drawPath(body, sk.Paint(AntiAlias=True, Color=sk.Color(24, 22, 27), StrokeWidth=6, Style=sk.Paint.kStroke_Style))


def _wear_qipao(b: Board, look: dict) -> None:
    """A red qipao: mandarin collar, the curved gold-trimmed closure, a flower print."""
    sk, top, bot = b.skia, -345, -128
    body = sk.Path()
    body.addRRect(sk.RRect.MakeRectXY(sk.Rect(-84, top, 84, bot), 66, 72))
    base = look.get("color", "#B3262E")
    b.c.save()
    b.c.clipPath(body, doAntiAlias=True)
    b.c.drawPath(body, sk.Paint(AntiAlias=True, Color=sk.Color(*_rgb(base))))
    r = random.Random(11)
    for _ in range(14):                                               # the flower print
        fx, fy, fs = r.uniform(-80, 80), r.uniform(top + 30, bot), r.uniform(9, 14)
        for k in range(5):
            a = k * 2 * math.pi / 5
            b.c.drawCircle(fx + fs * math.cos(a), fy + fs * math.sin(a), fs * .62,
                           sk.Paint(AntiAlias=True, Color=sk.Color(255, 214, 222, 230)))
        b.c.drawCircle(fx, fy, fs * .45, sk.Paint(AntiAlias=True, Color=sk.Color(242, 193, 78)))
    b._curve([(-34, top + 26), (40, top + 30), (52, top + 92)], "#F2C14E", 7)    # the closure
    b.c.restore()
    b.c.drawPath(body, sk.Paint(AntiAlias=True, Color=sk.Color(24, 22, 27), StrokeWidth=6, Style=sk.Paint.kStroke_Style))
    collar = sk.Path()
    collar.addRRect(sk.RRect.MakeRectXY(sk.Rect(-36, top - 14, 36, top + 22), 14, 14))
    b._shape(collar, base, 5)
    b._line((-30, top + 16), (30, top + 16), "#F2C14E", 4)


COSTUME_HAIR = {"swept": _hair_swept, "swept_forward": _hair_swept_forward, "wavy_long": _hair_wavy_long}
COSTUME_WEAR = {"leather": _wear_leather, "qipao": _wear_qipao}
