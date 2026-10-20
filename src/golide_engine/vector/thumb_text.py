"""Thumbnail text, set like the static posts (owner direction 2026-10-20).

The posts read: "OpenCode says **AI keys** were exposed." One short line under
the picture, centred: plain words in a light weight, the punch words in bold in
the glow colour with a soft glow of their own. The thumbnail does the same with
the cover hook (3 to 7 words), sized for a phone. The image model never draws
text; it is typeset here.
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..theme import load_theme

GOLD = (233, 196, 106)
WHITE = (246, 244, 238)
MAX_WORDS = 7
BAND_TOP = 0.72        # the text lives in the bottom 28 percent
MAX_LINES = 2


def _words(text: str) -> list[str]:
    return [w for w in re.sub(r"[^\w'$%&.,!?\- ]", " ", text).split() if w]


def thumbnail_line(text: str, gold: str) -> list[tuple[str, bool]]:
    """The hook as (word, is_punch) pairs; at most MAX_WORDS words, punch words kept."""
    words = _words(text)
    key = lambda w: w.lower().strip(".,!?")  # noqa: E731
    punch = {key(w) for w in _words(gold)}
    if len(words) > MAX_WORDS:
        first = next((i for i, w in enumerate(words) if key(w) in punch), 0)
        start = max(0, min(first - 2, len(words) - MAX_WORDS))
        words = words[start:start + MAX_WORDS]
    pairs = [(w, key(w) in punch) for w in words]
    if pairs and not any(p for _, p in pairs):
        pairs[-1] = (pairs[-1][0], True)   # always one bold word to land on
    return pairs


def _layout(pairs, fonts, width, draw):
    """Greedy lines that fit ``width``; None when they do not fit in MAX_LINES."""
    space = draw.textlength(" ", font=fonts[False])
    lines, line, used = [], [], 0.0
    for word, bold in pairs:
        w = draw.textlength(word, font=fonts[bold])
        extra = w + (space if line else 0)
        if line and used + extra > width:
            lines.append((line, used))
            line, used = [], 0.0
            extra = w
        line.append((word, bold, w))
        used += extra
    if line:
        lines.append((line, used))
    if len(lines) > MAX_LINES or any(u > width for _, u in lines):
        return None
    return lines, space


def stamp_thumbnail(path: Path, text: str, gold: str, palette: list | None = None) -> None:
    """Typeset the hook under the picture. palette: RGB accents; the first colours the punch."""
    pairs = thumbnail_line(text, gold)
    if not pairs:
        return
    accent = tuple((palette or [GOLD])[0])
    image = Image.open(path).convert("RGB")
    w, h = image.size
    # Darken the bottom band so the words always read, whatever the art does there.
    shade = Image.new("L", (w, h), 0)
    ds = ImageDraw.Draw(shade)
    top = int(h * (BAND_TOP - 0.10))
    for y in range(top, h):
        ds.line([(0, y), (w, y)], fill=int(205 * min(1.0, (y - top) / (h * 0.16)) ** 1.3))
    image = Image.composite(Image.new("RGB", (w, h), (8, 8, 11)), image, shade)

    theme = load_theme()
    probe = ImageDraw.Draw(image)
    size = int(h * 0.088)
    while True:
        fonts = {False: ImageFont.truetype(str(theme.font("light")), size),
                 True: ImageFont.truetype(str(theme.font("bold")), size)}
        fitted = _layout(pairs, fonts, w * 0.86, probe)
        if fitted and len(fitted[0]) * size * 1.18 <= h * (1 - BAND_TOP) - h * 0.04 or size <= h * 0.05:
            break
        size -= 2
    lines, space = fitted or ([([(word, bold, probe.textlength(word, font=fonts[bold])) for word, bold in pairs],
                                w * 0.86)], probe.textlength(" ", font=fonts[False]))

    text_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dt, dg = ImageDraw.Draw(text_layer), ImageDraw.Draw(glow_layer)
    block = len(lines) * size * 1.18
    y = h * BAND_TOP + (h * (1 - BAND_TOP) - block) / 2 - h * 0.01
    for line, used in lines:
        x = (w - used) / 2
        for word, bold, width in line:
            color = accent if bold else WHITE
            if bold:
                dg.text((x, y), word, font=fonts[True], fill=accent + (190,))
            dt.text((x, y), word, font=fonts[bold], fill=color + (255,))
            x += width + space
        y += size * 1.18
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(size / 6))
    out = Image.alpha_composite(image.convert("RGBA"), glow_layer)
    out = Image.alpha_composite(out, text_layer).convert("RGB")
    out.save(path)
