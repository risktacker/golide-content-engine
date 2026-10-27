"""Money and markets, drawn exactly (owner direction 2026-10-27).

"When it comes to money... our drawings are fumbling." Prices, growth and market moves are
numbers, so they are drawn here from the numbers the lines say, never guessed by the image
model: a line chart, bars, or market candles. Teal is growth, rose is a fall or a risk, gold
is the value the viewer should remember. Labels are placed by the canvas clear of every line.

    chart: type=candles; values=100,104,101,108,115,111,120; unit=$; label=NVDA
    chart: type=bar; values=12,18,25,40; labels=2023,2024,2025,2026; unit=bn $
    chart: type=line; values=1.2,1.5,2.1,3.4; labels=Q1,Q2,Q3,Q4; unit=%
"""

from __future__ import annotations

from .core import DIM, GOLD, WHITE, FigureError, fmt, new_canvas

TEAL = (110, 220, 200)
ROSE = (240, 138, 128)


def _values(params: dict) -> list[float]:
    try:
        values = [float(v) for v in str(params.get("values", "")).replace(" ", "").split(",") if v]
    except ValueError as exc:
        raise FigureError("values must be numbers separated by commas") from exc
    if not 2 <= len(values) <= 24:
        raise FigureError("a chart needs 2 to 24 values")
    return values


def chart(size, params, items):
    kind = str(params.get("type", "line")).strip().lower()
    values = _values(params)
    labels = [s.strip() for s in str(params.get("labels", "")).split(",") if s.strip()]
    unit = str(params.get("unit", "")).strip()
    n = len(values)
    lo, hi = min(values), max(values)
    if kind == "bar":
        lo = min(0.0, lo)
    span = (hi - lo) or abs(hi) or 1.0
    top, bottom = hi + span * 0.25, lo - span * (0.18 if kind != "bar" else 0.0)
    c = new_canvas(size, (-0.8, bottom - span * 0.22, n + 0.4, top), stretch=True)
    c.seg((-0.2, bottom), (n, bottom), DIM, 0.8)
    c.seg((-0.2, bottom), (-0.2, top - span * 0.1), DIM, 0.8)
    rising = values[-1] >= values[0]
    main = TEAL if rising else ROSE
    if kind == "bar":
        for i, v in enumerate(values):
            x0, x1 = i + 0.18, i + 0.82
            colour = GOLD if i == n - 1 else WHITE
            c.poly([(x0, 0), (x0, v), (x1, v), (x1, 0)], colour, 1.2)
            if i < n - 1:  # the last bar carries the end label below
                c.label(i + 0.5, v, f"{fmt(v)}", colour, small=True, anchor="mb", dy=-c.line * 4)
    elif kind == "candles":
        prev = values[0] - (values[1] - values[0]) * 0.5
        for i, close in enumerate(values):
            open_ = prev
            up = close >= open_
            colour = TEAL if up else ROSE
            body_lo, body_hi = min(open_, close), max(open_, close)
            wick = span * 0.05
            c.seg((i + 0.5, body_lo - wick), (i + 0.5, body_hi + wick), colour, 0.9)
            if body_hi - body_lo < span * 0.01:
                body_hi = body_lo + span * 0.01
            c.poly([(i + 0.25, body_lo), (i + 0.25, body_hi), (i + 0.75, body_hi), (i + 0.75, body_lo),
                    (i + 0.25, body_lo)], colour, 1.2)
            prev = close
        trend = [(i + 0.5, sum(values[max(0, i - 2):i + 1]) / len(values[max(0, i - 2):i + 1])) for i in range(n)]
        c.poly(trend, GOLD, 1.4)
    else:
        pts = [(i + 0.5, v) for i, v in enumerate(values)]
        c.poly(pts, main, 1.6)
        for x, y in pts:
            c.dot(x, y, main, 3.0)
    for i, text in enumerate(labels[:n]):
        c.label(i + 0.5, bottom, text, DIM, small=True, anchor="mt", dy=c.line * 4)
    change = (values[-1] - values[0]) / abs(values[0]) * 100 if values[0] else 0.0
    name = str(params.get("label", "")).strip()
    end = f"{unit}{fmt(values[-1])}" if unit in ("$", "€", "£", "K") else f"{fmt(values[-1])} {unit}".strip()
    if kind == "bar":
        c.label(n - 0.5, values[-1], end, GOLD, small=False, anchor="mb", dy=-c.line * 4)
    else:
        c.label(n - 0.5, values[-1], end, GOLD, small=False, anchor="lb", dx=c.line * 5, dy=-c.line * 4)
    sign = "+" if change >= 0 else ""
    pct = f"{sign}{fmt(change, 1 if abs(change) < 10 else 0)}%"
    head = f"{name}  {pct}" if name else pct
    c.label(n / 2, top - span * 0.08, head, main, small=False, anchor="mm")
    return c
