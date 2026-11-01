"""Thumbnails and covers modelled on the source video's own thumbnail (owner direction 2026-11-01).

"When you set rules on things it becomes obvious, but when every video is modelled each video
comes unique... title, thumbnail, how they did it, where they placed the title, how it looked,
and we just tweak a bit. Different channels have different looks and formats; we grab it all."

The old thumbnail was one template (black, product on the right, words on the left) and the
Shorts covers rotated four layouts. Now a vision call reads the modelled video's thumbnail:
where its words sit, how many, their case, colour and style, where the subject sits and how
big it is, the background and any arrow or circle. Our picture is made in that structure, with
our product and our words (their wording with a few words changed). Their image, text, logos
and faces are never copied: only the structure is.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..theme import load_theme

ZONES = ("top", "bottom", "left", "right", "center", "top-left", "top-right", "bottom-left",
         "bottom-right", "none")
SUBJECT_ZONES = ("left", "right", "center", "bottom", "top")
SIZES = ("small", "medium", "large", "huge")
STYLES = ("plain", "shadow", "outline", "box", "glow")
BACKGROUNDS = ("dark", "light", "gradient", "scene", "split")
EXTRAS = ("arrow", "circle", "split", "glow")

LAYOUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["their_text", "our_text", "highlight", "text_zone", "text_lines", "text_case",
                 "text_style", "text_size", "text_color", "highlight_color", "box_color",
                 "subject", "action", "subject_zone", "subject_size", "subject_angle", "background",
                 "bg_colors", "background_note", "extras", "mood"],
    "properties": {
        "their_text": {"type": "string"},
        "our_text": {"type": "string"},
        "highlight": {"type": "string"},
        "text_zone": {"type": "string", "enum": list(ZONES)},
        "text_lines": {"type": "integer"},
        "text_case": {"type": "string", "enum": ["upper", "title", "sentence"]},
        "text_style": {"type": "string", "enum": list(STYLES)},
        "text_size": {"type": "string", "enum": list(SIZES)},
        "text_color": {"type": "string"},
        "highlight_color": {"type": "string"},
        "box_color": {"type": "string"},
        "subject": {"type": "string"},
        "action": {"type": "string"},
        "subject_zone": {"type": "string", "enum": list(SUBJECT_ZONES)},
        "subject_size": {"type": "string", "enum": list(SIZES)},
        "subject_angle": {"type": "string"},
        "background": {"type": "string", "enum": list(BACKGROUNDS)},
        "bg_colors": {"type": "array", "items": {"type": "string"}},
        "background_note": {"type": "string"},
        "extras": {"type": "array", "items": {"type": "string", "enum": list(EXTRAS)}},
        "mood": {"type": "string"},
    },
}

READ_RULES = """You study one YouTube thumbnail (the image) so we can make ours in the SAME structure.
Describe exactly what you see:
- their_text: the words printed on it, exactly ("" if none).
- text_zone: where those words sit ("none" if there are no words). text_lines: how many lines
  (0 if none). text_case, text_style (plain, shadow, outline = a thick stroke round the letters,
  box = letters on a coloured block, glow), text_size (how much of the height a line takes:
  small under 10%, medium 10-18%, large 18-28%, huge more), text_color and highlight_color
  (hex; highlight is the colour of the one word set apart, or the same as text_color),
  box_color (hex, or "" when there is no box).
- subject: OUR subject, not theirs: the real object OUR_TITLE is about, named exactly (the
  iPhone Duo foldable phone, the touchscreen MacBook Pro, a stack of 100 dollar bills for a
  loss). When their subject is a person or the creator's face, ours is still that object,
  placed where the person was at the same size. Never a person, never a face.
- action: the ONE thing happening in OUR picture that tells OUR story at a glance (a hand
  touching the laptop screen, a hand folding the phone open, a red arrow at the cracked hinge).
  A hand and forearm may appear; never a face, a head or a whole person (owner direction
  2026-11-01: "the hand and or an arrow, those things will be needful").
