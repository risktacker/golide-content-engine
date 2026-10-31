"""The Shorts cover (owner direction 2026-10-31).

"The shorts look like covers... that's how this guy noticed the channel to be automated."
YouTube shows a frame grabbed from the middle of a Short, usually a drawing half drawn. A
Short now opens on a designed cover made from its own drawing, in code (no paid image):

* the short's strongest drawing, finished and painted, large and centred;
* every edge fading into black, so it reads as a poster, not a frame from a video;
* NO words (owner 2026-10-31: "the moment you repeat a thing 3 times it becomes obvious...
  just remove them so the art takes over, because it is already different"). The text
  option stays in the code but the engine passes no text.

The same picture is the video's first block, saved as cover.png and attached to the email
after the upload, ready to set as the thumbnail.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..theme import load_theme
from .thumb_text import GOLD, WHITE, thumbnail_words
from . import thumb_text

TEXT_TOP = 0.085          # the words start this far down (clear of the phone's status bar)
TEXT_BAND = 0.30          # and take at most this share of the height
ART_TOP = 0.36            # the drawing sits below the words


def _vignette(w: int, h: int) -> np.ndarray:
    """1 in the middle, falling to 0 at every edge (wider at the bottom)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / w, yy / h
    side = np.clip(np.minimum(u, 1 - u) / 0.14, 0, 1)
    top = np.clip(v / 0.06, 0, 1)
    bottom = np.clip((1 - v) / 0.22, 0, 1)
    return (side * top * bottom) ** 1.4


def compose(art: Image.Image, text: str, punch: str = "", accent=GOLD, size=(1080, 1920),
            box: tuple | None = None) -> Image.Image:
    """The cover: ``art`` (the finished, painted drawing on its stage) under the big line.
    ``box`` (left, top, right, bottom) is the drawing's own area in ``art``; it is cut out
    with some of its floor and enlarged to fill the space below the words."""
    w, h = size
    canvas = Image.new("RGB", (w, h), (8, 8, 11))
    if box:
        x0, y0, x1, y1 = box
        pad_x, pad_y = (x1 - x0) * 0.10, (y1 - y0) * 0.10
        art = art.crop((int(max(0, x0 - pad_x)), int(max(0, y0 - pad_y)),
                        int(min(art.width, x1 + pad_x)), int(min(art.height, y1 + (y1 - y0) * 0.22))))
    words_on = bool(str(text).strip())
    art_top = ART_TOP if words_on else 0.0
    space_h = h * (1 - art_top) * (0.92 if words_on else 0.72)
    aw, ah = art.size
    scale = min(w * (1.0 if words_on else 0.96) / aw, space_h / ah)
    art = art.resize((max(1, int(aw * scale)), max(1, int(ah * scale))), Image.Resampling.LANCZOS)
    top = int(h * art_top + (space_h - art.height) * 0.45) if words_on else int((h - art.height) / 2)
    # The cut-out art melts into the black: its own edges fade, so no rectangle shows.
    yy, xx = np.mgrid[0:art.height, 0:art.width].astype(np.float32)
    fx = np.clip(np.minimum(xx, art.width - 1 - xx) / (art.width * 0.14), 0, 1)
    fy = np.clip(np.minimum(yy, art.height - 1 - yy) / (art.height * 0.16), 0, 1)
    feather = Image.fromarray(((fx * fy) ** 1.2 * 255).astype(np.uint8))
    canvas.paste(art, ((w - art.width) // 2, top), feather)
    # Soft shading at the top so the words always read, then every edge fades out.
    rgb = np.asarray(canvas, np.float32)
    yy = np.arange(h, dtype=np.float32)[:, None, None] / h
    if words_on:
        rgb = rgb * (0.25 + 0.75 * np.clip((yy - ART_TOP + 0.04) / 0.10, 0, 1))
    rgb = rgb * _vignette(w, h)[..., None] + np.array((8, 8, 11), np.float32) * (1 - _vignette(w, h)[..., None])
    canvas = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))

    saved, thumb_text.MAX_WORDS = thumb_text.MAX_WORDS, 9    # the cover line is said in full
    try:
        pairs = thumbnail_words(text, punch)
    finally:
        thumb_text.MAX_WORDS = saved
    if not pairs:
        return canvas
    font_path = str(load_theme().font("bold"))
    probe = ImageDraw.Draw(canvas)
    max_w = w * 0.86
    fsize = int(w * 0.16)
    while True:
        font = ImageFont.truetype(font_path, fsize)
        lines: list[list[tuple[str, bool]]] = [[]]
        for pair in pairs:
            trial = " ".join(word for word, _ in lines[-1] + [pair])
            if lines[-1] and probe.textlength(trial, font=font) > max_w:
                lines.append([pair])
            else:
                lines[-1].append(pair)
        widest = max(probe.textlength(" ".join(word for word, _ in line), font=font) for line in lines)
        if (len(lines) <= 4 and widest <= max_w and len(lines) * fsize * 1.08 <= h * TEXT_BAND) or fsize <= w * 0.07:
            break
        fsize -= 4
    shadow, glow, words = (Image.new("RGBA", (w, h), (0, 0, 0, 0)) for _ in range(3))
    dsh, dg, dw = ImageDraw.Draw(shadow), ImageDraw.Draw(glow), ImageDraw.Draw(words)
    space = dw.textlength(" ", font=font)
    block = len(lines) * fsize * 1.08
    y = h * TEXT_TOP + (h * TEXT_BAND - block) / 2
    for line in lines:
        width = dw.textlength(" ".join(word for word, _ in line), font=font)
        x = (w - width) / 2
        for word, bold in line:
            colour = tuple(accent) if bold else WHITE
            dsh.text((x + fsize * 0.04, y + fsize * 0.06), word, font=font, fill=(0, 0, 0, 200))
            dg.text((x, y), word, font=font, fill=colour + (170 if bold else 60,))
            dw.text((x, y), word, font=font, fill=colour + (255,))
            x += dw.textlength(word, font=font) + space
        y += fsize * 1.08
    out = canvas.convert("RGBA")
    out = Image.alpha_composite(out, shadow.filter(ImageFilter.GaussianBlur(fsize / 9)))
    out = Image.alpha_composite(out, glow.filter(ImageFilter.GaussianBlur(fsize / 6)))
    return Image.alpha_composite(out, words).convert("RGB")


def save(image: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, quality=92)
    return path
