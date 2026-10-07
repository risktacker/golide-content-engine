"""The cover card: the picture people see before a video plays.

Owner direction 2026-10-07: wherever a platform or a download shows a video
without a chosen thumbnail it shows the first frame, which used to be black.
Every video now opens on a designed cover (the video's best illustration,
fully drawn and coloured, plus a short hook with its punch in gold), and the
same image is uploaded as the cover on Instagram, Facebook and LinkedIn.
YouTube keeps its own AI-generated thumbnail.

Layouts stay inside each format's safe area: 9:16 has the drawing above and
the hook below, within the middle of the frame that tall phones never crop;
16:9 has the hook on the left and the drawing on the right.
"""

from __future__ import annotations

import re
from typing import Any

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

COVER_HOLD = 0.12   # seconds the cover is the whole frame (the first-frame thumbnail)
COVER_FADE = 0.35   # then it fades into the opening scene


def _norm(word: str) -> str:
    return re.sub(r"[^\w']", "", word.lower())


def render_cover(renderer, drawing, text: str, gold: str) -> Image.Image:
    """Compose the cover for this renderer's format (RGB, full frame size)."""
    from .illustrate import draw_illustration
    from .primitives import Draw
    from .render import GLOW_SCALE

    L, theme = renderer.layout, renderer.theme
    W, H = L.width, L.height
    vertical = W < H
    unit = L.size / 2
    if vertical:
        region = (-0.36 * W / unit, (0.13 * H - L.cy) / unit, 0.36 * W / unit, (0.55 * H - L.cy) / unit)
    else:
        region = ((0.50 * W - L.cx) / unit, (0.14 * H - L.cy) / unit, (0.93 * W - L.cx) / unit, (0.86 * H - L.cy) / unit)

    main_s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    glow_s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W // GLOW_SCALE, H // GLOW_SCALE)
    main, glow = cairo.Context(main_s), cairo.Context(glow_s)
    for ctx, scale in ((main, 1.0), (glow, 1 / GLOW_SCALE)):
        ctx.scale(scale, scale)
        ctx.translate(L.cx, L.cy)
        ctx.scale(unit, unit)
    if drawing is not None:
        d = Draw(main, glow, 1.0, 0, 1, 9.0, 1, unit, renderer.colors, (), region=region)
        draw_illustration(d, drawing, region, 1.0)

    g = np.ndarray((H // GLOW_SCALE, W // GLOW_SCALE, 4), np.uint8, glow_s.get_data()).copy()
    glow_img = Image.fromarray(g[..., [2, 1, 0]], "RGB").filter(
        ImageFilter.GaussianBlur(theme.glow["line_blur_radius"] / GLOW_SCALE)).resize((W, H), Image.Resampling.BILINEAR)
    frame = renderer.stars.add(renderer.background.copy(), 2.0) + np.asarray(glow_img, np.float32) * 1.35
    m = np.ndarray((H, W, 4), np.uint8, main_s.get_data())
    alpha = m[..., 3:4].astype(np.float32) / 255.0
    frame = frame * (1 - alpha) + m[..., [2, 1, 0]].astype(np.float32)
    image = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).convert("RGBA")

    words = " ".join(text.split()).split(" ") if text.strip() else []
    if words:
        probe = ImageDraw.Draw(image)
        max_w = W * (0.80 if vertical else 0.42)
        size = int(W * (0.095 if vertical else 0.066))
        while True:
            font = ImageFont.truetype(str(theme.font("bold")), size)
            lines: list[list[str]] = [[]]
            for word in words:
                trial = " ".join(lines[-1] + [word])
                if lines[-1] and probe.textlength(trial, font=font) > max_w:
                    lines.append([word])
                else:
                    lines[-1].append(word)
            widest = max(probe.textlength(" ".join(line), font=font) for line in lines)
            if (len(lines) <= (3 if vertical else 4) and widest <= max_w) or size <= 36:
                break
            size -= 4
        gold_words = {_norm(w) for w in gold.split()}
        lh = int(size * 1.12)
        top = int(H * 0.60) if vertical else int(H * 0.5 - lh * len(lines) / 2)
        text_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        glow_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        dt, dg = ImageDraw.Draw(text_layer), ImageDraw.Draw(glow_layer)
        space = probe.textlength(" ", font=font)
        for row, line in enumerate(lines):
            y = top + row * lh
            width = sum(probe.textlength(w, font=font) for w in line) + space * (len(line) - 1)
            x = (W - width) / 2 if vertical else W * 0.07
            for word in line:
                color = theme.rgb("gold") if _norm(word) in gold_words else (246, 246, 246)
                dt.text((x, y), word, font=font, fill=color + (255,))
                dg.text((x, y), word, font=font, fill=color + (160,))
                x += probe.textlength(word, font=font) + space
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(size * 0.22))
        image = Image.alpha_composite(image, glow_layer)
        image = Image.alpha_composite(image, text_layer)

    mark = renderer.captions.wordmark()
    at = (int((W - mark.width) / 2), int(H * 0.90)) if vertical else (int(W * 0.07), int(H * 0.88))
    image.paste(mark, at, mark)
    return image.convert("RGB")


def cover_spec(plan: dict[str, Any]) -> dict[str, str]:
    """The cover chosen by the storyboard, or a fallback from the title."""
    cover = dict(plan.get("cover") or {})
    text = str(cover.get("text") or "").strip()
    if not text:
        title = str(plan.get("title", "")).strip()
        text = " ".join(title.split()[:7])
    return {"text": text, "gold": str(cover.get("gold") or "").strip(),
            "scene": str(cover.get("scene") or "").strip(),
            "thumbnail_moment": str(cover.get("thumbnail_moment") or "").strip()}


def pick_scene(scene_ids: list[str], drawings: dict[str, Any], wanted: str = "") -> str | None:
    """The storyboard's pick, else the most detailed drawing that has an accent."""
    if wanted in drawings:
        return wanted
    best, score = None, -1.0
    for scene_id in scene_ids:
        drawing = drawings.get(scene_id)
        if drawing is None:
            continue
        value = drawing.total * (1.25 if any(s.gold for s in drawing.strokes) else 1.0)
        if value > score:
            best, score = scene_id, value
    return best
