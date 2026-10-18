"""The background behind every frame: night sky that answers the scene on screen.

Owner direction 2026-10-18 ("make the whole scene not boring... mirror the block
which is currently on display"), kept quiet on purpose so the drawing, captions
and number cards always win:

1. SCENE LIGHT: a soft glow in the active scene's accent colour sits behind the
   drawing (about a tenth of full strength) and cross-fades at each scene change.
2. TINTED DUST: some of the drifting stars take that colour, and a few motes of
   light drift slowly in toward the drawing.
3. DEPTH: the star layers move apart at different rates as the camera pushes in
   (parallax), so a push-in feels three-dimensional.
4. LESSON GRID: under exact figures (maths and physics) a faint graph-paper grid,
   like a blueprint. Story and news scenes never get it.

Hard rules: nothing coloured behind the captions or the number cards (TEXT-SAFE
mask), the light always sits behind the line art, and the static grain of the
base keeps dark gradients from banding after YouTube compression.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter

LIGHT_STRENGTH = 0.10        # peak share of the accent colour added behind the drawing
DUST_TINTED = 0.28           # share of the mid and near stars that take the accent colour
MOTES = {"short": 22, "long": 34}
MOTE_PERIOD = (9.0, 15.0)    # seconds for one mote to drift in toward the drawing
GRID_MINOR, GRID_MAJOR = 5.5, 10.0   # lift (0-255) of graph-paper lines
GRID_TINT = np.array((0.78, 0.90, 1.0), np.float32)  # cool blueprint white
PARALLAX = (0.25, 0.55, 1.0)  # share of the camera push each star layer follows (far -> near)
DOT_GRID_LIFT = 20.0         # grey dots this much above the background (0-255)


@dataclass(frozen=True)
class AmbientState:
    """What the background shows at one moment."""
    accent: tuple = (233, 196, 106)   # 0-255 RGB of the scene on screen
    lesson: float = 0.0               # 0..1: graph-paper grid strength (exact figures only)
    push: float = 0.0                 # camera push-in (0 = none, 0.06 = the usual scene push)
    light: float = 1.0                # 0..1: overall strength of the scene light


# ------------------------------------------------------------------ base sky

def background(layout, theme) -> np.ndarray:
    """Charcoal vignette with a very faint blue-violet haze and dot grid (no stars here)."""
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
    # Owner direction 2026-10-09: a faint grey dot grid, almost unnoticed, so the
    # black is never plain. Dimmer toward the edges with the vignette.
    step = max(18, round(min(w, h) / 27))
    gy, gx = np.mgrid[step // 2:h:step, step // 2:w:step]
    soft = np.clip(1.15 - dist[gy, gx], 0.35, 1.0)
    for dy, dx, weight in ((0, 0, 1.0), (0, 1, 1.0), (1, 0, 1.0), (1, 1, 1.0), (-1, 0, 0.35), (0, -1, 0.35),
                           (2, 0, 0.35), (0, 2, 0.35)):
        yy2, xx2 = np.clip(gy + dy, 0, h - 1), np.clip(gx + dx, 0, w - 1)
        image[yy2, xx2] += (DOT_GRID_LIFT * weight * soft)[..., None] * np.array((1.0, 1.0, 1.06), np.float32)
    # Fine static grain hides 8-bit banding in the dark vignette (and in the scene light).
    image = image + np.random.default_rng(7).uniform(-1.6, 1.6, image.shape).astype(np.float32)
    return np.clip(image, 0, 255)


def text_safe(layout, ramp_share: float = 0.02) -> np.ndarray:
    """1 where colour may sit, 0 over the caption band and the number-card zone (H x W).
    A wider ramp gives a softer edge (used under the broad scene light)."""
    w, h = layout.width, layout.height
    y = np.arange(h, dtype=np.float32)
    top_end = layout.card_zone[1]
    ramp = h * ramp_share
    caption_top = layout.caption_y - layout.caption_size * 2.2
    smooth = lambda u: (lambda c: c * c * (3 - 2 * c))(np.clip(u, 0, 1))  # noqa: E731
    mask = smooth((y - top_end) / ramp) * smooth((caption_top - y) / ramp)
    return np.repeat(mask[:, None], w, axis=1)


def drawing_centre_y(layout, format_name: str) -> float:
    """Vertical centre (px) of the area the illustrations occupy."""
    from .illustrate import REGIONS

    _, top, _, bottom = REGIONS[format_name]
    return layout.cy + (top + bottom) / 2 * layout.size / 2


def _splat(frame: np.ndarray, x: np.ndarray, y: np.ndarray, rgb: np.ndarray, halo: float = 0.0) -> None:
    """Bilinear point splat (sub-pixel motion without shimmer), optional soft halo."""
    h, w = frame.shape[:2]
    keep = (x >= 1) & (y >= 1) & (x < w - 2) & (y < h - 2)
    x, y, rgb = x[keep], y[keep], rgb[keep]
    x0, y0 = x.astype(np.int64), y.astype(np.int64)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    for dx, dy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        np.add.at(frame, (y0 + dy, x0 + dx), rgb * wgt.astype(np.float32))
    if halo:
        ring = rgb * halo
        for dx, dy in ((-1, 0), (2, 0), (0, -1), (0, 2), (-1, -1), (2, 2), (-1, 2), (2, -1)):
            np.add.at(frame, (y0 + dy, x0 + dx), ring * (0.55 if abs(dx - 0.5) + abs(dy - 0.5) > 2 else 1.0))


def _unit(accent) -> np.ndarray:
    rgb = np.array(accent, np.float32)
    return rgb / max(1.0, float(rgb.max()))


# ------------------------------------------------------------------ stars

class StarField:
    """Three depths of small stars that twinkle and drift very slowly.

    Some mid and near stars take the scene's accent colour (never over text),
    and each depth follows the camera push by a different amount (parallax).
    """

    LAYERS = (  # (stars per megapixel, brightness range, drift px/s, twinkle depth)
        (220, (30, 70), 2.0, 0.35),
        (70, (80, 150), 4.5, 0.45),
        (12, (170, 235), 8.0, 0.30),
    )

    def __init__(self, width: int, height: int, seed: int = 11, centre: tuple | None = None):
        self.w, self.h = width, height
        self.centre = centre or (width / 2, height / 2)
        rng = np.random.default_rng(seed)
        mp = width * height / 1e6
        self.layers = []
        for index, (density, (lo, hi), drift, depth) in enumerate(self.LAYERS):
            n = int(density * mp)
            self.layers.append({
                "x": rng.uniform(0, width, n), "y": rng.uniform(0, height, n),
                "b": rng.uniform(lo, hi, n), "f": rng.uniform(0.15, 0.8, n),
                "ph": rng.uniform(0, math.tau, n), "drift": drift, "depth": depth,
                "tint": rng.choice([0, 1, 2], n, p=[0.75, 0.15, 0.10]),
                "accent": (rng.random(n) < DUST_TINTED) if index else np.zeros(n, bool),
                "parallax": PARALLAX[index],
            })
        self.tints = np.array([[1.0, 1.0, 1.0], [0.85, 0.92, 1.0], [1.0, 0.92, 0.78]], np.float32)

    def add(self, frame: np.ndarray, t: float, state: AmbientState | None = None,
            safe: np.ndarray | None = None) -> np.ndarray:
        state = state or AmbientState()
        accent = _unit(state.accent)
        cx, cy = self.centre
        for layer in self.layers:
            x = (layer["x"] + layer["drift"] * 0.35 * t) % (self.w - 1)
            y = (layer["y"] - layer["drift"] * t) % (self.h - 1)
            grow = 1.0 + state.push * layer["parallax"]
            x, y = cx + (x - cx) * grow, cy + (y - cy) * grow
            b = layer["b"] * (1 - layer["depth"] * (0.5 + 0.5 * np.sin(math.tau * layer["f"] * t + layer["ph"])))
            tint = self.tints[layer["tint"]]
            if layer["accent"].any():
                mix = layer["accent"].astype(np.float32) * 0.85
                if safe is not None:
                    yi = np.clip(y.astype(np.int64), 0, self.h - 1)
                    xi = np.clip(x.astype(np.int64), 0, self.w - 1)
                    mix = mix * safe[yi, xi]
                tint = tint * (1 - mix[:, None]) + accent[None, :] * mix[:, None]
            rgb = (b[:, None] * tint).astype(np.float32)
            _splat(frame, x, y, rgb, halo=0.18 if layer is self.layers[-1] else 0.0)
        return frame


class Motes:
    """A few points of light in the scene's colour drifting slowly in toward the drawing."""

    def __init__(self, layout, count: int, seed: int = 5):
        rng = np.random.default_rng(seed)
        self.cx, self.cy = layout.cx, layout.cy
        self.rx, self.ry = layout.width * 0.50, layout.height * 0.46
        self.period = rng.uniform(*MOTE_PERIOD, count)
        self.phase = rng.random(count)
        self.angle = rng.uniform(0, math.tau, count)
        self.bright = rng.uniform(55, 95, count)
        self.near = rng.uniform(0.38, 0.55, count)   # how close to the drawing a mote gets

    def add(self, frame: np.ndarray, t: float, state: AmbientState, safe: np.ndarray) -> np.ndarray:
        cycle = t / self.period + self.phase
        life = cycle % 1.0
        angle = self.angle + np.floor(cycle) * 2.39996   # a new path every cycle (golden angle)
        r = 1.0 - (1.0 - self.near) * life
        x = self.cx + np.cos(angle) * self.rx * r
        y = self.cy + np.sin(angle) * self.ry * r
        h, w = safe.shape
        yi, xi = np.clip(y.astype(np.int64), 0, h - 1), np.clip(x.astype(np.int64), 0, w - 1)
        b = self.bright * np.sin(math.pi * life) ** 1.5 * safe[yi, xi] * state.light
        rgb = (b[:, None] * _unit(state.accent)[None, :]).astype(np.float32)
        _splat(frame, x, y, rgb, halo=0.30)
        return frame


