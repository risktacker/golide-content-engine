"""Instagram carousel text slides, typeset in code (no image model, no cost).

Slide 1 is the AI cover image with the hook. Slides 2 to 5 are drawn here in
the GOLIDE Black style so they match the cover: near-black background with a
faint haze, a small gold slide counter, a large light heading whose key words
glow, a muted body line, and the spaced wordmark at the foot.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from golide_engine.engine.typeset import _fonts, _wrap, tokenize
from golide_engine.theme import Theme, load_theme

SIZE = (1080, 1350)  # Instagram 4:5, the same shape as the cover image


@dataclass(frozen=True)
class Slide:
    heading: str
    text: str
    emphasis: str = ""
    final: bool = False


def _background(theme: Theme, size: tuple[int, int]):
    import numpy as np
    from PIL import Image

    w, h = size
    base = np.array(theme.rgb("background"), np.float32)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    # A soft warm haze high on the slide, fading to the edges.
    d = np.sqrt(((x - w * 0.5) / (w * 0.75)) ** 2 + ((y - h * 0.32) / (h * 0.55)) ** 2)
    haze = np.clip(1.0 - d, 0, 1)[..., None] ** 2
    gold = np.array(theme.rgb("gold"), np.float32)
    img = base + (gold - base) * haze * 0.05
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def _block(draw, lines, fonts, top, width, line_height, theme, glow_draw=None, color="text"):
    light, bold = fonts
    space = draw.textlength(" ", font=light)
    for row, line in enumerate(lines):
        line_width = sum(draw.textlength(t.text, font=bold if t.emphasis else light) for t in line) + space * (len(line) - 1)
        x = (width - line_width) / 2
        y = top + row * line_height
        for token in line:
            font = bold if token.emphasis else light
            draw.text((x, y), token.text, font=font, fill=theme.rgb(color) + (255,))
            if token.emphasis and glow_draw is not None:
                glow_draw.text((x, y), token.text, font=font, fill=theme.rgb("white_glow") + (255,))
            x += draw.textlength(token.text, font=font) + space


def render_slide(slide: Slide, number: int, total: int, output: Path, theme: Theme | None = None) -> Path:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    theme = theme or load_theme()
    width, height = SIZE
    base = _background(theme, SIZE)
    text_layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    glow_layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    glow = ImageDraw.Draw(glow_layer)
    margin = int(width * 0.12)

    # Counter, top left: "02 / 05" in gold mono.
    mono = ImageFont.truetype(str(theme.font("mono")), int(width * 0.026))
    draw.text((margin, int(height * 0.075)), f"{number:02d} / {total:02d}", font=mono, fill=theme.rgb("gold") + (255,))

    # Heading: large, light, key words bold and glowing.
    tokens = tokenize(" ".join(slide.heading.split()), slide.emphasis or "")
    size = int(width * (0.084 if slide.final else 0.074))
    while True:
        fonts = _fonts(theme, size)
        lines = _wrap(tokens, fonts, width - 2 * margin, draw)
        if len(lines) <= 4 or size <= int(width * 0.05):
            break
        size -= 2
    heading_lh = int(size * 1.22)

    # Body: smaller, muted, plain.
    body_size = int(width * 0.038)
    body_fonts = (ImageFont.truetype(str(theme.font("light")), body_size),) * 2
    body_lines = _wrap([t for t in tokenize(" ".join(slide.text.split()), "")], body_fonts, width - 2 * margin, draw)
    body_lh = int(body_size * 1.5)

    gap = int(height * 0.045)
    rule = int(height * 0.03)
    block = heading_lh * len(lines) + gap + rule + body_lh * len(body_lines)
    top = int(height * 0.47) - block // 2
    _block(draw, lines, fonts, top, width, heading_lh, theme, glow_draw=glow)

    y = top + heading_lh * len(lines) + gap // 2
    gold = theme.rgb("gold")
    draw.line([(width / 2 - width * 0.04, y), (width / 2 + width * 0.04, y)], fill=gold + (200,), width=3)
    y += rule
    _block(draw, body_lines, body_fonts, y, width, body_lh, theme, color="text_muted")

    if slide.final:
        cta_font = ImageFont.truetype(str(theme.font("mono")), int(width * 0.028))
        cta = "S A V E   T H I S   F O R   L A T E R"
        tw = draw.textlength(cta, font=cta_font)
        draw.text(((width - tw) / 2, int(height * 0.84)), cta, font=cta_font, fill=gold + (255,))

    blur = theme.glow["text_blur_radius"] * width / 1080
    glow_img = glow_layer.filter(ImageFilter.GaussianBlur(blur))
    strength = theme.glow["text_glow_strength"]
    glow_img.putalpha(glow_img.getchannel("A").point(lambda a: int(a * strength)))
    base = Image.alpha_composite(base, glow_img)
    base = Image.alpha_composite(base, text_layer)

    # Wordmark at the foot, exactly as on the cover.
    mark = theme.watermark
    mark_font = ImageFont.truetype(str(theme.font("regular")), max(12, int(width * 0.016)))
    md = ImageDraw.Draw(base)
    letters = list(mark["text"])
    spacing = mark["letter_spacing"] * width / 1080
    total_w = sum(md.textlength(c, font=mark_font) for c in letters) + spacing * (len(letters) - 1)
    x = (width - total_w) / 2
    for char in letters:
        md.text((x, int(height * 0.955)), char, font=mark_font, fill=theme.rgb(mark["color"]) + (255,))
        x += md.textlength(char, font=mark_font) + spacing

    output.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(output, "JPEG", quality=94, optimize=True)
    return output
