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
        """Head and shoulders of a kit puppet filling the card's picture area."""
        kit = self.kit
        x0, y0, x1, y1 = inner_rect
        s = scale or (x1 - x0) / 330
        cx = (x0 + x1) / 2
        head_y = y0 + (y1 - y0) * .44
        feet = head_y - kit.HEAD_CY * s
        eyes, mouth, brow, tilt, extra = kit.EMOTIONS.get(emotion, kit.EMOTIONS["neutral"])
        self.c.save()
        self.c.clipRect(self.skia.Rect(*inner_rect), doAntiAlias=True)
        kit.draw_char(self.c, cx, feet, s, kit.make_look(spec), face=face, eyes=eyes, mouth=mouth, brow=brow,
                      brow_tilt=tilt, sweat=1.0 if extra.get("sweat") else -1.0)
        self.c.restore()

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
        p = sk.Paint(AntiAlias=True, Color=sk.Color(196, 24, 36), StrokeWidth=5, Style=sk.Paint.kStroke_Style)
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

    def goli(self, x, y, height, pose="shock", outfit="royal"):
        """Goli reacting, for the Stickman + Goli videos (edit/mascot.py, the same Goli as the videos)."""
        import cairosvg
        from ..edit import mascot
        w0, h0 = mascot.VIEW
        width = int(height * w0 / h0)
        png = cairosvg.svg2png(bytestring=mascot.svg(pose, width=width, mouth="O", outfit=outfit).encode("utf-8"),
                               output_width=width, output_height=int(height))
        img = self.skia.Image.MakeFromEncoded(png)
        shadow = self.skia.Paint(AntiAlias=True, Color=self.skia.Color(0, 0, 0, 120),
                                 MaskFilter=self.skia.MaskFilter.MakeBlur(self.skia.kNormal_BlurStyle, 24))
        self.c.drawOval(self.skia.Rect(x + width * .15, y + height * .9, x + width * .85, y + height * 1.02), shadow)
        self.c.drawImage(img, x, y)

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
    for p in pins:                                           # strings first: they run behind the cards
        b.string(p, main_pin)
    for p, q in zip(pins, pins[1:]):
        b.string(p, q)
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
    for p in pins + [main_pin]:
        b.pin(*p)
    b.banner(main["name"], (main_rect[0] + main_rect[2]) / 2, main_rect[3] - 70, 900, size=130)
    if reactor == "goli":        # Stickman + Goli videos: Goli in front, surprised at the board
        b.goli(-90, 250, 980, pose="shock", outfit=outfit)
    else:
        b.detective(200, 1900, s=3.4, emotion=main.get("detective", "angry"))
    b.light()
    problems = collisions(b.boxes)
    if problems:
        raise ValueError("; ".join(problems))
    return b.save(out)