# ------------------------------------------------------------------ light and grid

class SceneLight:
    """A soft radial light behind the drawing; the caller gives it the colour."""

    def __init__(self, layout, format_name: str, safe: np.ndarray):
        w, h = layout.width, layout.height
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        # Flatter than the drawing area so it has faded out before the text zones
        # (no visible edge where the text-safe mask begins).
        sx, sy = (w * 0.40, h * 0.14) if format_name == "short" else (w * 0.27, h * 0.17)
        cy = drawing_centre_y(layout, format_name)
        falloff = np.exp(-(((xx - layout.cx) / sx) ** 2 + ((yy - cy) / sy) ** 2))
        self.mask = (falloff * safe).astype(np.float32)

    def colour(self, state: AmbientState) -> np.ndarray:
        """RGB added where ``mask`` is 1."""
        return np.array(state.accent, np.float32) * (LIGHT_STRENGTH * state.light)


class LessonGrid:
    """Faint graph paper under exact figures, fading out toward the edges of the drawing area."""

    def __init__(self, layout, format_name: str, safe: np.ndarray):
        w, h = layout.width, layout.height
        step = max(16, round(min(w, h) / 22))
        lift = np.zeros((h, w), np.float32)
        x0, y0 = int(layout.cx) % step, int(layout.cy) % step
        for i, x in enumerate(range(x0, w, step)):
            lift[:, x] = np.maximum(lift[:, x], GRID_MAJOR if (x - int(layout.cx)) // step % 5 == 0 else GRID_MINOR)
        for y in range(y0, h, step):
            lift[y, :] = np.maximum(lift[y, :], GRID_MAJOR if (y - int(layout.cy)) // step % 5 == 0 else GRID_MINOR)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        sx, sy = (w * 0.44, h * 0.24) if format_name == "short" else (w * 0.36, h * 0.36)
        cy = drawing_centre_y(layout, format_name)
        fade = np.clip(1.25 - np.sqrt(((xx - layout.cx) / sx) ** 2 + ((yy - cy) / sy) ** 2), 0, 1)
        self.lift = (lift * fade * safe).astype(np.float32)

    def colour(self, state: AmbientState) -> np.ndarray:
        """RGB added where ``lift`` is 1 (graph-paper lines carry a lift of a few levels)."""
        return (GRID_TINT * 0.75 + _unit(state.accent) * 0.25) * state.lesson


# ------------------------------------------------------------------ composer

class Ambience:
    """The whole background for one format: base sky + light + grid + stars + motes.

    The light and the grid only change at scene changes, so the lit sky is cached
    and rebuilt only when the state changes (one matrix product for both layers).
    """

    def __init__(self, layout, theme, format_name: str):
        self.base = background(layout, theme)
        self.safe = text_safe(layout)
        self.light = SceneLight(layout, format_name, text_safe(layout, 0.12))
        self.grid = LessonGrid(layout, format_name, text_safe(layout, 0.08))
        self.stars = StarField(layout.width, layout.height, centre=(layout.cx, layout.cy))
        self.motes = Motes(layout, MOTES.get(format_name, 22))
        h, w = self.safe.shape
        self._layers = np.stack([self.light.mask, self.grid.lift], -1).reshape(h * w, 2)
        self._key: tuple | None = None
        self._sky = self.base

    def sky(self, state: AmbientState) -> np.ndarray:
        """Base sky with the scene light and lesson grid (cached per state)."""
        key = (tuple(round(float(c), 1) for c in state.accent), round(state.lesson, 3), round(state.light, 3))
        if key != self._key:
            coef = np.stack([self.light.colour(state), self.grid.colour(state)]).astype(np.float32)
            self._sky = self.base + (self._layers @ coef).reshape(self.base.shape)
            self._key = key
        return self._sky

    def frame(self, t: float, state: AmbientState) -> np.ndarray:
        frame = self.sky(state).copy()
        self.stars.add(frame, t, state, self.safe)
        self.motes.add(frame, t, state, self.safe)
        return frame


def crossfade(t: float, boundary: float, before: float, after: float) -> float:
    """0 -> 1 eased weight of the new scene across the hand-over window around ``boundary``."""
    u = min(1.0, max(0.0, (t - (boundary - before)) / (before + after)))
    return u * u * (3 - 2 * u)


def mix(a: AmbientState, b: AmbientState, w: float) -> AmbientState:
    lerp = lambda p, q: p + (q - p) * w  # noqa: E731
    return AmbientState(tuple(lerp(p, q) for p, q in zip(a.accent, b.accent)), lerp(a.lesson, b.lesson),
                        lerp(a.push, b.push), lerp(a.light, b.light))
