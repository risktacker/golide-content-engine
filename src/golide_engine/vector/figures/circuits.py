"""Circuit figures: a battery with resistors in series or parallel, Ohm's law worked out."""

from __future__ import annotations

from .core import DIM, GOLD, WHITE, Canvas, FigureError, fmt, new_canvas, num


def _resistors(params) -> list[float]:
    raw = params.get("resistors", params.get("r", ""))
    try:
        values = [float(v) for v in raw.replace(" ", "").split(",") if v]
    except ValueError as exc:
        raise FigureError("resistors are numbers in ohms, like 4,2") from exc
    if not 1 <= len(values) <= 4 or any(v <= 0 for v in values):
        raise FigureError("one to four resistors, each above 0 ohms")
    return values


def _zigzag(c: Canvas, a, b, vertical: bool = False) -> None:
    """A resistor symbol between a and b (wire, zigzag, wire)."""
    (x0, y0), (x1, y1) = a, b
    if vertical:
        length = y1 - y0
        lead = length * 0.25
        c.seg((x0, y0), (x0, y0 + lead), WHITE, 1.1)
        pts = [(x0, y0 + lead)]
        for k in range(1, 7):
            pts.append((x0 + (0.18 if k % 2 else -0.18), y0 + lead + (length - 2 * lead) * k / 7))
        pts.append((x0, y1 - lead))
        c.poly(pts, WHITE, 1.2)
        c.seg((x0, y1 - lead), (x0, y1), WHITE, 1.1)
        return
    length = x1 - x0
    lead = length * 0.25
    c.seg((x0, y0), (x0 + lead, y0), WHITE, 1.1)
    pts = [(x0 + lead, y0)]
    for k in range(1, 7):
        pts.append((x0 + lead + (length - 2 * lead) * k / 7, y0 + (0.18 if k % 2 else -0.18)))
    pts.append((x1 - lead, y0))
    c.poly(pts, WHITE, 1.2)
    c.seg((x1 - lead, y0), (x1, y0), WHITE, 1.1)


def _battery(c: Canvas, x: float, y0: float, y1: float, volts: float) -> None:
    mid = (y0 + y1) / 2
    c.seg((x, y0), (x, mid - 0.12), WHITE, 1.1)
    c.seg((x, mid + 0.12), (x, y1), WHITE, 1.1)
    c.seg((x - 0.35, mid + 0.12), (x + 0.35, mid + 0.12), WHITE, 1.4)   # long plate (+)
    c.seg((x - 0.18, mid - 0.12), (x + 0.18, mid - 0.12), WHITE, 2.2)   # short plate (-)
    c.label(x, mid, f"{fmt(volts)} V", WHITE, small=True, anchor="rm", dx=-c.line * 14)


def circuit(size, params, items) -> Canvas:
    volts = num(params, "voltage")
    rs = _resistors(params)
    parallel = params.get("layout", params.get("type", "series")).lower().startswith("par")
    n = len(rs)
    gap = 2.4  # between parallel branches
    width = 2.2 * n if not parallel else gap * n
    c = new_canvas(size, (-1.6, -1.4, width + (1.6 if parallel else 0.6), 3.2))
    top, bottom = 2.4, 0.0
    _battery(c, 0, bottom, top, volts)
    if not parallel:
        total = sum(rs)
        current = volts / total
        x = 0.0
        for r in rs:
            c.seg((x, top), (x + 0.3, top), WHITE, 1.1)
            _zigzag(c, (x + 0.3, top), (x + 2.2, top))
            c.label(x + 1.25, top, f"{fmt(r)} ohms", WHITE, small=True, anchor="mb", dy=-c.line * 9)
            c.label(x + 1.25, top, f"{fmt(current * r)} V", DIM, small=True, anchor="mt", dy=c.line * 9)
            x += 2.2
        c.seg((x, top), (x, bottom), WHITE, 1.1)
        c.seg((x, bottom), (0, bottom), WHITE, 1.1)
        c.arrow((x * 0.65, bottom), (x * 0.35, bottom), GOLD, 1.6)
        c.label(x / 2, bottom, f"current = {fmt(volts)} V ÷ {fmt(total)} ohms = {fmt(current)} A", GOLD,
                small=True, anchor="mt", dy=c.line * 9)
        return c
    inv = sum(1 / r for r in rs)
    total = 1 / inv
    current = volts / total
    right = gap * n
    c.seg((0, top), (right, top), WHITE, 1.1)
    c.seg((0, bottom), (right, bottom), WHITE, 1.1)
    for i, r in enumerate(rs):
        x = gap * (i + 1)
        _zigzag(c, (x, bottom), (x, top), vertical=True)
        c.label(x, top / 2, f"{fmt(r)} ohms", WHITE, small=True, anchor="lm", dx=c.line * 9)
        c.label(x, top / 2, f"{fmt(volts / r)} A", DIM, small=True, anchor="lm", dx=c.line * 9, dy=c.line * 14)
    c.arrow((right * 0.7, bottom), (right * 0.3, bottom), GOLD, 1.6)
    c.label(right / 2, bottom, f"total {fmt(current)} A (combined {fmt(total)} ohms)", GOLD, small=True,
            anchor="mt", dy=c.line * 9)
    return c
