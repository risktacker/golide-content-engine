"""Render a GOLIDE Black video from a scene plan and the owner's recording.

Pipeline per frame: night-sky background (charcoal vignette, faint haze,
slowly drifting and twinkling stars) -> soft glow layer (rendered small,
blurred, added) -> sharp line art -> captions (spoken words, current one bold
with a glow) -> tiny label tag -> wordmark.

Nothing cuts. Between scenes, a drawing that appears in both glides to its
new place; everything else dissolves into points of light that travel and
land where the next drawing is about to be drawn (see Transition). Frames are piped straight into FFmpeg together with the narration,
so there are no intermediate video files and the video is exactly as long as
the recording.
"""

from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from golide_engine.theme import Theme, load_theme

from .align import CaptionChunk, Group, align_lines, caption_chunks, group_lines
from .primitives import ICON_LAYOUTS, PRIMITIVES, Draw, ease, lead_slots

FORMATS = {"short": (1080, 1920), "long": (1920, 1080)}
GLOW_SCALE = 3  # glow layer is rendered at 1/3 size, then blurred and upscaled
TRANSITION_BEFORE = 0.40  # seconds of hand-over before the next line starts
TRANSITION_AFTER = 0.90   # ... and after it starts
PARTICLES = 170


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
    """Charcoal vignette with a very faint blue-violet haze (no stars here)."""
    w, h = layout.width, layout.height
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt(((xx - w / 2) / (w * 0.75)) ** 2 + ((yy - h * 0.42) / (h * 0.75)) ** 2)
    base = np.array(theme.rgb("background"), np.float32)
    lift = np.array(theme.rgb("background_vignette"), np.float32) - base
    image = base + lift * np.clip(1 - dist, 0, 1)[..., None]
    # Haze: low-frequency clouds, a few levels at most, so it reads as depth.
    rng = np.random.default_rng(21)
    for scale, tint in ((9, (5.0, 4.0, 11.0)), (17, (2.0, 4.0, 7.0))):
        cells = rng.random((max(2, h * scale // w), scale)).astype(np.float32)
        cloud = Image.fromarray((cells * 255).astype(np.uint8)).resize((w, h), Image.Resampling.BICUBIC)
        cloud = cloud.filter(ImageFilter.GaussianBlur(w / scale / 2))
        c = (np.asarray(cloud, np.float32) / 255.0) ** 2.2
        image = image + c[..., None] * np.array(tint, np.float32)
    # Fine static grain hides 8-bit banding in the dark vignette.
    image = image + np.random.default_rng(7).uniform(-1.6, 1.6, image.shape).astype(np.float32)
    return np.clip(image, 0, 255)


class StarField:
    """Three depths of small stars that twinkle and drift very slowly."""

    LAYERS = (  # (stars per megapixel, brightness range, drift px/s, twinkle depth)
        (220, (30, 70), 2.0, 0.35),
        (70, (80, 150), 4.5, 0.45),
        (12, (170, 235), 8.0, 0.30),
    )

    def __init__(self, width: int, height: int, seed: int = 11):
        self.w, self.h = width, height
        rng = np.random.default_rng(seed)
        mp = width * height / 1e6
        self.layers = []
        for density, (lo, hi), drift, depth in self.LAYERS:
            n = int(density * mp)
            self.layers.append({
                "x": rng.uniform(0, width, n), "y": rng.uniform(0, height, n),
                "b": rng.uniform(lo, hi, n), "f": rng.uniform(0.15, 0.8, n),
                "ph": rng.uniform(0, math.tau, n), "drift": drift, "depth": depth,
                "tint": rng.choice([0, 1, 2], n, p=[0.75, 0.15, 0.10]),
            })
        self.tints = np.array([[1.0, 1.0, 1.0], [0.85, 0.92, 1.0], [1.0, 0.92, 0.78]], np.float32)

    def add(self, frame: np.ndarray, t: float) -> np.ndarray:
        for layer in self.layers:
            x = (layer["x"] + layer["drift"] * 0.35 * t) % (self.w - 1)
            y = (layer["y"] - layer["drift"] * t) % (self.h - 1)
            b = layer["b"] * (1 - layer["depth"] * (0.5 + 0.5 * np.sin(math.tau * layer["f"] * t + layer["ph"])))
            x0, y0 = x.astype(np.int64), y.astype(np.int64)
            fx, fy = x - x0, y - y0
            rgb = (b[:, None] * self.tints[layer["tint"]]).astype(np.float32)
            # Bilinear splat: sub-pixel drift without shimmering.
            for dx, dy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                                (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
                np.add.at(frame, (y0 + dy, x0 + dx), rgb * wgt[:, None].astype(np.float32))
            if layer["depth"] == self.LAYERS[-1][3]:
                halo = rgb * 0.18
                for dx, dy in ((-1, 0), (2, 0), (0, -1), (0, 2), (-1, -1), (2, 2), (-1, 2), (2, -1)):
                    np.add.at(frame, (np.clip(y0 + dy, 0, self.h - 1), np.clip(x0 + dx, 0, self.w - 1)),
                              halo * (0.55 if abs(dx - 0.5) + abs(dy - 0.5) > 2 else 1.0))
        return frame


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
        self.stars = StarField(self.layout.width, self.layout.height)
        self._transitions: dict[int, "Transition"] = {}
        self.captions = CaptionRenderer(self.layout, self.theme)
        self.colors = _colors(self.theme)
        self.mark = self.captions.wordmark()
        self.end_mark = self.captions.wordmark(size=int(self.layout.caption_size * 1.1), color="text", alpha=255)

    def _draw_args(self, group: Group, t: float):
        n = len(group.lines)
        k = _active(group.lines, t, lambda l: l.start, lambda l: l.end)
        line = group.lines[k]
        local = (t - line.start) / max(0.4, min(line.end - line.start, 2.2))
        gp = min(1.0, (k + ease(local)) / n)
        if group.visual == "logo_end":
            gp = ease((t - group.start) / 1.2)
        return gp, k, n

    def _group_draw(self, main_ctx, glow_ctx, group: Group, t: float, seed: int, alpha: float,
                    carry: dict | None = None, hide: frozenset = frozenset(), gp: float | None = None) -> None:
        primitive = PRIMITIVES.get(group.visual, PRIMITIVES["single_glow"])
        auto_gp, k, n = self._draw_args(group, t)
        for ctx in (main_ctx, glow_ctx):
            ctx.push_group()
        from .illustrate import REGIONS
        primitive(Draw(main_ctx, glow_ctx, auto_gp if gp is None else gp, k, n, t - group.start, seed,
                       self.layout.size / 2, self.colors, tuple(group.icons),
                       carry=carry, hide=hide, visual=group.visual,
                       span=group.end - group.start, region=REGIONS[self.format]))
        for ctx in (main_ctx, glow_ctx):
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(alpha)

    def _points(self, group: Group, seed: int, hide: frozenset) -> np.ndarray:
        """Points on the finished drawing of a scene (unit coordinates)."""
        side, span = 200, 2.5
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, side, side)
        scratch = cairo.ImageSurface(cairo.FORMAT_ARGB32, 4, 4)
        main, glow = cairo.Context(surface), cairo.Context(scratch)
        for ctx in (main, glow):
            ctx.translate(side / 2, side / 2)
            ctx.scale(side / span, side / span)
        self._group_draw(main, glow, group, group.end - 1e-3, seed, 1.0, hide=hide, gp=1.0)
        alpha = np.ndarray((side, side, 4), np.uint8, surface.get_data())[..., 3]
        ys, xs = np.nonzero(alpha > 70)
        if len(xs) == 0:
            return np.zeros((0, 2))
        pts = np.stack([xs, ys], 1).astype(np.float64) / side * span - span / 2
        rng = np.random.default_rng(seed + 101)
        pick = rng.choice(len(pts), PARTICLES, replace=len(pts) < PARTICLES)
        return pts[pick]

    def _transition(self, groups: list[Group], gi: int) -> "Transition":
        if gi not in self._transitions:
            self._transitions[gi] = Transition.between(self, groups[gi - 1], groups[gi], gi)
        return self._transitions[gi]

    def _carried_into(self, groups: list[Group], gi: int) -> set[str]:
        if gi == 0:
            return set()
        return self._transition(groups, gi).shared

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
        # Hand-over window around each scene change (it starts a little before
        # the next line so the dots are travelling as the words land).
        nxt = gi + 1 if gi + 1 < len(groups) and t >= groups[gi + 1].start - TRANSITION_BEFORE else None
        if nxt is not None:
            self._transition(groups, nxt).draw(main, glow, t)
        elif gi > 0 and t < group.start + TRANSITION_AFTER:
            self._transition(groups, gi).draw(main, glow, t)
        else:
            carry = {name: None for name in self._carried_into(groups, gi)}
            self._group_draw(main, glow, group, t, gi, 1.0, carry=carry or None)

        # Glow: blur the small layer and add it onto the background.
        g = np.ndarray((gh, gw, 4), np.uint8, glow_surface.get_data()).copy()
        # Cairo stores premultiplied BGRA, so the colour channels are already
        # weighted by coverage and can be blurred and added directly.
        glow_img = Image.fromarray(g[..., [2, 1, 0]], "RGB")
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(self.theme.glow["line_blur_radius"] / GLOW_SCALE))
        glow_img = glow_img.resize((L.width, L.height), Image.Resampling.BILINEAR)
        frame = self.stars.add(self.background.copy(), t) + np.asarray(glow_img, np.float32) * 1.35

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

    @staticmethod
    def _use_illustrations(plan: dict[str, Any], lines, illustrations: dict[str, Path]):
        """Every line shows its scene's drawing (the closing logo line stays)."""
        from .illustrate import SCENES, vectorize

        SCENES.clear()
        owner: dict[int, str] = {}
        for scene in plan.get("scenes", []):
            path = illustrations.get(scene["id"])
            if path is None or not Path(path).exists():
                continue
            SCENES[scene["id"]] = vectorize(Path(path))
            for index in range(int(scene["first_line"]), int(scene["last_line"]) + 1):
                owner[index] = scene["id"]
        for line in lines:
            if line.visual == "logo_end" and line.index == len(lines) - 1:
                continue
            scene_id = owner.get(line.index)
            if scene_id:
                line.visual = "illustration"
                line.icons = (scene_id,)
        return lines

    def render(self, plan: dict[str, Any], words: list[dict[str, Any]], narration: Path, output: Path,
               duration: float, music: Path | None = None, music_volume: float = 0.03,
               illustrations: dict[str, Path] | None = None) -> Path:
        lines = align_lines(plan, words, duration)
        if illustrations:
            lines = self._use_illustrations(plan, lines, illustrations)
        groups = group_lines(lines)
        chunks = caption_chunks(lines)
        output.parent.mkdir(parents=True, exist_ok=True)
        L = self.layout
        # The owner's voice, small effects timed to the visuals, and a quiet
        # synthesised atmosphere that dips a little more while he speaks.
        from .ambient import render_ambient
        from .sfx import render_sfx

        sfx_path = render_sfx(groups, duration, output.with_name(output.stem + "-sfx.wav"))
        bed_path = render_ambient(duration, output.with_name(output.stem + "-bed.wav"),
                                  seed_text=str(plan.get("title", "")))
        inputs = ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{L.width}x{L.height}",
                  "-r", str(self.fps), "-i", "-", "-i", str(narration), "-i", str(sfx_path),
                  "-i", str(bed_path)]
        audio = ("[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,asplit=2[v][key];"
                 "[2:a]aresample=48000[s];"
                 "[3:a]aresample=48000[b0];"
                 "[b0][key]sidechaincompress=threshold=0.05:ratio=1.8:attack=120:release=1200[b];"
                 "[v][s][b]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.79:level=0:attack=2:release=60[a]")
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
        bed_path.unlink(missing_ok=True)
        if code != 0:
            raise RuntimeError("FFmpeg failed while encoding the vector video")
        return output


@dataclass
class Transition:
    """How one scene becomes the next, without a cut.

    * Drawings present in both scenes glide (position and size) to their new
      place and are never redrawn.
    * The rest of the old scene dissolves into points of light. The points
      travel in a soft arc and land on the shape of the next drawing, which
      is then drawn on by its travelling pen light as the points fade.
    """
    renderer: "VectorRenderer"
    old: Group
    new: Group
    index: int
    shared: set
    old_slots: dict
    new_slots: dict
    src: np.ndarray
    dst: np.ndarray
    bend: np.ndarray

    @classmethod
    def between(cls, renderer: "VectorRenderer", old: Group, new: Group, index: int) -> "Transition":
        old_slots = lead_slots(old.visual, old.icons) if old.visual in ICON_LAYOUTS else {}
        new_slots = lead_slots(new.visual, new.icons) if new.visual in ICON_LAYOUTS else {}
        shared = set(old_slots) & set(new_slots)
        hide = frozenset(shared)
        src = renderer._points(old, index - 1, hide)
        dst = renderer._points(new, index, hide)
        if len(src) and len(dst):
            # Pair points by angle around the centre: the cloud turns into the
            # new shape in one organised sweep instead of criss-crossing.
            src = src[np.argsort(np.arctan2(src[:, 1], src[:, 0]))]
            dst = dst[np.argsort(np.arctan2(dst[:, 1], dst[:, 0]))]
        rng = np.random.default_rng(index)
        bend = rng.uniform(-0.25, 0.25, PARTICLES)
        return cls(renderer, old, new, index, shared, old_slots, new_slots, src, dst, bend)

    def _u(self, t: float) -> float:
        start = self.new.start - TRANSITION_BEFORE
        return min(1.0, max(0.0, (t - start) / (TRANSITION_BEFORE + TRANSITION_AFTER)))

    def draw(self, main, glow, t: float) -> None:
        r = self.renderer
        u = self._u(t)
        # Shared drawings glide over the first half of the window.
        g = ease(min(1.0, u / 0.55))
        carry = {}
        for name in self.shared:
            a, b = self.old_slots[name], self.new_slots[name]
            carry[name] = None if g >= 1 else (a.x + (b.x - a.x) * g, a.y + (b.y - a.y) * g,
                                               a.size + (b.size - a.size) * g)
        hide = frozenset(self.shared)
        # Old scene: fades as it turns to light (its shared drawings are drawn by the new scene).
        old_alpha = 1 - ease(u / 0.30)
        if old_alpha > 0.01:
            r._group_draw(main, glow, self.old, self.old.end - 1e-3, self.index - 1, old_alpha, hide=hide)
        # New scene: draws on normally from the moment its words start.
        if t >= self.new.start or self.shared:
            r._group_draw(main, glow, self.new, max(t, self.new.start), self.index, 1.0, carry=carry or None)
        self._particles(main, glow, u)

    def _particles(self, main, glow, u: float) -> None:
        if not len(self.src) and not len(self.dst):
            return
        src = self.src if len(self.src) else self.dst * 0.15
        dst = self.dst if len(self.dst) else self.src * 1.4
        appear = ease(u / 0.22)
        fade = 1 - ease((u - 0.62) / 0.38)
        alpha = appear * fade
        if alpha <= 0.01:
            return
        travel = ease(min(1.0, max(0.0, (u - 0.12) / 0.5)))
        travel = travel * travel * (3 - 2 * travel)
        delta = dst - src
        normal = np.stack([-delta[:, 1], delta[:, 0]], 1)
        arc = math.sin(math.pi * travel)
        pos = src + delta * travel + normal * (self.bend[:, None] * arc)
        unit = self.renderer.layout.size / 2
        gold = self.renderer.colors["gold"]
        white = self.renderer.colors["white_glow"]
        for ctx, radius, color, a in ((main, 2.0 / unit, white, 0.9 * alpha), (glow, 5.0 / unit, gold, alpha)):
            ctx.save()
            ctx.set_source_rgba(*color, a)
            for x, y in pos:
                ctx.new_sub_path()
                ctx.arc(float(x), float(y), radius, 0, math.tau)
            ctx.fill()
            ctx.restore()
