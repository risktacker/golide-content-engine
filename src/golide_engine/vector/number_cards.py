"""Spoken numbers on screen (owner direction 2026-10-18).

"On noting the spoken word like 552 billion, yes, and zoom marking with
highlight." When the narration says a number that matters (a quantity with a
unit, a big figure, a year, a price), it appears big in the scene's accent
colour at the moment it is spoken, while the camera pushes toward the
drawing's glowing part and a ring is drawn around it.

Numbers arrive as words ("two point seven g", "fifty-thousand-dollar") or
digits ("552 billion", "$50,000", "80%"); both are read here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

ONES = {"zero": 0, "nought": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
        "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
        "ninety": 90}
SCALES = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
SCALE_NAMES = {1e6: "MILLION", 1e9: "BILLION", 1e12: "TRILLION"}
UNITS = {
    "percent": "%", "%": "%", "g": "G", "gs": "G", "kilonewtons": "kN", "kilonewton": "kN", "newtons": "N",
    "litres": "LITRES", "liters": "LITRES", "litre": "LITRE", "kilograms": "KG", "kilogram": "KG", "kg": "KG",
    "tonnes": "TONNES", "tons": "TONS", "metres": "METRES", "meters": "METRES", "kilometres": "KM",
    "kilometers": "KM", "km": "KM", "miles": "MILES", "mph": "MPH", "seconds": "SECONDS", "second": "SECOND",
    "minutes": "MINUTES", "hours": "HOURS", "days": "DAYS", "years": "YEARS", "volts": "V", "amps": "A",
    "watts": "W", "kilowatts": "kW", "megawatts": "MW", "gigawatts": "GW", "degrees": "°", "times": "×",
    "users": "USERS", "people": "PEOPLE", "jobs": "JOBS", "parameters": "PARAMETERS", "gigabytes": "GB",
    "terabytes": "TB", "dollars": "$", "dollar": "$", "pounds": "£", "euros": "€", "kwacha": "K",
}
MIN_GAP = 3.5        # seconds between two cards
CARD_HOLD = (1.6, 2.6)  # shortest and longest time a card stays


@dataclass(frozen=True)
class Card:
    text: str
    start: float
    end: float

    def progress(self, t: float) -> float:
        return max(0.0, min(1.0, (t - self.start) / max(0.1, self.end - self.start)))


def _tok(word: str) -> list[str]:
    """'fifty-thousand-dollar,' -> ['fifty', 'thousand', 'dollar']."""
    clean = word.lower().strip(".,!?;:'\"()").replace("’", "'")
    return [p for p in re.split(r"-", clean) if p]


def _digits(token: str) -> float | None:
    raw = token.replace(",", "").lstrip("$£€").rstrip("%")
    try:
        return float(raw)
    except ValueError:
        return None


def _is_num(token: str) -> bool:
    return token in ONES or token in TENS or token in SCALES or token == "hundred" or _digits(token) is not None


def _fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value)):,}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def parse(tokens: list[str]) -> tuple[str, int] | None:
    """Read a number (and its unit) at the start of ``tokens``.
    Returns (display text, tokens consumed) or None."""
    if not tokens or not _is_num(tokens[0]):
        return None
    i, total, current, biggest, decimal, words, digit = 0, 0.0, 0.0, 1.0, "", [], None
    while i < len(tokens):
        t = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        if t == "and" and words and _is_num(nxt) and nxt not in SCALES:
            i += 1
            continue
        if t == "point" and (nxt in ONES or nxt.isdigit()):
            i += 1
            while i < len(tokens) and (tokens[i] in ONES and ONES[tokens[i]] < 10 or tokens[i].isdigit()):
                decimal += str(ONES.get(tokens[i], tokens[i]))
                i += 1
            break
        d = _digits(t)
        if d is not None and not words:
            digit, current = t, d
            words.append(t)
            i += 1
            continue
        if t in ONES:
            current += ONES[t]
        elif t in TENS:
            current += TENS[t]
        elif t == "hundred":
            current = (current or 1) * 100
        elif t in SCALES:
            scale = SCALES[t]
            biggest = max(biggest, scale)
            total += (current or 1) * scale
            current = 0.0
        else:
            break
        words.append(t)
        i += 1
    if not words:
        return None
    value = total + current
    if decimal:
        value = float(f"{int(value)}.{decimal}")
    # Years: "twenty twenty-eight", "nineteen ninety" (two pairs, no hundred or scale).
    spelled = [w for w in words if not w.isdigit()]
    if (len(spelled) in (2, 3) and spelled[0] in {**TENS, **ONES} and "hundred" not in spelled
            and not any(w in SCALES for w in spelled) and not decimal):
        head = TENS.get(spelled[0], ONES.get(spelled[0], 0))
        rest = sum(TENS.get(w, ONES.get(w, 0)) for w in spelled[1:])
        if 10 <= head <= 20 and 10 <= rest < 100 and head * 100 + rest > 1900:
            return f"{head * 100 + rest}", i
    unit = ""
    if i < len(tokens):
        u = tokens[i]
        if u in ("miles", "kilometres") and tokens[i + 1:i + 3] in (["an", "hour"], ["per", "hour"]):
            unit, i = ("MPH" if u == "miles" else "KM/H"), i + 3
        elif u in ("per", "percent") and tokens[i:i + 2] == ["per", "cent"]:
            unit, i = "%", i + 2
        elif u in UNITS:
            unit, i = UNITS[u], i + 1
    if digit and digit.endswith("%"):
        unit = "%"
    if digit and digit.startswith("$"):
        unit = "$"
    if biggest >= 1e6 and not decimal:
        text = f"{_fmt(value / biggest)} {SCALE_NAMES[biggest]}"
    else:
        text = _fmt(value)
    if unit in ("$", "£", "€", "K"):
        text = unit + text
    elif unit in ("%", "×", "°"):
        text += unit
    elif unit:
        text += " " + unit
    worth = bool(unit) or value >= 100 or biggest >= 1e3 or bool(decimal)
    return (text, i) if worth else None


def find_cards(lines) -> list[Card]:
    """Cards for the numbers spoken in ``lines`` (TimedLine objects with word timings)."""
    stream: list[tuple[str, float, float]] = []
    for line in lines:
        for word in getattr(line, "words", []):
            for piece in _tok(word.text):
                stream.append((piece, float(word.start), float(word.end)))
    cards: list[Card] = []
    i = 0
    tokens = [s[0] for s in stream]
    while i < len(stream):
        found = parse(tokens[i:i + 8])
        if found:
            text, used = found
            start = stream[i][1]
            end = stream[min(len(stream) - 1, i + used - 1)][2]
            if not cards or start - cards[-1].start >= MIN_GAP:
                hold = min(CARD_HOLD[1], max(CARD_HOLD[0], end - start + 0.9))
                cards.append(Card(text, start, start + hold))
            i += max(1, used)
        else:
            i += 1
    return cards
