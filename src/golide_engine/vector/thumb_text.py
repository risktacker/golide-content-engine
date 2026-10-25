"""Thumbnail words (owner direction 2026-10-21, changed 2026-10-25).

2026-10-25: "those first block that you are adding to the video itself... those texts are
powerful... our thumbnail, we restricted it to like two or three words... who taught it,
who decides... kind of repetitive." The thumbnail now carries the same line as the video's
opening card: a 3 to 6 word claim or question, in its own case, wrapped over up to three
lines on the dark left side, with the punch words in the glow colour. The object fills the
right. Nothing goes in the bottom-right corner, where YouTube prints the duration. The
image model never draws text; it is typeset here.
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..theme import load_theme

GOLD = (233, 196, 106)
WHITE = (246, 244, 238)
MAX_WORDS = 7
MAX_LINES = 3
TEXT_SIDE = 0.47      # the words live in the left 47 percent
BLOCK_HEIGHT = 0.66   # and take at most this share of the height


def _words(text: str) -> list[str]:
    return [w for w in re.sub(r"[^\w'$%&?!.,:\- ]", " ", text).split() if w]


def _key(word: str) -> str:
    return word.strip(".,!?:").lower()


def thumbnail_words(text: str, punch: str = "") -> list[tuple[str, bool]]:
    """The line's words, as written, as (word, is_punch); at least one punch word."""
    words = _words(text)[:MAX_WORDS]
    marked = {_key(w) for w in _words(punch)}
    pairs = [(w, _key(w) in marked) for w in words]
    if pairs and not any(b for _, b in pairs):
        pairs[-1] = (pairs[-1][0], True)
    return pairs


def _wrap(pairs, font, probe, max_w):
    lines: list[list[tuple[str, bool]]] = [[]]
    for pair in pairs:
        trial = " ".join(w for w, _ in lines[-1] + [pair])
        if lines[-1] and probe.textlength(trial, font=font) > max_w:
            lines.append([pair])
        else:
            lines[-1].append(pair)
    return lines


def stamp_thumbnail(path: Path, text: str, punch: str = "", palette: list | None = None) -> None:
    """Typeset the line large on the left. palette: RGB accents; the first colours the punch."""
    pairs = thumbnail_words(text, punch)
    if not pairs:
        return
    accent = tuple((palette or [GOLD])[0])
    image = Image.open(path).convert("RGB")
    w, h = image.size
    # Darken the left so the words always read, whatever the art does there.
    shade = Image.new("L", (w, h), 0)
    ds = ImageDraw.Draw(shade)
    for x in range(int(w * 0.60)):
        ds.line([(x, 0), (x, h)], fill=int(190 * (1 - x / (w * 0.60)) ** 1.3))
    image = Image.composite(Image.new("RGB", (w, h), (8, 8, 11)), image, shade)

    font_path = str(load_theme().font("bold"))
    probe = ImageDraw.Draw(image)
    max_w = w * (TEXT_SIDE - 0.06)
    size = int(h * 0.26)
    while True:
        font = ImageFont.truetype(font_path, size)
        lines = _wrap(pairs, font, probe, max_w)
        widest = max(probe.textlength(" ".join(word for word, _ in line), font=font) for line in lines)
        if (len(lines) <= MAX_LINES and widest <= max_w and len(lines) * size * 1.08 <= h * BLOCK_HEIGHT) \
                or size <= h * 0.08:
            break
        size -= 3

    text_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dt, dg = ImageDraw.Draw(text_layer), ImageDraw.Draw(glow_layer)
    space = dt.textlength(" ", font=font)
    block = len(lines) * size * 1.08
    y = (h - block) / 2 - h * 0.03
    for line in lines:
        x = w * 0.06
        for word, bold in line:
            color = accent if bold else WHITE
            dg.text((x, y), word, font=font, fill=color + (200 if bold else 90,))
            dt.text((x, y), word, font=font, fill=color + (255,), stroke_width=max(2, size // 40),
                    stroke_fill=(0, 0, 0, 160))
            x += dt.textlength(word, font=font) + space
        y += size * 1.08
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(size / 7))
    out = Image.alpha_composite(image.convert("RGBA"), glow_layer)
    out = Image.alpha_composite(out, text_layer).convert("RGB")
    out.save(path)
