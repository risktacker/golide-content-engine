"""Thumbnail words (owner direction 2026-10-21).

"The caption type is better for a normal static post, but for us it's simple: 1
to 2 or 3 words of catch and curiosity." The thumbnail carries ONE to THREE huge
words on the dark left side, stacked, heavy and uppercase: white, with the punch
word in the glow colour and a soft glow of its own. The object fills the right.
Nothing goes in the bottom-right corner, where YouTube prints the duration.
The image model never draws text; it is typeset here.
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..theme import load_theme

GOLD = (233, 196, 106)
WHITE = (246, 244, 238)
MAX_WORDS = 3
TEXT_SIDE = 0.44      # the words live in the left 44 percent
BLOCK_HEIGHT = 0.62   # and take at most this share of the height


def _words(text: str) -> list[str]:
    return [w for w in re.sub(r"[^\w'$%&?!.\- ]", " ", text).split() if w]


def thumbnail_words(text: str, punch: str = "") -> list[tuple[str, bool]]:
    """Up to MAX_WORDS uppercase words as (word, is_punch); one punch word at least."""
    words = [w.upper() for w in _words(text)][:MAX_WORDS]
    key = lambda w: w.strip(".,!?").upper()  # noqa: E731
    marked = {key(w) for w in _words(punch)}
    pairs = [(w, key(w) in marked) for w in words]
    if pairs and not any(b for _, b in pairs):
        pairs[-1] = (pairs[-1][0], True)
    return pairs


def stamp_thumbnail(path: Path, text: str, punch: str = "", palette: list | None = None) -> None:
    """Typeset 1 to 3 huge words on the left. palette: RGB accents; the first colours the punch."""
    pairs = thumbnail_words(text, punch)
    if not pairs:
        return
    accent = tuple((palette or [GOLD])[0])
    image = Image.open(path).convert("RGB")
    w, h = image.size
    # Darken the left so the words always read, whatever the art does there.
    shade = Image.new("L", (w, h), 0)
    ds = ImageDraw.Draw(shade)
    for x in range(int(w * 0.58)):
        ds.line([(x, 0), (x, h)], fill=int(185 * (1 - x / (w * 0.58)) ** 1.3))
    image = Image.composite(Image.new("RGB", (w, h), (8, 8, 11)), image, shade)

    font_path = str(load_theme().font("bold"))
    probe = ImageDraw.Draw(image)
    # One word per line when short words would otherwise run too wide.
    lines = [[p] for p in pairs] if len(pairs) > 1 else [pairs]
    size = int(h * 0.30)
    while size > h * 0.08:
        font = ImageFont.truetype(font_path, size)
        widest = max(probe.textlength(" ".join(word for word, _ in line), font=font) for line in lines)
        if widest <= w * (TEXT_SIDE - 0.06) and len(lines) * size * 1.02 <= h * BLOCK_HEIGHT:
            break
        size -= 4
    font = ImageFont.truetype(font_path, size)

    text_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dt, dg = ImageDraw.Draw(text_layer), ImageDraw.Draw(glow_layer)
    space = dt.textlength(" ", font=font)
    block = len(lines) * size * 1.02
    y = (h - block) / 2 - h * 0.03
    for line in lines:
        x = w * 0.06
        for word, bold in line:
            color = accent if bold else WHITE
            if bold:
                dg.text((x, y), word, font=font, fill=accent + (200,))
            dt.text((x, y), word, font=font, fill=color + (255,), stroke_width=max(2, size // 40),
                    stroke_fill=(0, 0, 0, 160))
            x += dt.textlength(word, font=font) + space
        y += size * 1.02
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(size / 7))
    out = Image.alpha_composite(image.convert("RGBA"), glow_layer)
    out = Image.alpha_composite(out, text_layer).convert("RGB")
    out.save(path)
