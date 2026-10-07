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
    product: bool = False  # the marketplace slide in the evening carousel


def _background(theme: Theme, size: tuple[int, int]):
    """Near-black with a faint warm haze high on the slide (pure Pillow, no numpy)."""
    from PIL import Image, ImageDraw, ImageFilter

    w, h = size
    base = Image.new("RGB", size, theme.rgb("background"))
    glow = Image.new("L", size, 0)
    ImageDraw.Draw(glow).ellipse((w * -0.25, h * -0.23, w * 1.25, h * 0.87), fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(w * 0.22)).point(lambda v: int(v * 0.05))
    tint = Image.new("RGB", size, theme.rgb("gold"))
    return Image.composite(tint, base, glow).convert("RGBA")


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
    if slide.product:
        tag = "F R O M   T H E   G O L I D E   M A R K E T P L A C E"
        tw = draw.textlength(tag, font=mono)
        draw.text(((width - tw) / 2, int(height * 0.22)), tag, font=mono, fill=theme.rgb("gold") + (255,))

    # Heading: large, light, key words bold and glowing.
    tokens = tokenize(" ".join(slide.heading.split()), slide.emphasis or "")
    size = int(width * (0.078 if slide.final else 0.074))
    while True:
        fonts = _fonts(theme, size)
        lines = _wrap(tokens, fonts, width - 2 * margin, draw)
        if len(lines) <= 4 or size <= int(width * 0.05):
            break
        size -= 2
    heading_lh = int(size * 1.22)

    # Body: plain and readable. The short line that pulls the reader to the next
    # slide ("But there's a catch.") gets its own line in gold, so the story leads.
    body_size = int(width * 0.041)
    body_fonts = (ImageFont.truetype(str(theme.font("light")), body_size),) * 2
    main_text, pull = _split_pull(" ".join(slide.text.split()), slide.final or slide.product)
    body_lines = _wrap([t for t in tokenize(main_text, "")], body_fonts, width - 2 * margin, draw)
    pull_fonts = (ImageFont.truetype(str(theme.font("regular")), body_size),) * 2
    pull_lines = _wrap([t for t in tokenize(pull, "")], pull_fonts, width - 2 * margin, draw) if pull else []
    body_lh = int(body_size * 1.5)
    pull_gap = int(body_lh * 0.6) if pull_lines else 0

    gap = int(height * 0.045)
    rule = int(height * 0.03)
    block = heading_lh * len(lines) + gap + rule + body_lh * len(body_lines) + pull_gap + body_lh * len(pull_lines)
    top = int(height * 0.47) - block // 2
    _block(draw, lines, fonts, top, width, heading_lh, theme, glow_draw=glow)

    y = top + heading_lh * len(lines) + gap // 2
    gold = theme.rgb("gold")
    draw.line([(width / 2 - width * 0.04, y), (width / 2 + width * 0.04, y)], fill=gold + (200,), width=3)
    y += rule
    _block(draw, body_lines, body_fonts, y, width, body_lh, theme, color="text")
    if pull_lines:
        _block(draw, pull_lines, pull_fonts, y + body_lh * len(body_lines) + pull_gap, width, body_lh, theme, color="gold")

    if slide.final or slide.product:
        # The closing slide asks for the follow; the product slide points to the bio link.
        cta = "F O L L O W   G O L I D E   F O R   M O R E" if slide.final else "L I N K   I N   B I O"
        cta_font = ImageFont.truetype(str(theme.font("mono")), int(width * 0.028))
        tw = draw.textlength(cta, font=cta_font)
        pad_x, pad_y = int(width * 0.05), int(height * 0.022)
        box = (int((width - tw) / 2) - pad_x, int(height * 0.83) - pad_y,
               int((width + tw) / 2) + pad_x, int(height * 0.83) + int(cta_font.size * 1.2) + pad_y)
        draw.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, outline=gold + (230,), width=2)
        draw.text(((width - tw) / 2, int(height * 0.83)), cta, font=cta_font, fill=gold + (255,))

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


def _split_pull(text: str, closing: bool) -> tuple[str, str]:
    """Separate a short last sentence that leads into the next slide."""
    import re

    if closing:
        return text, ""
    sentences = re.findall(r"[^.!?]+[.!?]+", text)
    if len(sentences) < 2:
        return text, ""
    last = sentences[-1].strip()
    if len(last.split()) > 8:
        return text, ""
    return text[: len(text) - len(sentences[-1])].strip(), last