- subject_zone, subject_size (how much of the frame THEIR main subject fills),
  subject_angle (front, three-quarter, side, top-down, close-up...).
- background: dark, light, gradient, scene (a real place) or split (two halves);
  bg_colors: its two main colours as hex; background_note: a few words (white studio sweep,
  blurred desk, black with a red glow...).
- extras: only those present (arrow, circle drawn round something, split = before/after halves,
  glow behind the subject).
- mood: 2 to 4 words.
Then write OURS for the video in OUR_TITLE:
- our_text: their_text with ONE to THREE words changed so it fits our video, same length,
  same pattern, same punctuation ("" when theirs is ""). Never copy a channel name, a person's
  name or a handle; if theirs is only a name, write 1 to 3 words about our video instead.
- highlight: the one word of our_text that takes the highlight colour ("" if none)."""


def _data_url(path: Path) -> str:
    kind = "png" if path.suffix.lower() == ".png" else "jpeg"
    return f"data:image/{kind};base64," + base64.b64encode(path.read_bytes()).decode()


def read_layout(text, thumbnail: Path, our_title: str, on_output=None) -> dict:
    """One small vision call: the source thumbnail's structure plus our words for it.
    ``on_output`` receives the provider output (for the cost ledger)."""
    output = text.generate_json(READ_RULES, f"OUR_TITLE={our_title}", LAYOUT_SCHEMA,
                                max_output_tokens=3000, images=[_data_url(thumbnail)])
    if on_output is not None:
        on_output(output)
    return clean_layout(dict(output.value))


def stamp_modelled(path: Path, layout: dict) -> None:
    """Our words where theirs were, plus the GOLIDE mark, on a finished 16:9 thumbnail."""
    image = add_mark(place_text(Image.open(path), layout), layout)
    image.save(path)


# Owner direction 2026-11-01: "we can't lose our brand... just a bit." Everything else is
# modelled; these stay ours on every thumbnail and cover: our typeface, the highlight word
# in GOLIDE gold, a thin gold rim light on the subject, and the small GOLIDE mark.
BRAND_GOLD = "#E9C46A"


def clean_layout(layout: dict) -> dict:
    layout = dict(layout)
    layout["highlight_color"] = BRAND_GOLD
    layout["text_lines"] = max(0, min(3, int(layout.get("text_lines") or 0)))
    if not str(layout.get("our_text", "")).strip():
        layout["text_zone"] = "none"
    for key, allowed, default in (("text_zone", ZONES, "none"), ("subject_zone", SUBJECT_ZONES, "center"),
                                  ("text_size", SIZES, "large"), ("subject_size", SIZES, "large"),
                                  ("text_style", STYLES, "shadow"), ("background", BACKGROUNDS, "dark")):
        if layout.get(key) not in allowed:
            layout[key] = default
    colors = [c for c in layout.get("bg_colors") or [] if _rgb(c)]
    layout["bg_colors"] = (colors + ["#101418", "#22262c"])[:2]
    return layout


def _rgb(value, default=None):
    value = str(value or "").strip().lstrip("#")
    if len(value) != 6:
        return default
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# The picture prompt (long-video thumbnails, 16:9)
# ---------------------------------------------------------------------------

_SIZE_WORDS = {"small": "about a third of the frame", "medium": "about half the frame",
               "large": "about two thirds of the frame", "huge": "almost the whole frame, cropped close"}
_ZONE_WORDS = {"left": "on the left", "right": "on the right", "center": "in the centre",
               "bottom": "in the lower part", "top": "in the upper part"}
_FREE = {"top": "the top band", "bottom": "the bottom band", "left": "the left side",
         "right": "the right side", "center": "a band across the middle", "top-left": "the top-left corner",
         "top-right": "the top-right corner", "bottom-left": "the bottom-left corner",
         "bottom-right": "the bottom-right corner"}


def modelled_prompt(title: str, subject: str, layout: dict, has_reference: bool) -> str:
    background = {
        "dark": f"a dark background ({layout['background_note']})",
        "light": f"a light, bright background ({layout['background_note']})",
        "gradient": f"a smooth gradient background from {layout['bg_colors'][0]} to {layout['bg_colors'][1]}",
        "scene": f"a real setting in the background, softly out of focus ({layout['background_note']})",
        "split": f"a frame split into two halves, before and after ({layout['background_note']})",
    }[layout["background"]]
    extras = ""
    if "arrow" in layout["extras"]:
        extras += "One bold, simple arrow points at the key part. "
    if "circle" in layout["extras"]:
        extras += "One bold hand-drawn circle rings the key part. "
    if "glow" in layout["extras"]:
        extras += "A soft glow behind the subject. "
    free = _FREE.get(layout["text_zone"])
    space = (f"Keep {free} clear and quiet for big words added later; the subject never reaches into it. "
             if free else "")
    # 2026-11-01 preview: given the source thumbnail as a reference, the image model redrew the
    # source photo itself (the creator's face, his hands and desk). The source is only ever READ
    # for its structure; a reference here is our own picture of the product.
    reference = ("The reference image is our own picture of the product: draw THAT exact product. "
                 if has_reference else "")
    return (
        "16:9 YouTube thumbnail, photo-real, crisp at phone size. "
        f"Main subject: {subject or layout['subject']}, {_ZONE_WORDS[layout['subject_zone']]}, filling "
        f"{_SIZE_WORDS[layout['subject_size']]}, seen {layout['subject_angle'] or 'three-quarter'}. "
        f"Background: {background}. Colours lean to {layout['bg_colors'][0]} and {layout['bg_colors'][1]}. "
        f"Mood: {layout['mood']}. "
        + (f"The action that tells the story: {layout['action']}. " if layout.get("action") else "")
        + extras + space + reference +
        f"A thin, warm gold ({BRAND_GOLD}) rim light traces the subject's edges. "
        "No faces, no heads, no whole people: at most a hand and forearm. ABSOLUTELY NO text, letters, numbers, logos or watermarks anywhere. "
        f"Video title for context only: {title}"
    )


# ---------------------------------------------------------------------------
# Our words, set where theirs were, the way theirs looked
# ---------------------------------------------------------------------------

_LINE_HEIGHT = {"small": 0.085, "medium": 0.14, "large": 0.21, "huge": 0.28}


def place_text(image: Image.Image, layout: dict, text: str | None = None,
               highlight: str | None = None) -> Image.Image:
    """Typeset ``text`` (default: layout["our_text"]) in the modelled zone and style."""
    text = str(layout.get("our_text", "") if text is None else text).strip()
    zone = layout.get("text_zone", "none")
    if not text or zone == "none":
        return image
    highlight = str(layout.get("highlight", "") if highlight is None else highlight).strip().lower()
    case = layout.get("text_case", "upper")
    if case == "upper":
        text = text.upper()
    image = image.convert("RGB")
    w, h = image.size
    portrait = h > w
    font_path = str(load_theme().font("bold"))
    probe = ImageDraw.Draw(image)
    lines_wanted = max(1, int(layout.get("text_lines") or 1))
    side = zone in ("left", "right") or zone.endswith("-left") or zone.endswith("-right")
    max_w = w * (0.86 if portrait or not side else 0.5)
    size = int(h * _LINE_HEIGHT[layout.get("text_size", "large")] * (0.55 if portrait else 1.0))
    words = text.split()
    while True:
        font = ImageFont.truetype(font_path, size)
        lines: list[list[str]] = [[]]
        for word in words:
            trial = " ".join(lines[-1] + [word])
            if lines[-1] and probe.textlength(trial, font=font) > max_w:
                lines.append([word])
            else:
                lines[-1].append(word)
        # Balance to the modelled number of lines when the words allow it.
        if len(lines) < lines_wanted <= len(words):
            per = -(-len(words) // lines_wanted)
            lines = [words[i:i + per] for i in range(0, len(words), per)]
        widest = max(probe.textlength(" ".join(line), font=font) for line in lines)
        if (widest <= max_w and len(lines) * size * 1.08 <= h * 0.6) or size <= h * 0.04:
            break
        size -= 3
    block_w = max(probe.textlength(" ".join(line), font=font) for line in lines)
    block_h = len(lines) * size * 1.08
    margin_x, margin_y = w * 0.06, h * (0.06 if portrait else 0.08)
    if zone in ("left", "top-left", "bottom-left"):
        x0, align = margin_x, "left"
    elif zone in ("right", "top-right", "bottom-right"):
        x0, align = w - margin_x - block_w, "right"
    else:
        x0, align = (w - block_w) / 2, "center"
    if zone in ("top", "top-left", "top-right"):
        y0 = margin_y
    elif zone in ("bottom", "bottom-left", "bottom-right"):
        y0 = h - margin_y - block_h
    else:
        y0 = (h - block_h) / 2
    color = _rgb(layout.get("text_color"), (255, 255, 255))
    accent = _rgb(layout.get("highlight_color"), (255, 200, 60))
    style = layout.get("text_style", "shadow")
    out = image.convert("RGBA")
    under = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    top = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    du, dt = ImageDraw.Draw(under), ImageDraw.Draw(top)
    space = dt.textlength(" ", font=font)
    stroke = max(3, size // 9)
    if style == "box":
        box = _rgb(layout.get("box_color"), (200, 30, 40))
        pad = size * 0.18
        dt.rectangle([x0 - pad, y0 - pad * 0.6, x0 + block_w + pad, y0 + block_h + pad * 0.6], fill=box + (255,))
    y = y0
    for line in lines:
        lw = dt.textlength(" ".join(line), font=font)
        x = x0 if align == "left" else (x0 + block_w - lw if align == "right" else x0 + (block_w - lw) / 2)
        for word in line:
            fill = accent if highlight and word.lower().strip(".,!?:;'\"") == highlight.strip(".,!?:;'\"") else color
            if style in ("shadow", "glow", "plain"):
                du.text((x + size * 0.03, y + size * 0.05), word, font=font,
                        fill=(0, 0, 0, 200 if style != "plain" else 110))
            if style == "glow":
                du.text((x, y), word, font=font, fill=fill + (200,))
            dt.text((x, y), word, font=font, fill=fill + (255,),
                    **({"stroke_width": stroke, "stroke_fill": (0, 0, 0)} if style == "outline" else {}))
            x += dt.textlength(word, font=font) + space
        y += size * 1.08
    blur = size / (5 if style == "glow" else 9)
    out = Image.alpha_composite(out, under.filter(ImageFilter.GaussianBlur(blur)))
    out = Image.alpha_composite(out, top)
    return out.convert("RGB")


def add_mark(image: Image.Image, layout: dict) -> Image.Image:
    """The small GOLIDE mark, in the corner away from the words."""
    image = image.convert("RGBA")
    w, h = image.size
    font = ImageFont.truetype(str(load_theme().font("bold")), max(14, int(min(w, h) * 0.032)))
    text = "  ".join("GOLIDE")
    draw = ImageDraw.Draw(image)
    tw = draw.textlength(text, font=font)
    zone = layout.get("text_zone", "none")
    right = not (zone.endswith("right") or zone == "right")
    top = zone.startswith("bottom") or zone in ("bottom", "none", "left", "right", "center")
    x = w - tw - w * 0.035 if right else w * 0.035
    y = h * 0.035 if top else h - font.size * 1.6 - h * 0.035
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 140))
    ImageDraw.Draw(layer).text((x, y), text, font=font, fill=(246, 244, 238, 215))
    return Image.alpha_composite(image, layer).convert("RGB")


def layout_json(layout: dict) -> str:
    return json.dumps(layout, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Shorts and reel covers: our drawn object on a canvas in the modelled structure
# ---------------------------------------------------------------------------

_SUBJECT_SCALE = {"small": 0.42, "medium": 0.55, "large": 0.68, "huge": 0.8}


def canvas_from_layout(cut: Image.Image, mask, layout: dict, size=(1080, 1920)) -> Image.Image:
    """The cover in the modelled structure: background, subject place and size, then words."""
    import numpy as np
    from scipy import ndimage

    w, h = size
    a, b = (np.array(_rgb(c, (20, 24, 30)), np.float32) for c in layout["bg_colors"])
    if layout["background"] == "light":
        a, b = np.maximum(a, 200), np.maximum(b, 170)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = (yy / h)[..., None]
    zone = layout.get("subject_zone", "center")
    text_zone = layout.get("text_zone", "none")
    cy = {"top": 0.36, "bottom": 0.62}.get(zone, 0.5)
    if text_zone.startswith("top") and zone not in ("top", "bottom"):
        cy = 0.6
    elif text_zone.startswith("bottom") and zone not in ("top", "bottom"):
        cy = 0.42
    cx = {"left": 0.38, "right": 0.62}.get(zone, 0.5)
    if layout["background"] == "split":
        canvas = np.where((xx < w / 2)[..., None], a, b) * np.ones((h, w, 1), np.float32)
    else:
        canvas = a * (1 - t) + b * t
    light = np.exp(-(((xx - w * cx) / (w * 0.55)) ** 2 + ((yy - h * cy) / (h * 0.3)) ** 2))[..., None]
    glow = 0.9 if "glow" in layout.get("extras", []) else 0.45
    canvas = canvas + light * (a + b) * glow * (0.4 if layout["background"] == "light" else 1.0)
    share = _SUBJECT_SCALE.get(layout.get("subject_size", "large"), 0.68)
    scale = min(w * min(0.95, share * 1.3) / cut.width, h * share * 0.85 / cut.height)
    obj = cut.resize((max(1, int(cut.width * scale)), max(1, int(cut.height * scale))), Image.Resampling.LANCZOS)
    m = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8)).resize(obj.size, Image.Resampling.LANCZOS)
    alpha = np.clip(ndimage.grey_dilation(ndimage.gaussian_filter(np.asarray(m, np.float32) / 255, 1.5),
                                          size=(9, 9)), 0, 1)
    ox = int(max(0, min(w - obj.width, w * cx - obj.width / 2)))
    oy = int(max(0, min(h - obj.height, h * cy - obj.height / 2)))
    shadow = np.zeros((h, w), np.float32)
    shadow[oy:oy + obj.height, ox:ox + obj.width] = alpha
    shadow = ndimage.shift(ndimage.gaussian_filter(shadow, 28), (40, 18))
    canvas = canvas * (1 - 0.5 * shadow[..., None])
    region = canvas[oy:oy + obj.height, ox:ox + obj.width]
    al = alpha[..., None]
    canvas[oy:oy + obj.height, ox:ox + obj.width] = region * (1 - al) + np.asarray(obj, np.float32) * al * 1.15
    image = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(image)
    stroke = max(8, w // 90)
    accent = _rgb(layout.get("highlight_color"), (255, 200, 60))
    if "circle" in layout.get("extras", []):
        r = min(obj.width, obj.height) * 0.28
        x, y = ox + obj.width * 0.6, oy + obj.height * 0.45
        draw.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], outline=accent, width=stroke)
    if "arrow" in layout.get("extras", []):
        tip = (ox + obj.width * 0.15, oy + obj.height * 0.2)
        tail = (tip[0] - w * 0.12, tip[1] - h * 0.07)
        draw.line([tail, tip], fill=accent, width=stroke)
        draw.polygon([tip, (tip[0] - stroke * 4, tip[1] - stroke), (tip[0] - stroke, tip[1] - stroke * 4)], fill=accent)
    return add_mark(place_text(image, layout), layout)
