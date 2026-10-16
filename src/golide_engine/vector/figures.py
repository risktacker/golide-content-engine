"""Exact figures: the math layer (owner direction 2026-10-16).

Pictures from the image model are sketches: angles, lengths and curves are
guessed. When a scene's words carry exact maths, physics or engineering
(vectors, a right triangle, a function, the unit circle, a projectile, a beam,
forces), the storyboard gives the scene a ``figure`` instead, written in a
tiny spec language::

    vectors: a=3,1; b=1,2; sum=yes
    right_triangle: a=3; b=4; angle=yes
    function: f=x^2; x=-2,2; tangent=1
    function: f=sin(x); x=0,6.28; area=0,3.14
    unit_circle: angle=30; wave=yes
    projectile: speed=20; angle=45
    beam: length=6; load=10; at=2
    forces: 20@0; 15@120

Every coordinate is computed here and drawn in the house style (white line
art on black, the key part in gold, labels in the brand font) to a PNG. The
PNG then goes through the same tracing as an image-model drawing, so it is
drawn on by the pen, breathes and transitions exactly like every other scene.
No image model, no cost, and the geometry is true.
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
KINDS = ("vectors", "right_triangle", "function", "unit_circle", "projectile", "beam", "forces")


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
    if kind not in KINDS:
        raise FigureError(f"unknown figure kind {kind!r}")
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


def _num(params: dict, key: str, default: float | None = None) -> float:
    if key not in params:
        if default is None:
            raise FigureError(f"missing {key}")
        return default
    try:
        return float(_expr(params[key])(0.0))
    except Exception as exc:
        raise FigureError(f"{key} is not a number: {params[key]!r}") from exc


def _pair(params: dict, key: str) -> tuple[float, float]:
    if key not in params:
        raise FigureError(f"missing {key}")
    parts = [p for p in re.split(r"[,\s]+", params[key].strip("()[] ")) if p]
    if len(parts) != 2:
        raise FigureError(f"{key} needs two numbers")
    return float(_expr(parts[0])(0.0)), float(_expr(parts[1])(0.0))


def _yes(params: dict, key: str) -> bool:
    return params.get(key, "").strip().lower() in {"yes", "y", "true", "1", "on"}


_SAFE = {name: getattr(math, name) for name in ("sin", "cos", "tan", "sqrt", "exp", "log", "log10", "pi", "e",
                                                "asin", "acos", "atan", "sinh", "cosh", "tanh")}
_SAFE["abs"] = abs


def _expr(source: str):
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


def _fmt(value: float, places: int = 2) -> str:
    """Up to ``places`` decimals, no trailing zeros: 5, 0.5, 0.87, 40.82."""
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.{places}f}".rstrip("0").rstrip(".")


# ------------------------------------------------------------------ canvas

@dataclass
class Canvas:
    draw: ImageDraw.ImageDraw
    image: Image.Image
    scale: float          # pixels per math unit
    ox: float             # pixel x of math x=0
    oy: float             # pixel y of math y=0
    line: float
    font: ImageFont.FreeTypeFont
    small: ImageFont.FreeTypeFont
    # What the renderer draws: exact pen strokes in construction order and the
    # labels, each appearing once the pen has drawn what it names.
    strokes: list = field(default_factory=list)
    labels: list = field(default_factory=list)
    drawn: float = 0.0

    def p(self, x: float, y: float) -> tuple[float, float]:
        return self.ox + x * self.scale, self.oy - y * self.scale

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
            self.strokes.append({"points": [[x / SUPER, y / SUPER] for x, y in piece], "gold": color == GOLD,
                                 "dim": color == DIM, "width": w / SUPER})

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
        font = self.small if small else self.font
        self.draw.text((px, py), text, fill=color, font=font, anchor=anchor)
        x0, y0, x1, y1 = self.draw.textbbox((px, py), text, font=font, anchor=anchor)
        pad = 4 * SUPER
        x0, y0 = int(x0 - pad) // SUPER * SUPER, int(y0 - pad) // SUPER * SUPER
        x1, y1 = int(x1 + pad), int(y1 + pad)
        crop = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        ImageDraw.Draw(crop).text((px - x0, py - y0), text, fill=color + (255,), font=font, anchor=anchor)
        crop = crop.resize((max(1, crop.width // SUPER), max(1, crop.height // SUPER)), Image.Resampling.LANCZOS)
        self.labels.append({"text": text, "image": crop, "x": x0 / SUPER, "y": y0 / SUPER, "after": self.drawn})

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


def _canvas(size: tuple[int, int], bounds: tuple[float, float, float, float]) -> Canvas:
    """bounds: math-space x0, y0, x1, y1 to fit inside the image with margins."""
    from ..theme import load_theme

    w, h = size[0] * SUPER, size[1] * SUPER
    image = Image.new("RGB", (w, h), (0, 0, 0))
    x0, y0, x1, y1 = bounds
    margin = 0.14
    scale = min(w * (1 - 2 * margin) / max(1e-6, x1 - x0), h * (1 - 2 * margin) / max(1e-6, y1 - y0))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ox, oy = w / 2 - cx * scale, h / 2 + cy * scale
    base = min(w, h)
    theme = load_theme()
    font = ImageFont.truetype(str(theme.font("bold")), round(base * 0.058))
    small = ImageFont.truetype(str(theme.font("bold")), round(base * 0.046))
    return Canvas(ImageDraw.Draw(image), image, scale, ox, oy, base * 0.0042, font, small)


def sidecar_path(target: Path) -> Path:
    return target.with_suffix(".figure.json")


def _save(c: Canvas, target: Path) -> Path:
    """The PNG (a preview, and what the cover uses) plus the exact strokes and labels."""
    import json

    out = c.image.resize((c.image.width // SUPER, c.image.height // SUPER), Image.Resampling.LANCZOS)
    target.parent.mkdir(parents=True, exist_ok=True)
    out.save(target)
    total = c.drawn or 1.0
    labels = []
    for i, item in enumerate(c.labels):
        name = f"{target.stem}.label-{i:02d}.png"
        item["image"].save(target.parent / name)
        labels.append({"text": item["text"], "file": name, "x": item["x"], "y": item["y"],
                       "after": round(min(1.0, item["after"] / total), 4)})
    sidecar_path(target).write_text(json.dumps({
        "width": out.width, "height": out.height, "strokes": c.strokes, "labels": labels,
    }) + "\n", encoding="utf-8")
    return target


def _axes(c: Canvas, x0: float, x1: float, y0: float, y1: float, ticks: bool = True) -> None:
    c.arrow((x0, 0), (x1, 0), DIM, 0.8)
    c.arrow((0, y0), (0, y1), DIM, 0.8)
    if not ticks:
        return
    step = _tick_step(max(x1 - x0, y1 - y0))
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


def _tick_step(span: float) -> float:
    raw = span / 8
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for m in (1, 2, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


# ------------------------------------------------------------------ figures

def _vectors(size, params, items) -> Canvas:
    a = _pair(params, "a")
    b = _pair(params, "b") if "b" in params else None
    total = (a[0] + b[0], a[1] + b[1]) if b else a
    show_sum = b is not None and (_yes(params, "sum") or "sum" not in params)
    xs = [0, a[0]] + ([b[0], total[0]] if b else [])
    ys = [0, a[1]] + ([b[1], total[1]] if b else [])
    pad = 0.8
    x0, x1 = min(xs) - pad, max(xs) + pad
    y0, y1 = min(ys) - pad, max(ys) + pad
    c = _canvas(size, (x0, y0, x1, y1))
    _axes(c, x0, x1, y0, y1)
    names = [n.strip() for n in params.get("names", "a,b").split(",")] + ["b"]
    c.arrow((0, 0), a, WHITE, 1.2)
    c.side_label((0, 0), a, names[0], WHITE, away=1.0)
    if b:
        start = a if show_sum else (0, 0)
        end = (start[0] + b[0], start[1] + b[1])
        c.arrow(start, end, WHITE, 1.2)
        c.side_label(start, end, names[1], WHITE, away=1.0)
    if show_sum:
        c.arrow((0, 0), total, GOLD, 1.5)
        c.side_label((0, 0), total, f"{names[0]} + {names[1]}", GOLD, small=True, away=-1.4)
        c.label(total[0], total[1], f"({_fmt(total[0])}, {_fmt(total[1])})", GOLD, small=True,
                anchor="lb", dx=c.line * 6, dy=-c.line * 4)
        if _yes(params, "length"):
            c.label(total[0], total[1], f"length {_fmt(round(math.hypot(*total), 2))}", GOLD, small=True,
                    anchor="lt", dx=c.line * 6, dy=c.line * 4)
    elif not b:
        c.label(a[0], a[1], f"({_fmt(a[0])}, {_fmt(a[1])})", GOLD, small=True, anchor="lb",
                dx=c.line * 6, dy=-c.line * 4)
    return c


def _right_triangle(size, params, items) -> Canvas:
    a, b = _num(params, "a"), _num(params, "b")
    if a <= 0 or b <= 0:
        raise FigureError("triangle sides must be positive")
    hyp = math.hypot(a, b)
    c = _canvas(size, (-0.15 * a, -0.25 * b, a * 1.15, b * 1.12))
    A, B, C = (0, 0), (a, 0), (a, b)
    c.seg(A, B, WHITE, 1.2)
    c.seg(B, C, WHITE, 1.2)
    c.seg(C, A, GOLD, 1.5)
    box = min(a, b) * 0.12
    c.poly([(a - box, 0), (a - box, box), (a, box)], WHITE, 0.9)
    letters = _yes(params, "letters")
    c.label(a / 2, 0, "a" if letters else _fmt(a), WHITE, dy=c.line * 14)
    c.label(a, b / 2, "b" if letters else _fmt(b), WHITE, dx=c.line * 14)
    c.label(a / 2, b / 2, "c" if letters else _fmt(hyp), GOLD, dx=-c.line * 14, dy=-c.line * 10)
    if _yes(params, "angle"):
        deg = math.degrees(math.atan2(b, a))
        r = min(a, b) * 0.28
        c.arc(A, r, 0, deg, WHITE, 0.9)
        c.label(r * 1.25 * math.cos(math.radians(deg / 2)), r * 1.25 * math.sin(math.radians(deg / 2)),
                f"{_fmt(round(deg, 1))}°", WHITE, small=True, anchor="lm", dx=c.line * 3)
    if _yes(params, "formula"):
        c.label(a * 0.5, -0.18 * b, "a² + b² = c²", GOLD, small=True)
    return c


def _function(size, params, items) -> Canvas:
    f = _expr(params.get("f", "x^2"))
    lo, hi = _pair(params, "x") if "x" in params else (-3.0, 3.0)
    if hi <= lo:
        raise FigureError("x range must go low,high")
    n = 240
    xs = [lo + (hi - lo) * i / n for i in range(n + 1)]
    ys = []
    for x in xs:
        try:
            ys.append(f(x))
        except (ValueError, ZeroDivisionError, OverflowError):
            ys.append(float("nan"))
    good = [y for y in ys if math.isfinite(y)]
    if len(good) < n // 2:
        raise FigureError("function is undefined over most of the range")
    y_lo, y_hi = min(good + [0.0]), max(good + [0.0])
    if "y" in params:
        y_lo, y_hi = _pair(params, "y")
    span_y = max(1e-6, y_hi - y_lo)
    pad_x, pad_y = (hi - lo) * 0.08, span_y * 0.1
    x0, x1 = min(lo, 0) - pad_x, max(hi, 0) + pad_x
    y0, y1 = y_lo - pad_y, y_hi + pad_y
    c = _canvas(size, (x0, y0, x1, y1))
    # Different x and y units are fine for a graph: stretch y to the frame.
    w, h = c.image.width, c.image.height
    margin = 0.14
    sx = w * (1 - 2 * margin) / (x1 - x0)
    sy = h * (1 - 2 * margin) / (y1 - y0)
    c.scale = sx
    stretch = sy / sx
    c.ox = w / 2 - (x0 + x1) / 2 * sx
    c.oy = h / 2 + (y0 + y1) / 2 * sy
    P = lambda x, y: (x, y * stretch)  # noqa: E731
    base_p = c.p
    c.p = lambda x, y: base_p(*P(x, y))  # type: ignore[method-assign]
    _axes_stretched(c, x0, x1, y0, y1)
    key_gold = not ("tangent" in params or "area" in params)
    run: list[tuple[float, float]] = []
    for x, y in zip(xs, ys):
        if math.isfinite(y) and y0 - span_y <= y <= y1 + span_y:
            run.append((x, min(max(y, y0), y1)))
        elif run:
            c.poly(run, GOLD if key_gold else WHITE, 1.4)
            run = []
    if run:
        c.poly(run, GOLD if key_gold else WHITE, 1.4)
    if "area" in params:
        a0, a1 = _pair(params, "area")
        k = 60
        ax = [a0 + (a1 - a0) * i / k for i in range(k + 1)]
        top = [(x, f(x)) for x in ax]
        c.poly([(a0, 0)] + top + [(a1, 0), (a0, 0)], GOLD, 1.2)
        for i in range(1, 12):  # hatching shows the region without a solid fill
            x = a0 + (a1 - a0) * i / 12
            c.seg((x, 0), (x, f(x)), GOLD, 0.5)
        integral = sum((f(ax[i]) + f(ax[i + 1])) / 2 * (ax[i + 1] - ax[i]) for i in range(k))
        mid = (a0 + a1) / 2
        c.label(mid, f(mid) / 2, f"area ≈ {_fmt(round(integral, 2))}", GOLD, small=True, dy=-c.line * 2)
    if "tangent" in params:
        t = _num(params, "tangent")
        h_ = 1e-4
        slope = (f(t + h_) - f(t - h_)) / (2 * h_)
        yt = f(t)
        half = (hi - lo) * 0.28
        if abs(slope) > 1e-9:  # keep the line inside the graph's height
            half = min(half, abs((y1 - yt) / slope) * 0.95, abs((yt - y0) / slope) * 0.95)
        c.seg((t - half, yt - slope * half), (t + half, yt + slope * half), GOLD, 1.3)
        px, py = c.p(t, yt)
        r = c.line * 3.2
        c.pxcircle(px, py, r, GOLD)
        c.label(t, yt, f"slope = {_fmt(round(slope, 2))}", GOLD, small=True,
                anchor="lt" if slope > 0 else "lb", dx=c.line * 8, dy=c.line * (6 if slope > 0 else -6))
    label = params.get("label") or ("y = " + params.get("f", "x^2").replace("**", "^").replace("^2", "²"))
    c.label(hi, f(hi) if math.isfinite(f(hi)) else y1, label, WHITE, small=True, anchor="rb", dy=-c.line * 6)
    return c


def _axes_stretched(c: Canvas, x0, x1, y0, y1) -> None:
    c.arrow((x0, 0), (x1, 0), DIM, 0.8)
    if x0 <= 0 <= x1:
        c.arrow((0, y0), (0, y1), DIM, 0.8)


def _unit_circle(size, params, items) -> Canvas:
    deg = _num(params, "angle", 30)
    rad = math.radians(deg)
    wave = _yes(params, "wave")
    R = 1.0
    shift, wx = 1.75, 0.55  # the wave starts right of the circle; x units per radian
    right = shift + 2 * math.pi * wx + 0.3 if wave else 1.45
    c = _canvas(size, (-1.45, -1.4, right, 1.4))
    c.arrow((-1.3, 0), (right, 0), DIM, 0.8)
    c.arrow((0, -1.3), (0, 1.3), DIM, 0.8)
    c.arc((0, 0), R, 0, 360, WHITE, 1.1)
    px, py = R * math.cos(rad), R * math.sin(rad)
    c.seg((0, 0), (px, py), WHITE, 1.2)
    c.seg((0, 0), (px, 0), WHITE, 1.0)           # cos
    c.seg((px, 0), (px, py), GOLD, 1.5)          # sin, the key length
    c.arc((0, 0), 0.22, 0, deg, WHITE, 0.9)
    c.label(0.3 * math.cos(rad / 2), 0.3 * math.sin(rad / 2), f"{_fmt(deg)}°", WHITE, small=True, anchor="lm",
            dx=c.line * 2)
    c.label(px / 2, 0, f"cos {_fmt(math.cos(rad))}", WHITE, small=True, anchor="mt", dy=c.line * 7)
    if wave:
        pts = [(shift + wx * t, R * math.sin(t)) for t in [2 * math.pi * i / 180 for i in range(181)]]
        c.poly(pts, WHITE, 1.1)
        wxp = shift + wx * rad
        c.seg((px, py), (wxp, py), DIM, 0.6)
        c.seg((wxp, 0), (wxp, py), GOLD, 1.5)
        c.label(wxp, py, f"sin {_fmt(math.sin(rad))}", GOLD, small=True, anchor="mb", dy=-c.line * 8)
    else:
        c.label(px, py / 2, f"sin {_fmt(math.sin(rad))}", GOLD, small=True, anchor="lm", dx=c.line * 6)
    return c


def _projectile(size, params, items) -> Canvas:
    v, deg = _num(params, "speed"), _num(params, "angle", 45)
    g = _num(params, "g", 9.8)
    if v <= 0 or not 0 < deg < 90 or g <= 0:
        raise FigureError("projectile needs speed > 0 and 0 < angle < 90")
    rad = math.radians(deg)
    flight = 2 * v * math.sin(rad) / g
    reach = v * math.cos(rad) * flight
    peak = (v * math.sin(rad)) ** 2 / (2 * g)
    c = _canvas(size, (-0.08 * reach, -0.18 * max(peak, reach * 0.3), reach * 1.08, peak * 1.3 + 0.1 * reach))
    c.seg((-0.04 * reach, 0), (reach * 1.04, 0), WHITE, 1.0)
    pts = []
    for i in range(121):
        t = flight * i / 120
        pts.append((v * math.cos(rad) * t, v * math.sin(rad) * t - g * t * t / 2))
    c.poly(pts, GOLD, 1.5)
    launch = reach * 0.16
    c.arrow((0, 0), (launch * math.cos(rad), launch * math.sin(rad)), WHITE, 1.2)
    c.arc((0, 0), launch * 0.45, 0, deg, WHITE, 0.8)
    c.label(launch * 0.55 * math.cos(rad / 2), launch * 0.55 * math.sin(rad / 2), f"{_fmt(deg)}°", WHITE,
            small=True, anchor="lm", dx=c.line * 3)
    c.seg((reach / 2, 0), (reach / 2, peak), DIM, 0.6)
    c.label(reach / 2, peak, f"peak {_fmt(round(peak, 1))} m", WHITE, small=True, dy=-c.line * 12)
    c.label(reach, 0, f"{_fmt(round(reach, 1))} m", GOLD, small=True, dy=c.line * 14)
    c.label(launch * math.cos(rad), launch * math.sin(rad), f"{_fmt(v)} m/s", WHITE, small=True,
            anchor="rb", dx=-c.line * 4, dy=-c.line * 4)
    return c


def _beam(size, params, items) -> Canvas:
    length = _num(params, "length", 6)
    load = _num(params, "load", 10)
    at = _num(params, "at", length / 2)
    if not 0 <= at <= length or length <= 0:
        raise FigureError("load position must be on the beam")
    r_right = load * at / length
    r_left = load - r_right
    unit = params.get("unit", "kN")
    c = _canvas(size, (-0.12 * length, -0.42 * length, length * 1.12, 0.42 * length))
    t = length * 0.03
    c.poly([(0, 0), (length, 0), (length, t), (0, t), (0, 0)], WHITE, 1.2)
    s = length * 0.05
    c.poly([(0, 0), (-s, -1.6 * s), (s, -1.6 * s), (0, 0)], WHITE, 1.0)          # pin
    c.poly([(length, 0), (length - s, -1.4 * s), (length + s, -1.4 * s), (length, 0)], WHITE, 1.0)
    for k in (-0.6, 0, 0.6):                                                     # roller wheels
        cx, cy = c.p(length + k * s, -1.75 * s)
        r = s * 0.28 * c.scale
        c.pxcircle(cx, cy, r, WHITE)
    top = length * 0.3
    c.arrow((at, t + top), (at, t + length * 0.01), GOLD, 1.5)
    c.label(at, t + top, f"{_fmt(load)} {unit}", GOLD, small=True, dy=-c.line * 10)
    for x, value in ((0, r_left), (length, r_right)):
        c.arrow((x, -length * 0.32), (x, -1.9 * s), WHITE, 1.1)
        c.label(x, -length * 0.32, f"{_fmt(round(value, 2))} {unit}", WHITE, small=True, dy=c.line * 10)
    c.seg((0, -length * 0.08), (at, -length * 0.08), DIM, 0.5)
    c.label(at / 2, -length * 0.08, f"{_fmt(at)} m", DIM, small=True, dy=c.line * 8)
    c.label(length * 0.8 if at < length * 0.6 else length * 0.2, t, f"{_fmt(length)} m", DIM, small=True,
            dy=-c.line * 9)
    return c


def _forces(size, params, items) -> Canvas:
    raw = items + [f"{v}" for k, v in params.items() if k.startswith("f")]
    forces: list[tuple[float, float]] = []
    for item in raw:
        m = re.fullmatch(r"\s*([\d.]+)\s*(?:n|kn)?\s*@\s*(-?[\d.]+)\s*°?\s*", item.lower())
        if m:
            forces.append((float(m.group(1)), float(m.group(2))))
    if not forces:
        raise FigureError("forces need items like 20@0; 15@120")
    unit = params.get("unit", "N")
    vecs = [(mag * math.cos(math.radians(a)), mag * math.sin(math.radians(a))) for mag, a in forces]
    rx, ry = sum(v[0] for v in vecs), sum(v[1] for v in vecs)
    reach = max([math.hypot(*v) for v in vecs] + [math.hypot(rx, ry), 1e-6])
    c = _canvas(size, (-reach * 1.2, -reach * 1.2, reach * 1.2, reach * 1.2))
    box = reach * 0.12
    c.poly([(-box, -box), (box, -box), (box, box), (-box, box), (-box, -box)], WHITE, 1.1)
    for (mag, a), (vx, vy) in zip(forces, vecs):
        ux, uy = vx / mag, vy / mag
        c.arrow((ux * box, uy * box), (vx + ux * box, vy + uy * box), WHITE, 1.2)
        c.label(vx + ux * box * 2.4, vy + uy * box * 2.4, f"{_fmt(mag)} {unit}", WHITE, small=True)
    net = math.hypot(rx, ry)
    if net > 1e-6:
        ux, uy = rx / net, ry / net
        c.arrow((ux * box, uy * box), (rx + ux * box, ry + uy * box), GOLD, 1.5)
        c.label(rx + ux * box * 2.6, ry + uy * box * 2.6,
                f"net {_fmt(round(net, 1))} {unit} at {_fmt(round(math.degrees(math.atan2(ry, rx)), 1))}°", GOLD,
                small=True)
    else:
        c.label(0, -box * 2.5, f"net = 0 {unit}", GOLD, small=True)
    return c


BUILDERS = {
    "vectors": _vectors, "right_triangle": _right_triangle, "function": _function,
    "unit_circle": _unit_circle, "projectile": _projectile, "beam": _beam, "forces": _forces,
}


def render_figure(spec: str, target: Path, size: tuple[int, int]) -> Path:
    """Draw the figure named by ``spec`` to ``target`` (PNG). Raises FigureError."""
    kind, params, items = parse_figure(spec)
    try:
        canvas = BUILDERS[kind](size, params, items)
    except FigureError:
        raise
    except Exception as exc:  # a bad number or expression must never crash a video
        raise FigureError(f"{kind}: {exc}") from exc
    return _save(canvas, target)


def check_figure(spec: str) -> str:
    """'' when the spec draws, else the reason it cannot."""
    import tempfile

    try:
        with tempfile.TemporaryDirectory() as tmp:
            render_figure(spec, Path(tmp) / "f.png", (512, 512))
        return ""
    except FigureError as exc:
        return str(exc)
