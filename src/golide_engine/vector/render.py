"""Render a GOLIDE Black video from a scene plan and the owner's recording.

Pipeline per frame: static black background (vignette + faint stars) ->
soft glow layer (rendered small, blurred, added) -> sharp line art ->
captions (spoken words, current one bold with a glow) -> tiny label tag ->
wordmark. Frames are piped straight into FFmpeg together with the narration,
so there are no intermediate video files and the video is exactly as long as
the recording.
"""

from __future__ import annotations

import math
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from golide_engine.theme import Theme, load_theme

from .align import CaptionChunk, Group, align_lines, caption_chunks, group_lines
from .primitives import PRIMITIVES, Draw, ease

FORMATS = {"short": (1080, 1920), "long": (1920, 1080)}
GLOW_SCALE = 3  # glow layer is rendered at 1/3 size, then blurred and upscaled
CROSSFADE = 0.35


@dataclass
class Layout:
    width: int
    height: int
    cx: float
    cy: float
    size: float  # side of the drawing square in px
    caption_y: float
    caption_size: int
    label_y: float

    @classmethod
    def for_format(cls, format_name: str) -> "Layout":
        width, height = FORMATS[format_name]
        if format_name == "short":
            return cls(width, height, width / 2, height * 0.40, width * 0.74, height * 0.70, 46, height * 0.165)
        return cls(width, height, width / 2, height * 0.42, height * 0.60, height * 0.86, 44, height * 0.07)


def _background(layout: Layout, theme: Theme) -> np.ndarray:
    w, h = layout.width, layout.height
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt(((xx - w / 2) / (w * 0.75)) ** 2 + ((yy - h * 0.42) / (h * 0.75)) ** 2)
    base = np.array(theme.rgb("background"), np.float32)
    lift = np.array(theme.rgb("background_vignette"), np.float32) - base
    image = base + lift * np.clip(1 - dist, 0, 1)[..., None]
    # Fine static grain hides 8-bit banding in the dark vignette.
    image = image + np.random.default_rng(7).uniform(-1.6, 1.6, image.shape).astype(np.float32)
    rng = random.Random(11)
    for _ in range(int(w * h / 9000)):
        x, y = rng.randrange(w), rng.randrange(h)
        image[y, x] = image[y, x] + rng.uniform(20, 60)
    return np.clip(image, 0, 255)


