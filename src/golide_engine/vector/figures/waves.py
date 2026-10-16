"""Wave figures: a wave with its wavelength and amplitude, and the electromagnetic spectrum."""

from __future__ import annotations

import math

from .core import DIM, GOLD, WHITE, Canvas, FigureError, fmt, new_canvas, num

# Electromagnetic bands by wavelength in metres (long to short).
BANDS = [("radio", 1e3, 1e-1), ("microwave", 1e-1, 1e-3), ("infrared", 1e-3, 7e-7), ("visible", 7e-7, 4e-7),
         ("ultraviolet", 4e-7, 1e-8), ("X-ray", 1e-8, 1e-11), ("gamma", 1e-11, 1e-13)]
SHORT_NAMES = {"ultraviolet": "UV"}
ABOVE = {"microwave", "ultraviolet"}
TICKS = [(3, "1 km"), (-1, "10 cm"), (-5, "10 µm"), (-9, "1 nm"), (-13, "0.1 pm")]
VISIBLE = [(700, (235, 64, 52)), (620, (245, 140, 40)), (580, (245, 215, 60)), (530, (80, 200, 90)),
           (480, (60, 170, 230)), (450, (80, 90, 225)), (400, (155, 85, 215))]


def wave(size, params, items) -> Canvas:
    """y = A sin(2πx/λ): λ crest to crest, A from the middle line; v = fλ when f is given."""
    lam, amp = num(params, "wavelength"), num(params, "amplitude", 1.0)
    cycles = num(params, "cycles", 2.5)
    if lam <= 0 or amp <= 0 or not 0.5 <= cycles <= 8:
        raise FigureError("wavelength and amplitude must be positive, cycles 0.5 to 8")
    unit = params.get("unit", "m")
    length = lam * cycles
    c = new_canvas(size, (-0.08 * length, -amp * 2.0, length * 1.05, amp * 2.3), stretch=True)
    c.seg((0, 0), (length, 0), DIM, 0.7)
    pts = [(length * i / 400, amp * math.sin(2 * math.pi * (length * i / 400) / lam)) for i in range(401)]
    c.poly(pts, GOLD, 1.5)
    crest = lam / 4
    y = amp * 1.35
    c.dashed((crest, amp), (crest, y), DIM, 0.6)
    c.dashed((crest + lam, amp), (crest + lam, y), DIM, 0.6)
    c.arrow((crest + lam / 2, y), (crest, y), WHITE, 1.0)
    c.arrow((crest + lam / 2, y), (crest + lam, y), WHITE, 1.0)
    c.label(crest + lam / 2, y, f"wavelength {fmt(lam)} {unit}", WHITE, small=True, anchor="mb", dy=-c.line * 5)
    x = crest + lam * 2 if cycles >= 2.3 else crest
    c.arrow((x + lam * 0.12, 0), (x + lam * 0.12, amp), WHITE, 1.0)
    c.label(x + lam * 0.12, amp / 2, f"amplitude {fmt(amp)} {unit}", WHITE, small=True, anchor="lm",
            dx=c.line * 5)
    if "frequency" in params:
        freq = num(params, "frequency")
        c.label(length / 2, -amp * 1.6, f"speed = {fmt(freq)} Hz × {fmt(lam)} {unit} = {fmt(freq * lam)} {unit}/s",
                GOLD, small=True)
    return c


def spectrum(size, params, items) -> Canvas:
    """The electromagnetic spectrum on a true log scale of wavelength, with the visible band opened up."""
    highlight = params.get("highlight", "visible").strip().lower()
    hi_log, lo_log = 3.0, -13.0
    span = hi_log - lo_log
    c = new_canvas(size, (-0.6, -6.2, span + 0.6, 3.0))

    def x_of(metres: float) -> float:
        return hi_log - math.log10(metres)

    c.poly([(0, 0), (span, 0), (span, 1), (0, 1), (0, 0)], WHITE, 1.1)
    for row, (name, long, short) in enumerate(BANDS):
        x0, x1 = x_of(long), x_of(short)
        if x0 > 0:
            c.seg((x0, 0), (x0, 1), WHITE, 0.9)
        if name == "visible":
            continue  # opened up below
        color = GOLD if name.lower() == highlight else WHITE
        # Narrow bands are named just above the band, wide ones inside it.
        c.label((x0 + x1) / 2, 1.25 if name in ABOVE else 0.5, SHORT_NAMES.get(name, name), color, small="tiny")
    for exp, text in TICKS:
        c.seg((x_of(10.0 ** exp), 0), (x_of(10.0 ** exp), -0.18), DIM, 0.7)
        c.label(x_of(10.0 ** exp), -0.2, text, DIM, small="tiny", anchor="mt")
    # A wave whose wavelength shrinks from left to right, above the band.
    pts, x = [], 0.0
    phase = 0.0
    while x <= span:
        local = 2.0 * (0.14 / 2.0) ** (x / span)  # drawn wavelength: 2 units down to 0.14
        pts.append((x, 1.9 + 0.4 * math.sin(phase)))
        phase += 2 * math.pi * 0.01 / local
        x += 0.01
    c.poly(pts, WHITE, 0.9)
    c.label(0, 2.6, "long waves", DIM, small=True, anchor="lm")
    c.label(span, 2.6, "short waves", DIM, small=True, anchor="rm")
    # The visible band, opened up below: 700 nm (red) to 400 nm (violet).
    v0, v1 = x_of(7e-7), x_of(4e-7)
    left, right = span * 0.2, span * 0.8
    c.dashed((v0, 0), (left, -2.6), DIM, 0.6)
    c.dashed((v1, 0), (right, -2.6), DIM, 0.6)
    steps = 60
    for i in range(steps):
        nm = 700 - 300 * i / (steps - 1)
        rgb = _colour(nm)
        x = left + (right - left) * i / (steps - 1)
        c.seg((x, -2.6), (x, -4.0), rgb, 2.2)
    c.label(left, -4.1, "700 nm", (235, 64, 52), small=True, anchor="mt")
    c.label(right, -4.1, "400 nm", (155, 85, 215), small=True, anchor="mt")
    c.label((left + right) / 2, -4.9, "visible light", GOLD if highlight == "visible" else WHITE, small=True)
    return c


def _colour(nm: float) -> tuple[int, int, int]:
    for (n0, c0), (n1, c1) in zip(VISIBLE, VISIBLE[1:]):
        if n1 <= nm <= n0:
            t = (n0 - nm) / (n0 - n1)
            return tuple(int(a + (b - a) * t) for a, b in zip(c0, c1))
    return VISIBLE[-1][1] if nm < 400 else VISIBLE[0][1]
