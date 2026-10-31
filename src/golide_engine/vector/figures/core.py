"""Shared machinery for exact figures: the spec language, safe numbers and
expressions, and the Canvas that draws in the house style while recording the
exact pen strokes and labels the renderer animates.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WHITE = (238, 236, 230)
DIM = (150, 150, 150)
GOLD = (233, 196, 106)
DIM_PACE = 0.35  # matches illustrate.DIM_PACE: guide lines are drawn quickly
SUPER = 2  # draw at 2x, then downsample for smooth lines


MISSING_GLYPHS = {"γ": "gamma", "λ": "lambda", "θ": "angle", "Δ": "change in ", "→": "to", "μ": "µ"}


class FigureError(ValueError):
    pass


# ------------------------------------------------------------------ parsing

def parse_figure(spec: str) -> tuple[str, dict[str, str], list[str]]:
    """'kind: k=v; k=v; item' -> (kind, {k: v}, [items])."""
    text = str(spec or "").strip()
    if not text or ":" not in text:
        raise FigureError("figure needs 'kind: parameters'")
    kind, _, rest = text.partition(":")
    kind = kind.strip().lower().replace(" ", "_").replace("-", "_")
    params: dict[str, str] = {}
    items: list[str] = []
    for part in re.split(r"[;\n]", rest):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            key, _, value = part.partition("=")
            params[key.strip().lower()] = value.strip()
        else:
            items.append(part)
    return kind, params, items


def num(params: dict, key: str, default: float | None = None) -> float:
    if key not in params:
        if default is None:
            raise FigureError(f"missing {key}")
        return default
    try:
        return float(expr(params[key])(0.0))
    except Exception as exc:
        raise FigureError(f"{key} is not a number: {params[key]!r}") from exc


def pair(params: dict, key: str) -> tuple[float, float]:
    if key not in params:
        raise FigureError(f"missing {key}")
    parts = [p for p in re.split(r"[,\s]+", params[key].strip("()[] ")) if p]
    if len(parts) != 2:
        raise FigureError(f"{key} needs two numbers")
    return float(expr(parts[0])(0.0)), float(expr(parts[1])(0.0))


def yes(params: dict, key: str) -> bool:
    return params.get(key, "").strip().lower() in {"yes", "y", "true", "1", "on"}


_SAFE = {name: getattr(math, name) for name in ("sin", "cos", "tan", "sqrt", "exp", "log", "log10", "pi", "e",
                                                "asin", "acos", "atan", "sinh", "cosh", "tanh")}
_SAFE["abs"] = abs


def expr(source: str):
    """A safe f(x) from text like 'x^2 - 2x + 1' or '3sin(x)'."""
    text = source.strip().lower().replace("^", "**").replace("π", "pi").replace("·", "*")
    text = re.sub(r"^(y|f\(x\))\s*=", "", text).strip()
    if not re.fullmatch(r"[0-9x+\-*/().,\s a-z_]*", text):
        raise FigureError(f"bad expression {source!r}")
    names = set(re.findall(r"[a-z_]+", text)) - {"x"}
    if names - set(_SAFE):
        raise FigureError(f"unknown name in {source!r}: {sorted(names - set(_SAFE))}")
    # implicit multiplication: 2x, 3sin(x), 2(x+1), )(  , x(
    text = re.sub(r"(\d)\s*(x|[a-z]{2,}\(|\()", r"\1*\2", text)
    text = re.sub(r"\)\s*(\(|x|\d)", r")*\1", text)
    text = re.sub(r"\bx\s*(\(|\d)", r"x*\1", text)
    code = compile(text, "<figure>", "eval")
    return lambda x: float(eval(code, {"__builtins__": {}}, {**_SAFE, "x": x}))  # noqa: S307


def fmt(value: float, places: int = 2) -> str:
    """Up to ``places`` decimals, no trailing zeros: 5, 0.5, 0.87, 40.82."""
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    # Round halves away from zero, so equal members of a symmetric structure read
    # the same (3.75 -> 3.8 both times, never 3.8 and 3.7 from float noise).
    nudged = value + math.copysign(1e-9 * max(1.0, abs(value)), value)
    return f"{nudged:.{places}f}".rstrip("0").rstrip(".")


# ------------------------------------------------------------------ canvas

@dataclass
class Canvas:
    draw: ImageDraw.ImageDraw
    image: Image.Image
    scale: float          # pixels per math unit (x)
    ox: float             # pixel x of math x=0
    oy: float             # pixel y of math y=0
    line: float
    font: ImageFont.FreeTypeFont
    small: ImageFont.FreeTypeFont
    # What the renderer draws: exact pen strokes in construction order and the
    # labels, each appearing once the pen has drawn what it names.
    strokes: list = field(default_factory=list)
    labels: list = field(default_factory=list)
    # 2026-10-31: solid coloured parts (a screen layer, a metal plate), each shown once the
    # pen reaches it, so architecture drawings are real coloured parts, not wireframes.
    panels: list = field(default_factory=list)
    drawn: float = 0.0
    yscale: float | None = None
    tiny: ImageFont.FreeTypeFont | None = None  # dense scales (the spectrum); label(small="tiny")  # graphs: pixels per math unit (y), when x and y units differ

    def p(self, x: float, y: float) -> tuple[float, float]:
        return self.ox + x * self.scale, self.oy - y * (self.yscale or self.scale)

    def pxline(self, pts, color=WHITE, width: float = 1.0) -> None:
        """Draw and record a polyline given in (supersampled) pixels."""
        pts = [(float(x), float(y)) for x, y in pts]
        if len(pts) < 2:
            return
        w = max(1, round(self.line * width))
        self.draw.line(pts, fill=color, width=w, joint="curve")
        # The renderer smooths each stroke into a curve, so a corner (a box, a
        # right-angle mark, an arrowhead) is split into separate strokes there.
        pieces, current = [], [pts[0]]
        for i in range(1, len(pts)):
            current.append(pts[i])
            if 0 < i < len(pts) - 1:
                a, b, c = pts[i - 1], pts[i], pts[i + 1]
                t1 = math.atan2(b[1] - a[1], b[0] - a[0])
                t2 = math.atan2(c[1] - b[1], c[0] - b[0])
                turn = abs((t2 - t1 + math.pi) % math.tau - math.pi)
                if turn > math.radians(25):
                    pieces.append(current)
                    current = [pts[i]]
        pieces.append(current)
        for piece in pieces:
            length = sum(math.dist(a, b) for a, b in zip(piece, piece[1:]))
            if length <= 0:
                continue
            self.drawn += length * (DIM_PACE if color == DIM else 1.0)
            stroke = {"points": [[x / SUPER, y / SUPER] for x, y in piece], "gold": color == GOLD,
                      "dim": color == DIM, "width": w / SUPER}
            if color not in (WHITE, GOLD, DIM):
                stroke["rgb"] = list(color)  # true colours where colour is the physics (a spectrum)
            self.strokes.append(stroke)

    def panel(self, pts, rgb, outline=None, width: float = 1.0, shade: float = 0.35) -> None:
        """A solid part in maths coordinates: filled in ``rgb`` (lit from above), then outlined."""
        px = [self.p(*q) for q in pts]
        self.panels.append({"points": [[x / SUPER, y / SUPER] for x, y in px], "rgb": list(rgb),
                            "shade": shade, "after": self.drawn})
        self.draw.polygon(px, fill=tuple(int(v) for v in rgb))
        self.pxline(px + [px[0]], outline or WHITE, width)

    def dashed(self, a, b, color=DIM, width: float = 0.8, dash: float = 0.05) -> None:
        """A dashed line (virtual rays, extensions); dash is a share of the segment."""
        steps = max(2, int(1 / dash))
        for i in range(0, steps, 2):
            t0, t1 = i / steps, min(1.0, (i + 1) / steps)
            self.seg((a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
                     (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1), color, width)

    def dot(self, x: float, y: float, color=WHITE, radius: float = 3.5) -> None:
        """A small round marker (round on stretched graphs too); radius in line widths."""
        px, py = self.p(x, y)
        self.pxcircle(px, py, self.line * radius, color)

    def circle(self, center, r: float, color=WHITE, width: float = 1.0) -> None:
        self.arc(center, r, 0, 360, color, width)

    def seg(self, a, b, color=WHITE, width: float = 1.0) -> None:
        self.pxline([self.p(*a), self.p(*b)], color, width)

    def poly(self, pts, color=WHITE, width: float = 1.0) -> None:
        self.pxline([self.p(*q) for q in pts], color, width)

    def pxcircle(self, cx: float, cy: float, r: float, color=WHITE, width: float = 1.0) -> None:
        self.pxline([(cx + r * math.cos(math.tau * i / 36), cy + r * math.sin(math.tau * i / 36))
                     for i in range(37)], color, width)

    def arrow(self, a, b, color=WHITE, width: float = 1.0, head: float | None = None) -> None:
        self.seg(a, b, color, width)
        ax, ay = self.p(*a)
        bx, by = self.p(*b)
        ang = math.atan2(by - ay, bx - ax)
        size = head or self.line * 5.5
        left = (bx - size * math.cos(ang + 0.45), by - size * math.sin(ang + 0.45))
        right = (bx - size * math.cos(ang - 0.45), by - size * math.sin(ang - 0.45))
        self.pxline([left, (bx, by), right], color, width)

    def _text(self, px: float, py: float, text: str, color, small: bool, anchor: str) -> None:
        """Record a label; it is placed (clear of every line and label) and drawn in ``save``."""
        for glyph, word in MISSING_GLYPHS.items():  # the brand font has no Greek letters
            text = text.replace(glyph, word)
        font = self.tiny if small == "tiny" else self.small if small else self.font
        self.labels.append({"text": text, "px": px, "py": py, "color": tuple(color), "font": font,
                            "anchor": anchor, "after": self.drawn})

    def label(self, x: float, y: float, text: str, color=WHITE, small: bool = False,
              anchor: str = "mm", dx: float = 0, dy: float = 0) -> None:
        px, py = self.p(x, y)
        self._text(px + dx, py + dy, text, color, small, anchor)

    def side_label(self, a, b, text: str, color=WHITE, small: bool = False, away: float = 1.0) -> None:
        """Label the middle of segment a-b, pushed off the line on its left side."""
        ax, ay = self.p(*a)
        bx, by = self.p(*b)
        length = math.hypot(bx - ax, by - ay) or 1.0
        nx, ny = (ay - by) / length, (bx - ax) / length  # left normal in pixels
        gap = self.line * 11 * away
        self._text((ax + bx) / 2 + nx * gap, (ay + by) / 2 + ny * gap, text, color, small, "mm")

    def arc(self, center, r: float, start_deg: float, end_deg: float, color=WHITE, width: float = 1.0) -> None:
        """Counter-clockwise in maths degrees."""
        steps = max(8, int(abs(end_deg - start_deg) / 3))
        pts = [(center[0] + r * math.cos(math.radians(start_deg + (end_deg - start_deg) * i / steps)),
                center[1] + r * math.sin(math.radians(start_deg + (end_deg - start_deg) * i / steps)))
               for i in range(steps + 1)]
        self.poly(pts, color, width)


def new_canvas(size: tuple[int, int], bounds: tuple[float, float, float, float], stretch: bool = False) -> Canvas:
    """bounds: math-space x0, y0, x1, y1 to fit inside the image with margins.

    stretch: a graph whose axes have different units fills the frame (x and y
    scale separately); geometry (triangles, circles, rays) never stretches.
    """
    from ...theme import load_theme

    w, h = size[0] * SUPER, size[1] * SUPER
    image = Image.new("RGB", (w, h), (0, 0, 0))
    x0, y0, x1, y1 = bounds
    margin = 0.14
    sx = w * (1 - 2 * margin) / max(1e-6, x1 - x0)
    sy = h * (1 - 2 * margin) / max(1e-6, y1 - y0)
    if not stretch:
        sx = sy = min(sx, sy)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ox, oy = w / 2 - cx * sx, h / 2 + cy * sy
    base = min(w, h)
    theme = load_theme()
    font = ImageFont.truetype(str(theme.font("bold")), round(base * 0.058))
    small = ImageFont.truetype(str(theme.font("bold")), round(base * 0.046))
    tiny = ImageFont.truetype(str(theme.font("bold")), round(base * 0.034))
    return Canvas(ImageDraw.Draw(image), image, sx, ox, oy, base * 0.0042, font, small,
                  yscale=sy if stretch else None, tiny=tiny)


def sidecar_path(target: Path) -> Path:
    return target.with_suffix(".figure.json")


def save(c: Canvas, target: Path) -> Path:
    """The PNG (a preview, and what the cover uses) plus the exact strokes and labels.

    Labels are placed here, once every stroke is known, so no text touches a line
    or another text (see ``placement``).
    """
    import json

    from .placement import MARGIN, occupancy, place

    size = (c.image.width, c.image.height)
    mask = occupancy(size, c.strokes, SUPER, c.line)
    total = c.drawn or 1.0
    labels = []
    target.parent.mkdir(parents=True, exist_ok=True)
    for i, item in enumerate(c.labels):
        font, text, anchor = item["font"], item["text"], item["anchor"]
        x0, y0, x1, y1 = c.draw.textbbox((item["px"], item["py"]), text, font=font, anchor=anchor)
        gap = c.line * MARGIN
        dx, dy = place(mask, (x0 - gap, y0 - gap, x1 + gap, y1 + gap), size, step=max(c.line * 3, (y1 - y0) * 0.35))
        px, py = item["px"] + dx, item["py"] + dy
        c.draw.text((px, py), text, fill=item["color"], font=font, anchor=anchor)
        pad = 4 * SUPER
        bx0, by0, bx1, by1 = c.draw.textbbox((px, py), text, font=font, anchor=anchor)
        bx0, by0 = int(bx0 - pad) // SUPER * SUPER, int(by0 - pad) // SUPER * SUPER
        bx1, by1 = int(bx1 + pad), int(by1 + pad)
        crop = Image.new("RGBA", (bx1 - bx0, by1 - by0), (0, 0, 0, 0))
        ImageDraw.Draw(crop).text((px - bx0, py - by0), text, fill=item["color"] + (255,), font=font, anchor=anchor)
        crop = crop.resize((max(1, crop.width // SUPER), max(1, crop.height // SUPER)), Image.Resampling.LANCZOS)
        name = f"{target.stem}.label-{i:02d}.png"
        crop.save(target.parent / name)
        labels.append({"text": text, "file": name, "x": bx0 / SUPER, "y": by0 / SUPER,
                       "after": round(min(1.0, item["after"] / total), 4)})
    out = c.image.resize((c.image.width // SUPER, c.image.height // SUPER), Image.Resampling.LANCZOS)
    out.save(target)
    sidecar_path(target).write_text(json.dumps({
        "width": out.width, "height": out.height, "strokes": c.strokes, "labels": labels,
        "panels": [dict(item, after=round(min(1.0, item["after"] / total), 4)) for item in c.panels],
    }) + "\n", encoding="utf-8")
    return target


def axes(c: Canvas, x0: float, x1: float, y0: float, y1: float, ticks: bool = True) -> None:
    c.arrow((x0, 0), (x1, 0), DIM, 0.8)
    c.arrow((0, y0), (0, y1), DIM, 0.8)
    if not ticks:
        return
    step = tick_step(max(x1 - x0, y1 - y0))
    t = c.line * 2.2
    for i in range(math.ceil(x0 / step), math.floor(x1 / step) + 1):
        x = i * step
        if i and x < x1 - step * 0.4:
            px, py = c.p(x, 0)
            c.pxline([(px, py - t), (px, py + t)], DIM, 0.7)
    for i in range(math.ceil(y0 / step), math.floor(y1 / step) + 1):
        y = i * step
        if i and y < y1 - step * 0.4:
            px, py = c.p(0, y)
            c.pxline([(px - t, py), (px + t, py)], DIM, 0.7)


def tick_step(span: float) -> float:
    raw = span / 8
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for m in (1, 2, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def graph(c: Canvas, x0: float, x1: float, y0: float, y1: float, xlabel: str = "", ylabel: str = "",
          numbers: bool = True) -> None:
    """Axes for a graph with numbered ticks and axis names (a stretched canvas)."""
    c.arrow((x0, 0), (x1, 0), DIM, 0.8)
    c.arrow((0, y0), (0, y1), DIM, 0.8)
    t = c.line * 2.2
    xs, ys = tick_step((x1 - x0) * 1.6), tick_step((y1 - y0) * 1.6)
    for i in range(math.ceil(x0 / xs), math.floor(x1 / xs) + 1):
        x = i * xs
        if i and x < x1 - xs * 0.3:
            px, py = c.p(x, 0)
            c.pxline([(px, py - t), (px, py + t)], DIM, 0.7)
            if numbers:
                c.label(x, 0, fmt(x), DIM, small=True, anchor="mt", dy=t * 2)
    for i in range(math.ceil(y0 / ys), math.floor(y1 / ys) + 1):
        y = i * ys
        if i and y < y1 - ys * 0.3:
            px, py = c.p(0, y)
            c.pxline([(px - t, py), (px + t, py)], DIM, 0.7)
            if numbers:
                c.label(0, y, fmt(y), DIM, small=True, anchor="rm", dx=-t * 2.5)
    if xlabel:
        c.label(x1, 0, xlabel, DIM, small=True, anchor="rb", dy=-t * 2.5)
    if ylabel:
        c.label(0, y1, ylabel, DIM, small=True, anchor="lm", dx=t * 3)