class CaptionRenderer:
    def __init__(self, layout: Layout, theme: Theme):
        self.layout = layout
        self.theme = theme
        size = layout.caption_size
        self.light = ImageFont.truetype(str(theme.font("light")), size)
        self.bold = ImageFont.truetype(str(theme.font("bold")), size)
        self.mono = ImageFont.truetype(str(theme.font("mono")), max(16, int(size * 0.56)))
        self.mark = ImageFont.truetype(str(theme.font("regular")), max(14, int(size * 0.38)))
        self._cache: dict[tuple, Image.Image] = {}

    @staticmethod
    def _clean(text: str) -> str:
        return text.strip()

    def caption(self, chunk: CaptionChunk, t: float, fade: float) -> Image.Image:
        current = -1
        for i, word in enumerate(chunk.words):
            if word.start <= t:
                current = i
        emphasis = {w.lower().strip(".,!?;:'\"") for w in chunk.emphasis.split()}
        key = (id(chunk), current, round(fade, 2))
        if key in self._cache:
            return self._cache[key]
        if len(self._cache) > 64:
            self._cache.clear()
        w = self.layout.width
        size = self.layout.caption_size
        line_h = int(size * 1.35)
        layer = Image.new("RGBA", (w, line_h * 3), (0, 0, 0, 0))
        glow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        draw, gdraw = ImageDraw.Draw(layer), ImageDraw.Draw(glow)
        words = [self._clean(word.text) for word in chunk.words]
        fonts = []
        for word in words:
            fonts.append(self.bold if word.lower().strip(".,!?;:'\"") in emphasis else self.light)
        space = draw.textlength(" ", font=self.light)
        max_w = w * (0.80 if self.layout.width < self.layout.height else 0.62)
        rows: list[list[int]] = [[]]
        width = 0.0
        for i, word in enumerate(words):
            ww = draw.textlength(word, font=fonts[i])
            add = ww if not rows[-1] else ww + space
            if rows[-1] and width + add > max_w:
                rows.append([i])
                width = ww
            else:
                rows[-1].append(i)
                width += add
        text_rgb = self.theme.rgb("text")
        muted = self.theme.rgb("text_muted")
        for r, row in enumerate(rows[:3]):
            row_w = sum(draw.textlength(words[i], font=fonts[i]) for i in row) + space * (len(row) - 1)
            x = (w - row_w) / 2
            y = r * line_h
            for i in row:
                spoken = i <= current
                is_now = i == current
                color = text_rgb if spoken else muted
                alpha = int(255 * fade * (1.0 if spoken else 0.75))
                draw.text((x, y), words[i], font=fonts[i], fill=color + (alpha,))
                if is_now and fonts[i] is self.bold:
                    gdraw.text((x, y), words[i], font=fonts[i], fill=(255, 255, 255, int(220 * fade)))
                x += draw.textlength(words[i], font=fonts[i]) + space
        glow = glow.filter(ImageFilter.GaussianBlur(size * 0.28))
        result = Image.alpha_composite(glow, layer)
        self._cache[key] = result
        return result

    def label(self, text: str, color: tuple[int, int, int], alpha: float) -> Image.Image:
        spaced = "  ".join(text.split())
        draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        tw = int(draw.textlength(spaced, font=self.mono)) + 4
        th = int(self.mono.size * 1.4)
        img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((2, 0), spaced, font=self.mono, fill=color + (int(255 * alpha),))
        return img

    def wordmark(self, size: int | None = None, color: str = "text_muted", alpha: int = 200) -> Image.Image:
        font = self.mark if size is None else ImageFont.truetype(str(self.theme.font("regular")), size)
        text = "  ".join(self.theme.watermark["text"])
        draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        tw = int(draw.textlength(text, font=font)) + 4
        img = Image.new("RGBA", (tw, int(font.size * 1.5)), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((2, 0), text, font=font, fill=self.theme.rgb(color) + (alpha,))
        return img


def _colors(theme: Theme) -> dict[str, tuple[float, float, float]]:
    return {name: tuple(v / 255 for v in theme.rgb(name)) for name in theme.raw["colors"]}


def _active(items, t, key_start, key_end):
    for index, item in enumerate(items):
        if key_start(item) <= t < key_end(item):
            return index
    return len(items) - 1 if items and t >= key_start(items[-1]) else 0


class VectorRenderer:
    def __init__(self, format_name: str, theme: Theme | None = None, fps: int = 30):
        if format_name not in FORMATS:
            raise ValueError(f"unknown format {format_name}")
        self.format = format_name
        self.theme = theme or load_theme()
        self.fps = fps
        self.layout = Layout.for_format(format_name)
        self.background = _background(self.layout, self.theme)
        self.captions = CaptionRenderer(self.layout, self.theme)
        self.colors = _colors(self.theme)
        self.mark = self.captions.wordmark()
        self.end_mark = self.captions.wordmark(size=int(self.layout.caption_size * 1.1), color="text", alpha=255)

    def _group_draw(self, main_ctx, glow_ctx, group: Group, t: float, seed: int, alpha: float) -> None:
        primitive = PRIMITIVES.get(group.visual, PRIMITIVES["single_glow"])
        n = len(group.lines)
        k = _active(group.lines, t, lambda l: l.start, lambda l: l.end)
        line = group.lines[k]
        local = (t - line.start) / max(0.4, min(line.end - line.start, 2.2))
        gp = min(1.0, (k + ease(local)) / n)
        if group.visual == "logo_end":
            gp = ease((t - group.start) / 1.2)
        for ctx in (main_ctx, glow_ctx):
            ctx.push_group()
        primitive(Draw(main_ctx, glow_ctx, gp, k, n, t - group.start, seed,
                       self.layout.size / 2, self.colors, tuple(group.icons)))
        for ctx in (main_ctx, glow_ctx):
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(alpha)

    def frame(self, t: float, groups: list[Group], chunks: list[CaptionChunk], duration: float) -> np.ndarray:
        L = self.layout
        main_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, L.width, L.height)
        gw, gh = L.width // GLOW_SCALE, L.height // GLOW_SCALE
        glow_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, gw, gh)
        main = cairo.Context(main_surface)
        glow = cairo.Context(glow_surface)
        for ctx, scale in ((main, 1.0), (glow, 1 / GLOW_SCALE)):
            ctx.scale(scale, scale)
            ctx.translate(L.cx, L.cy)
            ctx.scale(L.size / 2, L.size / 2)

        gi = _active(groups, t, lambda g: g.start, lambda g: g.end)
        group = groups[gi]
        into = t - group.start
        if gi > 0 and into < CROSSFADE:
            a = ease(into / CROSSFADE)
            self._group_draw(main, glow, groups[gi - 1], groups[gi - 1].end - 1e-3, gi - 1, 1 - a)
            self._group_draw(main, glow, group, t, gi, a)
        else:
            self._group_draw(main, glow, group, t, gi, 1.0)

        # Glow: blur the small layer and add it onto the background.
        g = np.ndarray((gh, gw, 4), np.uint8, glow_surface.get_data()).copy()
        # Cairo stores premultiplied BGRA, so the colour channels are already
        # weighted by coverage and can be blurred and added directly.
        glow_img = Image.fromarray(g[..., [2, 1, 0]], "RGB")
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(self.theme.glow["line_blur_radius"] / GLOW_SCALE))
        glow_img = glow_img.resize((L.width, L.height), Image.Resampling.BILINEAR)
        frame = self.background + np.asarray(glow_img, np.float32) * 1.35

        m = np.ndarray((L.height, L.width, 4), np.uint8, main_surface.get_data())
        alpha = m[..., 3:4].astype(np.float32) / 255.0
        rgb = m[..., [2, 1, 0]].astype(np.float32)  # premultiplied
        frame = rgb + frame * (1 - alpha)
        image = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8), "RGB")

        # Captions.
        ci = _active(chunks, t, lambda c: c.start, lambda c: c.end)
        if chunks:
            chunk = chunks[ci]
            fade = min(1.0, (t - chunk.start) / 0.18 + 0.2) if t >= chunk.start else 0.0
            if t > duration - 0.5:
                fade *= max(0.0, (duration - t) / 0.5)
            cap = self.captions.caption(chunk, t, fade)
            image.paste(cap, (0, int(L.caption_y)), cap)

        # Label tag for the active line.
        line_index = _active(group.lines, t, lambda l: l.start, lambda l: l.end)
        label = group.lines[line_index].label
        if label:
            color = self.theme.rgb("gold" if gi % 2 == 0 else "cyan")
            tag = self.captions.label(label, color, min(1.0, (t - group.lines[line_index].start) / 0.3))
            image.paste(tag, (int(L.cx - tag.width / 2), int(L.label_y)), tag)

        if group.visual == "logo_end":
            a = ease((t - group.start) / 0.8)
            mark = self.end_mark.copy()
            mark.putalpha(mark.getchannel("A").point(lambda v: int(v * a)))
            image.paste(mark, (int(L.cx - mark.width / 2), int(L.cy + L.size * 0.36)), mark)
        else:
            margin = int(L.width * 0.05)
            image.paste(self.mark, (L.width - self.mark.width - margin, margin), self.mark)
        return np.asarray(image)

    def render(self, plan: dict[str, Any], words: list[dict[str, Any]], narration: Path, output: Path,
               duration: float, music: Path | None = None, music_volume: float = 0.03) -> Path:
        lines = align_lines(plan, words, duration)
        groups = group_lines(lines)
        chunks = caption_chunks(lines)
        output.parent.mkdir(parents=True, exist_ok=True)
        L = self.layout
        # No music: the owner's voice plus small effects timed to the visuals.
        from .sfx import render_sfx

        sfx_path = render_sfx(groups, duration, output.with_name(output.stem + "-sfx.wav"))
        inputs = ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{L.width}x{L.height}",
                  "-r", str(self.fps), "-i", "-", "-i", str(narration), "-i", str(sfx_path)]
        audio = ("[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[v];"
                 "[2:a]aresample=48000[s];"
                 "[v][s]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[a]")
        command = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", audio,
                   "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                   "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                   "-t", f"{duration:.3f}", "-movflags", "+faststart", str(output)]
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        assert process.stdin is not None
        total = int(math.ceil(duration * self.fps))
        try:
            for index in range(total):
                process.stdin.write(self.frame(index / self.fps, groups, chunks, duration).tobytes())
        finally:
            process.stdin.close()
        code = process.wait()
        sfx_path.unlink(missing_ok=True)
        if code != 0:
            raise RuntimeError("FFmpeg failed while encoding the vector video")
        return output
