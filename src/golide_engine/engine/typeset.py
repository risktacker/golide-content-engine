"""Code-set typography for GOLIDE Black stills.

The image model never draws text. The hook is typeset here so spelling, font
and the glowing emphasis phrase are identical on every post: thin white words,
one key phrase bold with a soft glow, and a small muted wordmark.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from golide_engine.theme import Theme, load_theme


@dataclass(frozen=True)
class Token:
    text: str
    emphasis: bool


def tokenize(hook: str, emphasis: str) -> list[Token]:
    words = hook.split()
    marked = [False] * len(words)
    target = emphasis.split()
    if target:
        lowered = [w.lower().strip(".,!?:;\"'") for w in words]
        wanted = [w.lower().strip(".,!?:;\"'") for w in target]
        for start in range(len(words) - len(wanted) + 1):
            if lowered[start:start + len(wanted)] == wanted:
                for index in range(start, start + len(wanted)):
                    marked[index] = True
                break
    return [Token(word, flag) for word, flag in zip(words, marked)]


def _fonts(theme: Theme, size: int):
    from PIL import ImageFont

    return (
        ImageFont.truetype(str(theme.font("light")), size),
        ImageFont.truetype(str(theme.font("bold")), size),
    )


def _wrap(tokens: list[Token], fonts, max_width: int, draw) -> list[list[Token]]:
    light, bold = fonts
    space = draw.textlength(" ", font=light)
    lines: list[list[Token]] = [[]]
    width = 0.0
    for token in tokens:
        font = bold if token.emphasis else light
        word = draw.textlength(token.text, font=font)
        extra = word if not lines[-1] else space + word
        if lines[-1] and width + extra > max_width:
            lines.append([token])
            width = word
        else:
            lines[-1].append(token)
            width += extra
    return lines


def overlay_hook(image, hook: str, emphasis: str, theme: Theme | None = None):
    """Return a copy of ``image`` with the hook typeset in its lower third."""
    from PIL import Image, ImageDraw, ImageFilter

    theme = theme or load_theme()
    base = image.convert("RGBA")
    width, height = base.size

    # Darken the lower part so text always sits on near-black.
    fade = Image.new("L", (1, height))
    start = int(height * 0.52)
    for y in range(height):
        fade.putpixel((0, y), 0 if y < start else min(255, int(255 * ((y - start) / (height - start)) ** 0.8 * 1.05)))
    shade = Image.new("RGBA", (width, height), theme.rgb("background") + (255,))
    shade.putalpha(fade.resize((width, height)))
    base = Image.alpha_composite(base, shade)

    hook = " ".join(hook.split())
    if not hook:
        return base.convert("RGB")
    tokens = tokenize(hook, emphasis)
    size = int(width * 0.058)
    measure = ImageDraw.Draw(base)
    margin = int(width * 0.11)
    while True:
        fonts = _fonts(theme, size)
        lines = _wrap(tokens, fonts, width - 2 * margin, measure)
        if len(lines) <= 3 or size <= int(width * 0.038):
            break
        size -= 2
    light, bold = fonts
    line_height = int(size * 1.32)
    block = line_height * len(lines)
    top = int(height * 0.80) - block // 2
    if top + block > int(height * 0.90):
        top = int(height * 0.90) - block

    text_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glow_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    glow_draw = ImageDraw.Draw(glow_layer)
    space = measure.textlength(" ", font=light)
    for row, line in enumerate(lines):
        line_width = sum(
            measure.textlength(t.text, font=bold if t.emphasis else light) for t in line
        ) + space * (len(line) - 1)
        x = (width - line_width) / 2
        y = top + row * line_height
        for token in line:
            font = bold if token.emphasis else light
            text_draw.text((x, y), token.text, font=font, fill=theme.rgb("text") + (255,))
            if token.emphasis:
                glow_draw.text((x, y), token.text, font=font, fill=theme.rgb("white_glow") + (255,))
            x += measure.textlength(token.text, font=font) + space

    blur = theme.glow["text_blur_radius"] * width / 1080
    glow = glow_layer.filter(ImageFilter.GaussianBlur(blur))
    strength = theme.glow["text_glow_strength"]
    glow.putalpha(glow.getchannel("A").point(lambda a: int(a * strength)))
    base = Image.alpha_composite(base, glow)
    base = Image.alpha_composite(base, text_layer)

    mark = theme.watermark
    mark_font_size = max(12, int(width * 0.016))
    from PIL import ImageFont

    mark_font = ImageFont.truetype(str(theme.font("regular")), mark_font_size)
    mark_draw = ImageDraw.Draw(base)
    letters = list(mark["text"])
    spacing = mark["letter_spacing"] * width / 1080
    total = sum(mark_draw.textlength(c, font=mark_font) for c in letters) + spacing * (len(letters) - 1)
    x = (width - total) / 2
    y = int(height * 0.955)
    for char in letters:
        mark_draw.text((x, y), char, font=mark_font, fill=theme.rgb(mark["color"]) + (255,))
        x += mark_draw.textlength(char, font=mark_font) + spacing
    return base.convert("RGB")


def compose_post(master: Path, hook: str, emphasis: str, output: Path, size: tuple[int, int], centering=(0.5, 0.4)) -> None:
    from PIL import Image, ImageOps

    with Image.open(master) as image:
        fitted = ImageOps.fit(
            image.convert("RGB"), size, method=Image.Resampling.LANCZOS, centering=centering
        )
    result = overlay_hook(fitted, hook, emphasis)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, "JPEG", quality=94, optimize=True)
