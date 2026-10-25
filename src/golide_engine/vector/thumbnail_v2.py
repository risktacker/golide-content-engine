"""Thumbnails drawn from the real product (owner direction 2026-10-25).

"The car no sign of thrusters and real Roadster, the Microducks opposite... the text
should overlap with the image art but well designed." The image model only had words,
so it guessed what a brand-new product looks like (a robot dog for the two-legged
Microduck, the 2008 Roadster with a jet for the new one). Now:

* the trending video we model shows the real product in its thumbnail; that image is
  handed to the image model as a reference: draw THIS product, in our style, never
  copying its text, faces, logos or layout;
* the subject comes in larger and reaches toward the middle, and the line is set over
  the dark edge of it with a soft shadow, so words and picture are one design.
"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..theme import load_theme
from .thumb_text import GOLD, WHITE, thumbnail_words
from .thumbnail_style import GLOW_WORDS

REFERENCE_SIZES = ("maxresdefault", "sddefault", "hqdefault")


def video_id(url: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url or "")
    return match.group(1) if match else ""


def fetch_reference(url: str, dest: Path) -> Path | None:
    """The source video's own thumbnail (the real product), or None."""
    vid = video_id(url)
    if not vid:
        return None
    for size in REFERENCE_SIZES:
        try:
            with urllib.request.urlopen(f"https://i.ytimg.com/vi/{vid}/{size}.jpg", timeout=20) as response:
                data = response.read()
        except Exception:  # noqa: BLE001 - try the next size, then go without
            continue
        if len(data) > 5000:  # YouTube answers a missing size with a tiny grey placeholder
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return dest
    return None


def thumbnail_prompt_v2(title: str, moment: str, colors: list[str], has_reference: bool) -> str:
    subject = moment.strip() or f"the one object the story is about: {title}"
    names = [GLOW_WORDS.get(c, c) for c in colors] or [GLOW_WORDS["gold"]]
    glow, rim = names[0], (names[1] if len(names) > 1 else names[0])
    reference = (
        "REFERENCE IMAGE: it shows the real product this video is about. Draw THAT exact product: "
        "its real shape, proportions, number of legs or wheels, colours of its parts and its "
        "distinctive details, so anyone who has seen it recognises it at once. Take ONLY the "
        "product from it: never copy its text, logos, faces, people, background, arrows or layout. "
        if has_reference else
        "If it is a real, named product, draw THAT product with its real, recognisable design. "
    )
    return (
        "16:9 YouTube thumbnail in a premium editorial poster style. Pure black deep-space "
        "background (#0B0B0E) with a very faint, sparse starfield. "
        f"ONE hero subject: {subject}. " + reference +
        "Render it as a cinematic, softly lit real object with fine luminous edge lines (real, but in "
        "a calm night style, not a cartoon), large and slightly angled toward the camera, filling the right "
        "55 percent of the frame top to bottom, crisp at phone size. "
        "Draw its mechanisms as they really look (compressed-air nozzles or fans, not rocket flames). "
        f"Exactly ONE key part glows {glow} with a neon-like inner light; a soft {glow} halo fades "
        f"behind it, a subtle {rim} rim light traces its edges, a faint pool of light beneath it. "
        "The left 42 percent of the frame stays completely dark and empty: big words go there and "
        "nothing of the subject may reach into it. One subject only, no clutter. "
        "No faces, no people, no avatars, no characters. "
        "ABSOLUTELY NO text, letters, words, numbers, logos, watermarks, user-interface elements or "
        f"borders anywhere in the image. Video title for context only: {title}"
    )


def art_left_edge(image: Image.Image, top: float = 0.12, bottom: float = 0.88) -> float:
    """Share of the width where the subject begins (2026-10-25: "text is overlapping and
    hiding the art"): the first column, from the left, with real bright detail."""
    import numpy as np
    gray = np.asarray(image.convert("L"), np.float32)
    h, w = gray.shape
    band = gray[int(h * top):int(h * bottom)]
    lit = (band > 70).sum(axis=0) > band.shape[0] * 0.02
    cols = np.nonzero(lit[int(w * 0.25):])[0]
    return (cols[0] + int(w * 0.25)) / w if len(cols) else 0.6


def stamp_overlap(path: Path, text: str, punch: str = "", palette: list | None = None) -> None:
    """Set the line large on the dark left, sized so it ends before the art begins, with a
    soft shadow and glow so words and picture read as one design without hiding it."""
    pairs = thumbnail_words(text, punch)
    if not pairs:
        return
    accent = tuple((palette or [GOLD])[0])
    image = Image.open(path).convert("RGB")
    w, h = image.size
    edge = max(0.34, min(0.56, art_left_edge(image)))
    shade = Image.new("L", (w, h), 0)
    ds = ImageDraw.Draw(shade)
    for x in range(int(w * edge)):
        ds.line([(x, 0), (x, h)], fill=int(150 * (1 - x / (w * edge)) ** 1.6))
    image = Image.composite(Image.new("RGB", (w, h), (6, 6, 9)), image, shade)

    font_path = str(load_theme().font("bold"))
    probe = ImageDraw.Draw(image)
    left = w * 0.055
    max_w = w * edge - left - w * 0.035      # a clear gap before the art
    size = int(h * 0.25)
    while True:
        font = ImageFont.truetype(font_path, size)
        lines: list[list[tuple[str, bool]]] = [[]]
        for pair in pairs:
            trial = " ".join(word for word, _ in lines[-1] + [pair])
            if lines[-1] and probe.textlength(trial, font=font) > max_w:
                lines.append([pair])
            else:
                lines[-1].append(pair)
        widest = max(probe.textlength(" ".join(word for word, _ in line), font=font) for line in lines)
        if (len(lines) <= 3 and widest <= max_w and len(lines) * size * 1.06 <= h * 0.74) or size <= h * 0.07:
            break
        size -= 3

    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    words = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dsh, dg, dw = ImageDraw.Draw(shadow), ImageDraw.Draw(glow), ImageDraw.Draw(words)
    space = dw.textlength(" ", font=font)
    y = (h - len(lines) * size * 1.06) / 2 - h * 0.02
    for line in lines:
        x = left
        for word, bold in line:
            color = accent if bold else WHITE
            dsh.text((x + size * 0.03, y + size * 0.05), word, font=font, fill=(0, 0, 0, 220),
                     stroke_width=max(4, size // 14), stroke_fill=(0, 0, 0, 220))
            if bold:
                dg.text((x, y), word, font=font, fill=accent + (210,))
            dw.text((x, y), word, font=font, fill=color + (255,))
            x += dw.textlength(word, font=font) + space
        y += size * 1.06
    shadow = shadow.filter(ImageFilter.GaussianBlur(size / 9))
    glow = glow.filter(ImageFilter.GaussianBlur(size / 6))
    out = Image.alpha_composite(image.convert("RGBA"), shadow)
    out = Image.alpha_composite(out, glow)
    out = Image.alpha_composite(out, words).convert("RGB")
    out.save(path)
