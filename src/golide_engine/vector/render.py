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
from .ambience import Ambience, AmbientState, StarField, crossfade, mix  # noqa: F401 (StarField re-exported)
from .primitives import ICON_LAYOUTS, PRIMITIVES, Draw, ease, lead_slots

FORMATS = {"short": (1080, 1920), "long": (1920, 1080)}
GLOW_SCALE = 3  # glow layer is rendered at 1/3 size, then blurred and upscaled
TRANSITION_BEFORE = 0.40  # seconds of hand-over before the next line starts
TRANSITION_AFTER = 0.90   # ... and after it starts
CHAPTER_CARD_SECONDS = 2.8  # how long a chapter card stays at the start of a chapter
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
    card_zone: tuple = (0.0, 0.0)  # (top, bottom) in px: where spoken numbers sit, clear of the drawing

    @classmethod
    def for_format(cls, format_name: str) -> "Layout":
        width, height = FORMATS[format_name]
        if format_name == "short":
            return cls(width, height, width / 2, height * 0.40, width * 0.74, height * 0.635, 46, height * 0.115,
                       (height * 0.070, height * 0.165))
        return cls(width, height, width / 2, height * 0.42, height * 0.60, height * 0.86, 44, height * 0.07,
                   (height * 0.030, height * 0.180))


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

    def caption(self, chunk: CaptionChunk, t: float, fade: float, accent: tuple | None = None) -> Image.Image:
        current = -1
        for i, word in enumerate(chunk.words):
            if word.start <= t:
                current = i
        key = (id(chunk), current, round(fade, 2), accent)
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
        for i, word in enumerate(words):
            fonts.append(self.bold if i in chunk.keys else self.light)
        space = draw.textlength(" ", font=self.light)
        max_w = w * (0.72 if self.layout.width < self.layout.height else 0.62)  # tall phones crop the sides
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
        # 2026-10-18: key terms light up in the scene's accent (gold, rose, teal, ivory,
        # copper by meaning), not always gold.
        gold = tuple(accent) if accent else self.theme.rgb("gold")
        dim_gold = tuple(int(c * 0.62) for c in gold)
        for r, row in enumerate(rows[:3]):
            row_w = sum(draw.textlength(words[i], font=fonts[i]) for i in row) + space * (len(row) - 1)
            x = (w - row_w) / 2
            y = r * line_h
            for i in row:
                spoken = i <= current
                is_now = i == current
                key_term = fonts[i] is self.bold
                ww = draw.textlength(words[i], font=fonts[i])
                # Key terms ("crypto agility", "Nvidia", "25%") light up in gold and
                # stay gold once said, with a gold underline, so the idea sticks.
                if key_term:
                    color = gold if spoken else dim_gold
                else:
                    color = text_rgb if spoken else muted
                alpha = int(255 * fade * (1.0 if spoken else 0.75))
                draw.text((x, y), words[i], font=fonts[i], fill=color + (alpha,))
                if key_term and spoken:
                    gdraw.text((x, y), words[i], font=fonts[i],
                               fill=gold + (int((230 if is_now else 120) * fade),))
                    uy = y + int(size * 1.18)
                    pos = row.index(i)
                    joined = pos + 1 < len(row) and fonts[row[pos + 1]] is self.bold and row[pos + 1] <= current
                    draw.line([(x, uy), (x + ww + (space if joined else 0), uy)],
                              fill=gold + (int(200 * fade),), width=max(2, size // 16))
                x += ww + space
        glow = glow.filter(ImageFilter.GaussianBlur(size * 0.28))
        result = Image.alpha_composite(glow, layer)
        self._cache[key] = result
        return result

    def number_card(self, text: str, accent: tuple, a: float, pop: float) -> Image.Image:
        """A spoken number, big, in the scene's accent with a soft glow (2026-10-18).
        Sized to fit its own zone above the drawing, so it never covers anything."""
        top, bottom = self.layout.card_zone
        max_h, max_w = (bottom - top) * 0.62, self.layout.width * 0.84
        probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
        size = int(max_h * 1.3)
        while size > 16:
            font = ImageFont.truetype(str(self.theme.font("bold")), size)
            x0, y0, x1, y1 = probe.textbbox((0, 0), text, font=font)
            if x1 - x0 <= max_w and y1 - y0 <= max_h:
                break
            size -= 4
        size = max(12, int(size * pop))
        font = ImageFont.truetype(str(self.theme.font("bold")), size)
        x0, y0, x1, y1 = probe.textbbox((0, 0), text, font=font)
        pad = int(size * 0.5)
        w, h = x1 - x0 + 2 * pad, y1 - y0 + 2 * pad
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(glow).text((pad - x0, pad - y0), text, font=font, fill=tuple(accent) + (int(220 * a),))
        ImageDraw.Draw(layer).text((pad - x0, pad - y0), text, font=font, fill=tuple(accent) + (int(255 * a),),
                                   stroke_width=max(1, size // 40), stroke_fill=(10, 10, 12, int(160 * a)))
        glow = glow.filter(ImageFilter.GaussianBlur(size * 0.18))
        return Image.alpha_composite(glow, layer)

    def label(self, text: str, color: tuple[int, int, int], alpha: float) -> Image.Image:
        spaced = "  ".join(text.split())
        draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        tw = int(draw.textlength(spaced, font=self.mono)) + 4
        th = int(self.mono.size * 1.4)
        img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((2, 0), spaced, font=self.mono, fill=color + (int(255 * alpha),))
        return img

    def follow_pill(self, done: bool = False) -> Image.Image:
        """The call-out pill from the reference endings: a soft white pill with dark
        text, '+ FOLLOW GOLIDE' while the owner asks, then '✓ MORE ON ITS WAY'."""
        key = ("follow", done)
        if key in self._cache:
            return self._cache[key]
        size = self.layout.caption_size
        font = ImageFont.truetype(str(self.theme.font("bold")), max(18, int(size * 0.6)))
        text = "MORE ON ITS WAY" if done else "FOLLOW GOLIDE"
        probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        spacing = size * 0.06
        tw = sum(probe.textlength(ch, font=font) for ch in text) + spacing * (len(text) - 1)
        icon = size * 0.5
        pad_x, pad_y = int(size * 0.85), int(size * 0.4)
        gap = size * 0.4
        width = int(icon + gap + tw) + pad_x * 2
        height = int(font.size * 1.3) + pad_y * 2
        margin = int(size * 0.6)  # room for the glow
        layer = Image.new("RGBA", (width + margin * 2, height + margin * 2), (0, 0, 0, 0))
        glow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        box = (margin, margin, margin + width, margin + height)
        ImageDraw.Draw(glow).rounded_rectangle(box, radius=height // 2, fill=(255, 255, 255, 150))
        draw = ImageDraw.Draw(layer)
        draw.rounded_rectangle(box, radius=height // 2, fill=(244, 241, 236, 255))
        ink = (22, 22, 26, 255)
        cx, cy, half = margin + pad_x + icon / 2, margin + height / 2, icon * 0.42
        w = max(3, int(size * 0.075))
        if done:  # check mark
            draw.line([(cx - half, cy), (cx - half * 0.25, cy + half * 0.7), (cx + half, cy - half * 0.7)],
                      fill=ink, width=w, joint="curve")
        else:  # plus
            draw.line([(cx - half, cy), (cx + half, cy)], fill=ink, width=w)
            draw.line([(cx, cy - half), (cx, cy + half)], fill=ink, width=w)
        x = margin + pad_x + icon + gap
        for ch in text:
            draw.text((x, cy), ch, font=font, fill=ink, anchor="lm")
            x += probe.textlength(ch, font=font) + spacing
        glow = glow.filter(ImageFilter.GaussianBlur(size * 0.35))
        pill = Image.alpha_composite(glow, layer)
        self._cache[key] = pill
        return pill

    def chapter_card(self, number: str, title: str) -> Image.Image:
        """'02  WHERE IT HIDES': gold number, spaced white title, soft gold glow."""
        key = ("chapter", number, title)
        if key in self._cache:
            return self._cache[key]
        size = self.layout.caption_size
        num_font = ImageFont.truetype(str(self.theme.font("mono")), int(size * 1.9))
        title_font = ImageFont.truetype(str(self.theme.font("regular")), int(size * 0.95))
        title_text = "  ".join(title.upper().split())
        title_text = " ".join(title_text)  # letter-spaced, the way the wordmark is
        probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        nw = probe.textlength(number, font=num_font)
        tw = probe.textlength(title_text, font=title_font)
        gap = size * 0.7
        pad = int(size * 0.8)
        width = int(nw + gap + tw) + pad * 2
        height = int(size * 2.6) + pad
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        mid = height / 2
        gold = self.theme.rgb("gold")
        draw.text((pad, mid), number, font=num_font, fill=gold + (255,), anchor="lm")
        line_x = pad + nw + gap * 0.5
        draw.line([(line_x, mid - size * 0.42), (line_x, mid + size * 0.42)], fill=gold + (150,), width=2)
        draw.text((pad + nw + gap, mid), title_text, font=title_font, fill=self.theme.rgb("text") + (255,), anchor="lm")
        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ImageDraw.Draw(glow).text((pad, mid), number, font=num_font, fill=gold + (170,), anchor="lm")
        glow = glow.filter(ImageFilter.GaussianBlur(size * 0.35))
        result = Image.alpha_composite(glow, layer)
        self._cache[key] = result
        return result

    def wordmark(self, size: int | None = None, color: str = "text_muted", alpha: int = 200) -> Image.Image:
        font = self.mark if size is None else ImageFont.truetype(str(self.theme.font("regular")), size)
        text = "  ".join(self.theme.watermark["text"])
        draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        tw = int(draw.textlength(text, font=font)) + 4
        img = Image.new("RGBA", (tw, int(font.size * 1.5)), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((2, 0), text, font=font, fill=self.theme.rgb(color) + (alpha,))
        return img


def _colors(theme: Theme) -> dict[str, tuple[float, float, float]]:
    from .illustrate import ACCENTS

    colors = {name: tuple(v / 255 for v in theme.rgb(name)) for name in theme.raw["colors"]}
    colors.update({f"accent_{name}": tuple(v / 255 for v in rgb) for name, rgb in ACCENTS.items()})
    return colors


def _active(items, t, key_start, key_end):
    for index, item in enumerate(items):
        if key_start(item) <= t < key_end(item):
            return index
    return len(items) - 1 if items and t >= key_start(items[-1]) else 0


BODY_CUT = 0.85  # how much of the background and set is replaced inside the object's shape
BODY_FILL = np.array((17, 19, 26), np.float32)   # the object's own dark body, a shade above black
BODY_TINT = 0.07  # and a touch of its accent, so it reads as a solid thing, not a hole
# 2026-10-31 (owner: "the shorts look like covers... skeletons... we can build images based on
# code and good colouring, so there is canvas in looking"): the parts of a drawing are painted,
# each enclosed region its own tone from the scene's palette, lit from above.
PAINT = False   # preview only until the owner approves the look
# name: (base colour, finish 0 matte / 1 metal / 2 gloss, coverage). Real colours, darkened a
# little so the white lines stay the brightest thing in the frame.
MATERIALS = {
    "aluminium": ((150, 156, 165), 1, 0.92), "dark-metal": ((62, 66, 74), 1, 0.95),
    "black": ((26, 28, 32), 2, 0.96), "white": ((205, 205, 200), 0, 0.85),
    "gold": ((190, 148, 62), 1, 0.95), "copper": ((176, 98, 60), 1, 0.95),
    "red": ((158, 30, 36), 2, 0.95), "blue": ((36, 72, 160), 2, 0.95), "green": ((34, 110, 72), 2, 0.95),
    "glass": ((30, 44, 60), 2, 0.70), "screen": ((18, 24, 38), 2, 0.95), "wood": ((116, 78, 48), 0, 0.92),
    "concrete": ((112, 112, 108), 0, 0.9), "paper": ((222, 216, 200), 0, 0.88), "fabric": ((84, 86, 96), 0, 0.9),
}
PAINT_IN = (0.55, 0.95)   # the colour fades in as the pen finishes the drawing (share of the reveal)


class VectorRenderer:
    def __init__(self, format_name: str, theme: Theme | None = None, fps: int = 30):
        if format_name not in FORMATS:
            raise ValueError(f"unknown format {format_name}")
        self.format = format_name
        self.theme = theme or load_theme()
        self.fps = fps
        self.layout = Layout.for_format(format_name)
        self.ambience = Ambience(self.layout, self.theme, format_name)
        from .stage import Stages
        self.stages = Stages(self.layout, format_name)
        self._transitions: dict[int, "Transition"] = {}
        self.chapters: list = []
        self.follow: set[int] = set()  # spoken line indexes of the follow call-out
        self.captions = CaptionRenderer(self.layout, self.theme)
        self.colors = _colors(self.theme)
        self.mark = self.captions.wordmark()
        self.end_mark = self.captions.wordmark(size=int(self.layout.caption_size * 1.1), color="text", alpha=255)

    def _cover(self, plan: dict[str, Any], output: Path) -> np.ndarray | None:
        """Build the cover card, save it beside the video, and return it as a frame."""
        from .cover import cover_spec, pick_scene, render_cover
        from .illustrate import SCENES

        try:
            spec = cover_spec(plan)
            ids = [str(scene.get("id")) for scene in plan.get("scenes") or []]
            scene = pick_scene(ids, SCENES, spec["scene"])
            from .thumbnail_style import palette_rgb, thumbnail_colors
            # 2026-10-18: the punch words take the video's first meaning colour.
            punch = palette_rgb(thumbnail_colors(plan.get("cover") or {}, plan.get("scenes") or []))[0]
            image = render_cover(self, SCENES.get(scene) if scene else None, spec["text"], spec["gold"], punch)
            image.save(output.with_name(output.stem + "-cover.jpg"), quality=93)
            return np.asarray(image, np.float32)
        except Exception as exc:  # a cover must never stop a video
            print({"status": "cover_failed", "error": str(exc)})
            return None

    def _action_cues(self, plan: dict[str, Any], lines, groups) -> list[tuple[float, str]]:
        from .illustrate import ACCENT_DELAY, SCENES
        from .sfx import action_cues

        lights = [g.start + ACCENT_DELAY for g in groups
                  if g.visual == "illustration" and g.icons and g.icons[0] in SCENES
                  and SCENES[g.icons[0]].entrance == "fade"]
        asked = [line for line in lines if line.index in self.follow]
        follow = (asked[0].start, asked[-1].end) if asked else None
        return action_cues(lines, plan.get("scenes") or [], lights, follow)

    def _follow_state(self, groups, t: float):
        """(done, alpha) while the call-out pill shows: from the follow sentence to the end."""
        if not self.follow:
            return None
        lines = [line for group in groups for line in group.lines]
        asked = [line for line in lines if line.index in self.follow]
        if not asked:
            return None
        start, end = asked[0].start, asked[-1].end
        if t < start:
            return None
        finale = lines[-1].end
        a = min(1.0, (t - start) / 0.3) * min(1.0, max(0.0, (finale - t) / 0.5))
        done = t >= end - 0.05
        if done:
            a *= min(1.0, 0.35 + (t - end) / 0.25)  # quick swap to the check
        return done, max(0.0, a)

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
                    carry: dict | None = None, hide: frozenset = frozenset(), gp: float | None = None,
                    zoom: float = 1.0) -> None:
        primitive = PRIMITIVES.get(group.visual, PRIMITIVES["single_glow"])
        auto_gp, k, n = self._draw_args(group, t)
        for ctx in (main_ctx, glow_ctx):
            ctx.push_group()
        from .illustrate import REGIONS
        from .pacing import HOOK_SECONDS
        words = sum(len(str(line.text).split()) for line in group.lines)
        primitive(Draw(main_ctx, glow_ctx, auto_gp if gp is None else gp, k, n, t - group.start, seed,
                       self.layout.size / 2, self.colors, tuple(group.icons),
                       carry=carry, hide=hide, visual=group.visual,
                       span=group.end - group.start, region=REGIONS[self.format], zoom=zoom,
                       words=words, hook=group.start < HOOK_SECONDS.get(self.format, 30.0),
                       marking=self._marking(group, t)))
        for ctx in (main_ctx, glow_ctx):
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(alpha)

    def _accent_rgb(self, group: Group) -> tuple:
        """The active scene's accent colour (0-255 RGB), gold when it has none."""
        from .illustrate import SCENES

        drawing = SCENES.get(group.icons[0]) if group.icons else None
        name = getattr(drawing, "accent", "gold") if drawing is not None else "gold"
        rgb = self.colors.get(f"accent_{name}", self.colors["gold"])
        return tuple(int(round(c * 255)) for c in rgb)

    def _look(self, group: Group, t: float) -> AmbientState:
        """What the background shows for one scene at time ``t`` (see vector.ambience)."""
        from .illustrate import LIFE_PUSH, SCENES

        drawing = SCENES.get(group.icons[0]) if group.icons else None
        lesson = bool(drawing is not None and (drawing.figure or (drawing.companion is not None
                                                                   and drawing.companion.figure)))
        breathe = min(1.0, max(0.0, (t - group.start) / max(0.5, group.end - group.start)))
        marking = self._marking(group, t)
        push = LIFE_PUSH * breathe + 0.14 * math.sin(math.pi * min(1.0, marking)) ** 0.6
        light = 0.0 if group.visual == "logo_end" else 1.0
        return AmbientState(self._accent_rgb(group), 1.0 if lesson else 0.0, push, light)

    def _ambient(self, groups: list[Group], gi: int, t: float) -> AmbientState:
        """The background state, cross-faded over the same hand-over window as the drawings."""
        group = groups[gi]
        if gi + 1 < len(groups) and t >= groups[gi + 1].start - TRANSITION_BEFORE:
            old, new = group, groups[gi + 1]
        elif gi > 0 and t < group.start + TRANSITION_AFTER:
            old, new = groups[gi - 1], group
        else:
            return self._look(group, t)
        w = crossfade(t, new.start, TRANSITION_BEFORE, TRANSITION_AFTER)
        return mix(self._look(old, min(t, old.end)), self._look(new, max(t, new.start)), w)

    def _stage_of(self, group: Group) -> str:
        """The set behind a scene (vector.stage): the storyboard's choice, the plain sky for
        exact figures and the closing logo, the floor grid otherwise."""
        from .illustrate import SCENES

        if group.visual == "logo_end":
            return "none"
        drawing = SCENES.get(group.icons[0]) if group.icons else None
        if drawing is None:
            return "none"
        if drawing.figure:
            return drawing.stage or "none"   # maths figures keep the lesson grid; charts carry "market"
        return drawing.stage or "grid"

    def _with_stage(self, frame: np.ndarray, groups: list[Group], gi: int, t: float) -> np.ndarray:
        """Add the scene's set under the drawing, cross-faded with the next one at a scene change."""
        group = groups[gi]
        pairs = [(group, 1.0)]
        if gi + 1 < len(groups) and t >= groups[gi + 1].start - TRANSITION_BEFORE:
            w = crossfade(t, groups[gi + 1].start, TRANSITION_BEFORE, TRANSITION_AFTER)
            pairs = [(group, 1 - w), (groups[gi + 1], w)]
        elif gi > 0 and t < group.start + TRANSITION_AFTER:
            w = crossfade(t, group.start, TRANSITION_BEFORE, TRANSITION_AFTER)
            pairs = [(groups[gi - 1], 1 - w), (group, w)]
        breathe = 0.92 + 0.08 * math.sin(t * 0.9)
        for g, weight in pairs:
            if weight <= 0.001:
                continue
            image = self.stages.image(self._stage_of(g), self._accent_rgb(g), self._footprint(groups.index(g), g))
            if image is not None:
                frame = frame + image * (weight * breathe)
        return frame

    def _footprint(self, gi: int, group: Group):
        """(left, right, bottom, top) in px of a scene's finished drawing, measured once by drawing
        it off screen: the stage floor starts where the object stands (owner review 2026-10-29)."""
        cache = self.__dict__.setdefault("_footprints", {})
        key = (gi, group.start, group.icons)
        if key not in cache:
            L = self.layout
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, L.width // 2, L.height // 2)
            glow = cairo.ImageSurface(cairo.FORMAT_ARGB32, 8, 8)
            ctxs = (cairo.Context(surface), cairo.Context(glow))
            for ctx, scale in zip(ctxs, (0.5, 0.5)):
                ctx.scale(scale, scale)
                ctx.translate(L.cx, L.cy)
                ctx.scale(L.size / 2, L.size / 2)
            try:
                self._group_draw(ctxs[0], ctxs[1], group, max(group.start, group.end - 0.05), gi, 1.0, gp=1.0)
            except Exception:  # noqa: BLE001 - a failed measure just keeps the default floor
                cache[key] = None
                return None
            a = np.ndarray((L.height // 2, surface.get_stride() // 4, 4), np.uint8, surface.get_data())[:, :L.width // 2, 3]
            rows = np.where((a > 60).sum(axis=1) >= 3)[0]
            cols = np.where((a > 60).sum(axis=0) >= 2)[0]
            cache[key] = None if len(rows) == 0 else (float(cols[0] * 2), float(cols[-1] * 2), float(rows[-1] * 2),
                                                       float(rows[0] * 2))
        return cache[key]

    def _body(self, alpha: np.ndarray) -> np.ndarray:
        """The drawing's solid shape (H x W x 1, 0..1): its outline closed and filled, so the set
        and the background stay behind the object instead of showing through it."""
        from scipy import ndimage

        a = alpha[..., 0] if alpha.ndim == 3 else alpha
        if a.dtype != np.uint8:
            a = (np.clip(a, 0, 1) * 255).astype(np.uint8)
        h, w = a.shape
        k = 4
        a = a[: h // k * k, : w // k * k]
        small = np.maximum.reduce([a[i::k, j::k] for i in range(k) for j in range(k)]) > 50
        if not small.any():
            return np.zeros((h, w, 1), np.float32)
        closed = ndimage.binary_dilation(small, iterations=3)
        filled = ndimage.binary_fill_holes(closed)
        body = ndimage.binary_erosion(filled, iterations=2) | small
        soft = Image.fromarray((body * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
        return (np.asarray(soft.resize((w, h), Image.Resampling.BILINEAR), np.float32) / 255)[..., None]

    def _finished_alpha(self, group: Group, t: float, gi: int) -> np.ndarray:
        """The scene's drawing as it will look when finished, at this moment's position."""
        L = self.layout
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, L.width, L.height)
        glow = cairo.ImageSurface(cairo.FORMAT_ARGB32, 8, 8)
        ctxs = (cairo.Context(surface), cairo.Context(glow))
        for ctx in ctxs:
            ctx.translate(L.cx, L.cy)
            ctx.scale(L.size / 2, L.size / 2)
        self._group_draw(ctxs[0], ctxs[1], group, t, gi, 1.0, gp=1.0)
        return np.ndarray((L.height, surface.get_stride() // 4, 4), np.uint8, surface.get_data())[:, :L.width, 3].copy()

    def _paint(self, alpha: np.ndarray, body: np.ndarray, drawing) -> tuple[np.ndarray, np.ndarray]:
        """Real materials inside the drawing (2026-10-31: "make the colour look real").

        Every area the lines enclose is painted. Areas on the outside of the object (its shell)
        get the storyboard's "body" material, areas inside it (a screen, a window) the "inner"
        one; people are neutral. Each area is lit from its own top, metals get a soft band of
        light and glossy surfaces a diagonal reflection. Worked out at half resolution with
        no blur, so the colour sits inside the lines. Returns (colour, coverage)."""
        from scipy import ndimage

        h, w = alpha.shape[:2]
        k = 2
        a = alpha[: h // k * k, : w // k * k]
        lines = np.maximum.reduce([a[i::k, j::k] for i in range(k) for j in range(k)]) > 60
        solid = body[: h // k * k: k, : w // k * k: k, 0] > 0.5
        sh, sw = solid.shape
        colour = np.zeros((sh, sw, 3), np.float32)
        cover = np.zeros((sh, sw), np.float32)
        regions, count = ndimage.label(solid & ~ndimage.binary_dilation(lines, iterations=1))
        if count:
            people = bool(getattr(drawing, "people", False))
            body_name = "white" if people else (getattr(drawing, "body", "") or "aluminium")
            inner_name = "white" if people else (getattr(drawing, "inner", "") or "glass")
            outside = ~ndimage.binary_dilation(solid, iterations=2)
            near_out = ndimage.binary_dilation(outside, iterations=4)
            idx = np.arange(1, count + 1)
            touches = ndimage.maximum(near_out, regions, idx) > 0
            sizes = ndimage.sum(np.ones_like(regions), regions, idx)
            yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
            y0, y1 = ndimage.minimum(yy, regions, idx), ndimage.maximum(yy, regions, idx)
            x0, x1 = ndimage.minimum(xx, regions, idx), ndimage.maximum(xx, regions, idx)
            lut_base = np.zeros((count + 1, 3), np.float32)
            lut_finish = np.zeros(count + 1, np.int32)
            lut_cover = np.zeros(count + 1, np.float32)
            for n in range(count):
                if sizes[n] < 30:
                    continue        # specks between lines stay dark
                name = body_name if touches[n] else inner_name
                if name == "none":
                    continue
                base, finish, opacity = MATERIALS.get(name, MATERIALS["aluminium"])
                if people:
                    base = np.array(base, np.float32) * (0.75 + 0.25 * ((n * 7) % 3) / 2)
                lut_base[n + 1], lut_finish[n + 1], lut_cover[n + 1] = base, finish, opacity
            reg_y0, reg_y1 = np.concatenate([[0], y0]), np.concatenate([[1], y1])
            reg_x0, reg_x1 = np.concatenate([[0], x0]), np.concatenate([[1], x1])
            v = np.clip((yy - reg_y0[regions]) / np.maximum(1, reg_y1[regions] - reg_y0[regions]), 0, 1)
            u = np.clip((xx - reg_x0[regions]) / np.maximum(1, reg_x1[regions] - reg_x0[regions]), 0, 1)
            base = lut_base[regions]
            finish = lut_finish[regions]
            light = 1.18 - 0.42 * v
            band = 0.22 * np.exp(-((v - 0.22) / 0.07) ** 2)                       # metal: a band of light
            streak = 0.20 * np.exp(-(((u - 0.55 * v) - 0.30) / 0.05) ** 2)        # gloss: a reflection
            colour = base * light[..., None]
            colour += (np.where(finish == 1, band, 0) + np.where(finish == 2, streak, 0))[..., None] * 255
            cover = lut_cover[regions]
        up = lambda x: np.repeat(np.repeat(x, k, axis=0), k, axis=1)          # noqa: E731 - nearest, crisp
        full_c = np.zeros((h, w, 3), np.float32)
        full_a = np.zeros((h, w), np.float32)
        full_c[: sh * k, : sw * k] = up(colour)
        full_a[: sh * k, : sw * k] = up(cover)
        return full_c, full_a[..., None]

    def _marking(self, group: Group, t: float) -> float:
        """0..1 while a spoken-number card belonging to this scene is on screen."""
        for card in getattr(self, "cards", ()):
            if group.start <= card.start < group.end and card.start <= t < card.end:
                return card.progress(t)
        return 0.0

    def _points(self, group: Group, seed: int, hide: frozenset) -> np.ndarray:
        """Points on the finished drawing of a scene (unit coordinates)."""
        # The whole drawing area: long videos reach far to the sides (wide and duo layouts).
        side, span = 200, 2.5
        wide = 4.6 if self.format == "long" else span
        cols = int(side * wide / span)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, cols, side)
        scratch = cairo.ImageSurface(cairo.FORMAT_ARGB32, 4, 4)
        main, glow = cairo.Context(surface), cairo.Context(scratch)
        for ctx in (main, glow):
            ctx.translate(cols / 2, side / 2)
            ctx.scale(side / span, side / span)
        self._group_draw(main, glow, group, group.end - 1e-3, seed, 1.0, hide=hide, gp=1.0)
        stride = surface.get_stride() // 4
        alpha = np.ndarray((side, stride, 4), np.uint8, surface.get_data())[:, :cols, 3]
        ys, xs = np.nonzero(alpha > 70)
        if len(xs) == 0:
            return np.zeros((0, 2))
        pts = np.stack([xs - cols / 2, ys - side / 2], 1).astype(np.float64) / side * span
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
        m = np.ndarray((L.height, L.width, 4), np.uint8, main_surface.get_data())
        alpha = m[..., 3:4].astype(np.float32) / 255.0
        # Layers (owner review 2026-10-29): background and stage behind, the object in front.
        # The object's solid shape is cut out of both, then its own glow goes on top.
        frame = self._with_stage(self.ambience.frame(t, self._ambient(groups, gi, t)), groups, gi, t)
        body = self._body(m[..., 3])
        fill = BODY_FILL + np.array(self._accent_rgb(group), np.float32) * BODY_TINT
        frame = frame * (1 - BODY_CUT * body) + body * (BODY_CUT * fill)
        if PAINT:
            from .illustrate import SCENES
            drawing = SCENES.get(group.icons[0]) if group.icons else None
            if drawing is not None and not drawing.figure:
                gp = self._draw_args(group, t)[0]
                strength = float(np.clip((gp - PAINT_IN[0]) / (PAINT_IN[1] - PAINT_IN[0]), 0, 1))
                if gi + 1 < len(groups):   # gone before the hand-over turns the drawing into dots
                    strength *= float(np.clip((groups[gi + 1].start - TRANSITION_BEFORE - t) / 0.3, 0, 1))
                strength = strength * strength * (3 - 2 * strength)
                if strength > 0.01:
                    # 2026-10-31 (owner: the colour flickered "like a TV with a weak signal"): the
                    # areas are found on the FINISHED drawing, drawn off screen at this moment, so
                    # they never change while the pen is still working.
                    full = self._finished_alpha(group, t, gi)
                    colour, cover = self._paint(full, self._body(full), drawing)
                    cover = cover * body * strength
                    frame = frame * (1 - cover) + colour * cover
        frame = frame + np.asarray(glow_img, np.float32) * 1.35
        rgb = m[..., [2, 1, 0]].astype(np.float32)  # premultiplied
        frame = rgb + frame * (1 - alpha)
        image = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8), "RGB")

        accent = self._accent_rgb(group)

        card_on = False

        # Captions.
        ci = _active(chunks, t, lambda c: c.start, lambda c: c.end)
        if chunks:
            chunk = chunks[ci]
            fade = min(1.0, (t - chunk.start) / 0.18 + 0.2) if t >= chunk.start else 0.0
            if t > duration - 0.5:
                fade *= max(0.0, (duration - t) / 0.5)
            cap = self.captions.caption(chunk, t, fade, accent)
            image.paste(cap, (0, int(L.caption_y)), cap)

        # Chapter card at the start of each numbered chapter.
        card = None
        for mark in getattr(self, "chapters", ()):
            if mark.number and mark.start - 0.2 <= t < mark.start + CHAPTER_CARD_SECONDS:
                card = mark
        if card is not None:
            u = t - (card.start - 0.2)
            a = min(1.0, u / 0.45) * min(1.0, max(0.0, (card.start + CHAPTER_CARD_SECONDS - t) / 0.6))
            a = ease(max(0.0, min(1.0, a)))
            tile = self.captions.chapter_card(card.number, card.title)
            if a < 1.0:
                tile = tile.copy()
                tile.putalpha(tile.getchannel("A").point(lambda v: int(v * a)))
            rise = int((1 - a) * L.caption_size * 0.25)
            top = L.label_y - tile.height * 0.30 if self.format == "short" else L.height * 0.015
            image.paste(tile, (int(L.cx - tile.width / 2), int(top) + rise), tile)

        # Label tag for the active line (hidden while a chapter card shows).
        line_index = _active(group.lines, t, lambda l: l.start, lambda l: l.end)
        label = group.lines[line_index].label
        active = group.lines[line_index]
        if active.index in self.follow:
            label = ""  # the pill speaks for this line
        pill_state = self._follow_state(groups, t)
        if pill_state is not None:
            done, a = pill_state
            pill = self.captions.follow_pill(done)
            pop = 0.92 + 0.08 * ease(min(1.0, a * 1.4))
            if abs(pop - 1.0) > 1e-3:
                pill = pill.resize((max(1, int(pill.width * pop)), max(1, int(pill.height * pop))), Image.Resampling.LANCZOS)
            if a < 1.0:
                pill = pill.copy()
                pill.putalpha(pill.getchannel("A").point(lambda v: int(v * a)))
            if self.format == "short":
                # Below the captions, as in the reference endings.
                top = L.caption_y + L.caption_size * 1.35 * 2 + L.caption_size * 0.2
            else:
                top = L.height * 0.02
            image.paste(pill, (int(L.cx - pill.width / 2), int(top)), pill)
        # Spoken numbers (2026-10-18): big, in the scene's accent, in their own zone above
        # the drawing, never while a chapter card or the follow pill holds that space.
        top_busy = card is not None or (pill_state is not None and self.format == "long")
        for number in getattr(self, "cards", ()):
            if number.start <= t < number.end and not top_busy:
                u = number.progress(t)
                a = min(1.0, u / 0.12) * min(1.0, (1.0 - u) / 0.18)
                pop = 0.86 + 0.14 * ease(min(1.0, u / 0.18))
                tile = self.captions.number_card(number.text, accent, max(0.0, a), pop)
                zone_top, zone_bottom = L.card_zone
                y = (zone_top + zone_bottom) / 2 - tile.height / 2
                image.paste(tile, (int(L.cx - tile.width / 2), int(y)), tile)
                card_on = True
                break
        if label and card is None and not card_on:
            color = self.theme.rgb("gold" if (gi % 2 == 0 or self.chapters) else "cyan")
            tag = self.captions.label(label, color, min(1.0, (t - group.lines[line_index].start) / 0.3))
            image.paste(tag, (int(L.cx - tag.width / 2), int(L.label_y)), tag)

        if group.visual == "logo_end":
            a = ease((t - group.start) / 0.8)
            mark = self.end_mark.copy()
            mark.putalpha(mark.getchannel("A").point(lambda v: int(v * a)))
            image.paste(mark, (int(L.cx - mark.width / 2), int(L.cy + L.size * 0.36)), mark)
        else:
            # Shorts are cropped at the sides on tall phones; keep the mark inside.
            margin = int(L.width * (0.12 if self.format == "short" else 0.05))
            image.paste(self.mark, (L.width - self.mark.width - margin, int(L.width * 0.05)), self.mark)
        return np.asarray(image)

    @staticmethod
    def _use_illustrations(plan: dict[str, Any], lines, illustrations: dict[str, Path]):
        """Every line shows its scene's drawing (the closing logo line stays)."""
        from .illustrate import SCENES
        from .layouts import second_id

        SCENES.clear()
        owner: dict[int, str] = {}
        for scene in plan.get("scenes", []):
            if scene.get("picture_of"):
                # A pacing shot: the same picture, framed on another part of it.
                from .illustrate import shot_of
                parent = SCENES.get(str(scene["picture_of"]))
                if parent is None:
                    continue
                SCENES[scene["id"]] = shot_of(parent, int(scene.get("shot") or 1))
                SCENES[scene["id"]].stage = parent.stage
                for index in range(int(scene["first_line"]), int(scene["last_line"]) + 1):
                    owner[index] = scene["id"]
                continue
            drawing = _load_drawing(illustrations.get(scene["id"]), scene)
            if drawing is None:
                continue
            if not drawing.keep_order:  # traced pictures (figures are always pen-drawn)
                # The first picture is drawn by the pen; the rest fade in (reference style).
                drawing.entrance = "pen" if not SCENES else "fade"
            if scene.get("layout") == "duo":
                # Duo layout: the right-hand drawing is always drawn by the pen.
                drawing.companion = _load_drawing(illustrations.get(second_id(scene["id"])), scene, "label_b")
                if drawing.companion is not None:
                    drawing.companion.entrance = "pen"
            drawing.stage = str(scene.get("stage") or "")
            drawing.body = str(scene.get("body") or "")
            drawing.inner = str(scene.get("inner") or "")
            drawing.people = bool(scene.get("people"))
            if drawing.figure and str(scene.get("figure") or "").strip().lower().startswith("chart"):
                # 2026-10-27: money charts stand on the market set, not in empty black.
                drawing.stage = drawing.stage or "market"
            SCENES[scene["id"]] = drawing
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
               illustrations: dict[str, Path] | None = None, bed_variant: int | None = None) -> Path:
        lines = align_lines(plan, words, duration)
        from .number_cards import find_cards
        self.cards = find_cards(lines)
        from .chapters import chapter_marks, line_chapters
        self.chapters = chapter_marks(plan, lines) if plan.get("chapters") else []
        if self.chapters:
            # The small tag under the card names the chapter the viewer is in.
            owner = line_chapters(plan)
            chapters = plan["chapters"]
            for line in lines:
                key = owner[line.index] if line.index < len(owner) else None
                if key is not None:
                    number = str(chapters[key].get("number", "")).strip()
                    line.label = f"{number}  {chapters[key].get('title', '')}".upper() if number else ""
        spoken = [line for line in plan.get("lines", []) if str(line.get("text", "")).strip()]
        self.follow = {i for i, line in enumerate(spoken) if line.get("follow") is True}
        if illustrations:
            lines = self._use_illustrations(plan, lines, illustrations)
        groups = group_lines(lines)
        chunks = caption_chunks(lines)
        output.parent.mkdir(parents=True, exist_ok=True)
        cover = self._cover(plan, output)
        L = self.layout
        # The owner's voice, small effects timed to the visuals, and a quiet
        # synthesised atmosphere that dips a little more while he speaks.
        from .ambient import render_ambient
        from .sfx import render_sfx

        sfx_path = render_sfx(groups, duration, output.with_name(output.stem + "-sfx.wav"),
                              self._action_cues(plan, lines, groups))
        bed_path = render_ambient(duration, output.with_name(output.stem + "-bed.wav"),
                                  seed_text=str(plan.get("title", "")), variant=bed_variant)
        inputs = ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{L.width}x{L.height}",
                  "-r", str(self.fps), "-i", "-", "-i", str(narration), "-i", str(sfx_path),
                  "-i", str(bed_path)]
        audio = ("[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,asplit=2[v][key];"
                 "[2:a]aresample=48000[s];"
                 "[3:a]aresample=48000[b0];"
                 "[b0][key]sidechaincompress=threshold=0.05:ratio=2.4:attack=120:release=1200[b];"
                 "[v][s][b]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.79:level=0:attack=2:release=60[a]")
        command = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", audio,
                   "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                   "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                   "-t", f"{duration:.3f}", "-movflags", "+faststart", str(output)]
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        assert process.stdin is not None
        total = int(math.ceil(duration * self.fps))
        try:
            from .cover import COVER_FADE, COVER_HOLD
            for index in range(total):
                t = index / self.fps
                frame = self.frame(t, groups, chunks, duration)
                if cover is not None and t < COVER_HOLD + COVER_FADE:
                    # The video opens on its cover, so the first frame is the thumbnail.
                    k = 1.0 if t < COVER_HOLD else 1.0 - ease((t - COVER_HOLD) / COVER_FADE)
                    frame = (cover * k + frame.astype(np.float32) * (1 - k)).astype(np.uint8)
                process.stdin.write(frame.tobytes())
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

    def _fades(self) -> bool:
        """Illustration to illustration: the reference channel's soft fade."""
        from .illustrate import SCENES

        if self.old.visual != "illustration" or self.new.visual != "illustration":
            return False
        drawing = SCENES.get(self.new.icons[0]) if self.new.icons else None
        return drawing is not None and drawing.entrance == "fade"

    def draw(self, main, glow, t: float) -> None:
        r = self.renderer
        u = self._u(t)
        if self._fades():
            # Owner direction 2026-10-09: the old picture breaks into points of
            # light that travel and land as the next picture, changing colour on
            # the way to the next picture's accent; the new picture forms as they land.
            out = 1 - ease(min(1.0, u / 0.35))
            if out > 0.01:
                r._group_draw(main, glow, self.old, self.old.end - 1e-3, self.index - 1, out,
                              zoom=1.0 + 0.03 * ease(u))
            arrive = ease(min(1.0, max(0.0, (u - 0.45) / 0.45)))
            if arrive > 0.01:
                r._group_draw(main, glow, self.new, max(t, self.new.start), self.index, arrive,
                              zoom=1.03 - 0.03 * arrive)
            self._particles(main, glow, u, accents=(self._accent(self.old), self._accent(self.new)))
            return
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

    def _accent(self, group: Group):
        from .illustrate import SCENES

        drawing = SCENES.get(group.icons[0]) if group.icons else None
        name = getattr(drawing, "accent", "gold") if drawing is not None else "gold"
        return self.renderer.colors.get(f"accent_{name}", self.renderer.colors["gold"])

    def _particles(self, main, glow, u: float, accents=None) -> None:
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
        if accents:
            a, b = accents
            gold = tuple(x + (y - x) * travel for x, y in zip(a, b))
            white = tuple(0.55 * w + 0.45 * g for w, g in zip(white, gold))
        for ctx, radius, color, a in ((main, 2.0 / unit, white, 0.9 * alpha), (glow, 5.0 / unit, gold, alpha)):
            ctx.save()
            ctx.set_source_rgba(*color, a)
            for x, y in pos:
                ctx.new_sub_path()
                ctx.arc(float(x), float(y), radius, 0, math.tau)
            ctx.fill()
            ctx.restore()


def _load_drawing(path, scene: dict, label_key: str = "label"):
    """A scene picture as pen strokes: an exact figure (math layer) or a traced drawing."""
    from .illustrate import ACCENTS, load_figure, vectorize
    from .scene_labels import attach_label

    if path is None or not Path(path).exists():
        return None
    figure = load_figure(Path(path))
    if figure is not None:
        # Exact figures are always drawn by the pen, in gold: the construction is the explanation.
        return figure
    drawing = vectorize(Path(path))
    drawing.accent = str(scene.get("accent") or "gold")
    # 2026-10-20: a word on the glowing part (a jar's label), typeset sharp, never traced.
    attach_label(drawing, str(scene.get(label_key) or ""), ACCENTS.get(drawing.accent, ACCENTS["gold"]))
    return drawing
