"""Numbers in scripts are written as digits (owner direction 2026-10-27).

"Every number has to be written as number, not in words... it's giving me hard time to
read numbers as text." The script writer is told to use digits; this converter makes sure,
turning spelled-out numbers into digits after every script draft:

    "sixteen point three billion dollars" -> "16.3 billion dollars"
    "October twenty-sixth, twenty twenty-six" -> "October 26th, 2026"
    "eighty-five percent" -> "85 percent"      "four robots" -> "4 robots"

"one" on its own stays a word ("one of them", "no one", "one-time"); it becomes 1 only as
part of a bigger number ("one hundred", "one point four").
"""

from __future__ import annotations

import re

UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
         "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
            "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
            "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19,
            "twentieth": 20, "thirtieth": 30}
SCALES = {"hundred": 100, "thousand": 1000}
BIG = {"million", "billion", "trillion"}           # kept as words after the digits: "16.3 billion"
MONTHS = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"}

NUMBER_WORD = "|".join(sorted(list(UNITS) + list(TENS) + list(SCALES) + list(ORDINALS), key=len, reverse=True))
TOKEN = re.compile(rf"\b(?:(?:{NUMBER_WORD})(?:-(?:{NUMBER_WORD}))?)\b|\band\b|\bpoint\b|\ba\b", re.I)
RUN = re.compile(
    rf"\b(?:{NUMBER_WORD})(?:[- ](?:{NUMBER_WORD}))*(?:\s+point(?:\s+(?:{NUMBER_WORD}))+)?"
    rf"(?:\s+(?:and\s+)?(?:{NUMBER_WORD})(?:[- ](?:{NUMBER_WORD}))*)*\b", re.I)


def _suffix(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _parse_int(words: list[str]) -> tuple[int, bool] | None:
    """Words of one whole number -> (value, ordinal)."""
    total, current, ordinal = 0, 0, False
    for w in words:
        if w in UNITS:
            current += UNITS[w]
        elif w in TENS:
            current += TENS[w]
        elif w in ORDINALS:
            current += ORDINALS[w]
            ordinal = True
        elif w == "hundred":
            current = max(1, current) * 100
        elif w == "thousand":
            total += max(1, current) * 1000
            current = 0
        else:
            return None
    return total + current, ordinal


def _year(words: list[str]) -> int | None:
    """'twenty twenty-six' -> 2026, 'nineteen ninety' -> 1990."""
    if len(words) < 2 or words[0] not in ("nineteen", "twenty") or words[1] in ("hundred", "thousand"):
        return None
    head = UNITS.get(words[0]) or TENS.get(words[0])
    rest = _parse_int(words[1:])
    if rest is None or rest[1] or not 10 <= rest[0] <= 99:
        return None
    return head * 100 + rest[0]


def _convert(match: re.Match, text: str) -> str:
    raw = match.group(0)
    words = [w for w in re.split(r"[\s-]+", raw.lower()) if w and w != "and"]
    if not words:
        return raw
    if "point" in words:
        i = words.index("point")
        whole = _parse_int(words[:i])
        digits = [str(UNITS[w]) for w in words[i + 1:] if w in UNITS and UNITS[w] < 10]
        if whole is None or not digits or len(digits) != len(words[i + 1:]):
            return raw
        return f"{whole[0]}.{''.join(digits)}"
    year = _year(words)
    if year is not None and 1900 <= year <= 2099:
        return str(year)
    after = text[match.end():].lstrip().split(" ")[0].lower().strip(",.") if match.end() < len(text) else ""
    if after in ("thirds", "quarters", "halves", "fifths", "tenths"):
        return raw      # 2026-10-30: fractions are said as words ("two thirds")
    parsed = _parse_int(words)
    if parsed is None:
        return raw
    value, ordinal = parsed
    if words == ["one"] or (ordinal and len(words) == 1 and value < 10):
        # "one" alone and "first"/"second" are words in normal speech; dates are handled below.
        before = text[:match.start()].rstrip().split(" ")[-1].lower().strip(",") if match.start() else ""
        if not (ordinal and before in MONTHS):
            return raw
    if ordinal:
        return f"{value}{_suffix(value)}"
    return f"{value:,}" if value >= 10000 else str(value)


def digits(text: str) -> str:
    """Spelled-out numbers in ``text`` written as digits."""
    text = re.sub(r"\b([Aa]) (hundred|thousand)\b", lambda m: ("One " if m.group(1) == "A" else "one ") + m.group(2), text)
    out, last = [], 0
    for match in RUN.finditer(text):
        out.append(text[last:match.start()])
        out.append(_convert(match, text))
        last = match.end()
    out.append(text[last:])
    return "".join(out)


def plan_digits(plan: dict) -> dict:
    """The same plan with every line's text and emphasis written with digits."""
    lines = []
    for line in plan.get("lines", []):
        text = digits(str(line.get("text", "")))
        emphasis = digits(str(line.get("emphasis", "")))
        if emphasis and emphasis.lower() not in text.lower():
            emphasis = str(line.get("emphasis", ""))
        lines.append(dict(line, text=text, emphasis=emphasis if emphasis.lower() in text.lower() else line.get("emphasis", "")))
    return dict(plan, lines=lines)
