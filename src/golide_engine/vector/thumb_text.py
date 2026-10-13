"""Big, bold thumbnail words (owner direction 2026-10-13).

The YouTube thumbnail is the same kind of art as the Instagram covers, so the
picture carries it and the text stays tiny in count: 2 to 4 words, set huge on
the clean left side, white with the punch in gold. The image model never draws
text; it is typeset here.
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..theme import load_theme

GOLD = (233, 196, 106)
WHITE = (246, 244, 238)


def thumbnail_words(text: str, gold: str) -> tuple[list[str], set[str]]:
    """2 to 4 words to stamp, and which of them are gold."""
    clean = lambda s: [w for w in re.sub(r"[^\w'$%&\- ]", " ", s).split() if w]
    punch = clean(gold)
    words = punch if 2 <= len(punch) <= 4 else clean(text)[:4]
    if len(words) == 1 and clean(text):
        words = clean(text)[:3]
    gold_set = {w.upper() for w in punch}
    upper = [w.upper() for w in words]
    if set(upper) <= gold_set:  # all punch: white words, the last one in gold
        gold_set = {upper[-1]}
    return upper, gold_set


def stamp_thumbnail(path: Path, text: str, gold: str) -> None:
    words, gold_set = thumbnail_words(text, gold)
    if not words:
        return
    image = Image.open(path).convert("RGB")
    w, h = image.size
    # Darken the left side so the words always read, whatever the art does there.
    shade = Image.new("L", (w, h), 0)
    ds = ImageDraw.Draw(shade)
    for x in range(int(w * 0.55)):
        ds.line([(x, 0), (x, h)], fill=int(170 * (1 - x / (w * 0.55)) ** 1.4))
    image = Image.composite(Image.new("RGB", (w, h), (8, 8, 11)), image, shade)

    font_path = str(load_theme().font("bold"))
    max_w, max_h = w * 0.44, h * 0.70
    lines: list[list[str]] = []
    size = 150
    while size > 40:
        font = ImageFont.truetype(font_path, size)
        probe = ImageDraw.Draw(image)
        lines, current = [], []
        for word in words:
            trial = current + [word]
            if current and probe.textlength(" ".join(trial), font=font) > max_w:
                lines.append(current)
                current = [word]
            else:
                current = trial
        lines.append(current)
        widest = max(probe.textlength(" ".join(line), font=font) for line in lines)
        height = len(lines) * size * 1.05
        if widest <= max_w and height <= max_h and len(lines) <= 3:
            break
        size -= 6

    font = ImageFont.truetype(font_path, size)
    text_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dt, dg = ImageDraw.Draw(text_layer), ImageDraw.Draw(glow_layer)
    space = dt.textlength(" ", font=font)
    total = len(lines) * size * 1.05
    y = (h - total) / 2
    for line in lines:
        x = w * 0.06
        for word in line:
            color = GOLD if word.strip(".,!?") in gold_set else WHITE
            dg.text((x, y), word, font=font, fill=color + (200,))
            dt.text((x, y), word, font=font, fill=color + (255,), stroke_width=2, stroke_fill=(0, 0, 0, 180))
            x += dt.textlength(word, font=font) + space
        y += size * 1.05
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(size / 7))
    out = Image.alpha_composite(image.convert("RGBA"), glow_layer)
    out = Image.alpha_composite(out, text_layer).convert("RGB")
    out.save(path)
