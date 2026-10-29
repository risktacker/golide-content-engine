"""The set every drawing stands in (owner direction 2026-10-27).

"Our illustrations... feel naked because the video has no frames and boldness... the
rest is black, almost showing nothing happening in background." The pen still draws the
object; behind it, each scene now gets a set that frames and contains it, drawn in code
(no image cost), chosen by the storyboard per scene:

* grid      the floor grid running to a glowing horizon (the base of every set)
* pedestal  the grid plus glowing rings lying on the floor under the object
* factory   the grid plus lamps hanging at the sides
* market    the grid plus faint candle bands at the far left and right
* space     the grid plus a planet curve far behind the horizon and a faint nebula above
* none      the plain sky (exact maths figures keep their lesson grid)

Colour rule (owner review of fills, 2026-10-27): sets are drawn in a cool colour (teal,
blue, violet, ivory); warm colours (gold, copper, rose) never fill a set, they only light
small parts (lamps, a sun). Nothing strong sits behind the captions or number cards: the
set fades to a sixth there. Each set is built once per colour and cached; the renderer adds
it under the drawing and cross-fades it at scene changes.

Layers (owner review 2026-10-29: "the objects and base stage + background is colliding...
stage below, background behind, then the objects in front... even the color is mattering"):

* background  everything above the floor line is the back wall: dimmed and greyed, so it
              recedes and never competes with the object
* stage       the floor starts exactly where the object stands (its footprint, measured from
              the drawing), lit a little brighter than the wall, with a clean horizon line, a
              pool of light and a contact shadow under the object
* object      the renderer cuts the drawing's solid shape out of both (vector.render), so no
              set line ever runs through it
* colour      the set never takes the object's own colour: when they are close, the set moves
              to the cool colour farthest from it
"""

from __future__ import annotations

import math

import numpy as np

# 2026-10-29 (owner: "the main goal here is to never collide objects with background and
# stage... grid and glow fits better"): every set is the grid floor with its glow and the
# object's shadow; the others only add an extra at the sides, above or under the base.
# Orbit, horizon, wall, studio and storefront drew lines behind or around the object and are
# gone; old plans that still name them get the nearest set that cannot collide.
KINDS = ("grid", "pedestal", "factory", "market", "space", "none")
ALIASES = {"orbit": "grid", "wall": "grid", "studio": "pedestal", "storefront": "grid", "horizon": "space"}
COLLISION = 7.0          # mean set light (0-255) allowed inside the object's box before falling back to grid
COOL = {"teal": (110, 220, 200), "blue": (115, 165, 250), "violet": (168, 140, 242), "ivory": (236, 230, 210)}
WARM = (233, 196, 106)
UNDER_TEXT = 0.15         # share of the set kept behind captions and number cards
STRENGTH = 1.0
HOLD_OUT = 0.55          # share of the set held back around the object (its solid shape is cut out in render)
WALL = 0.65              # brightness of the back wall relative to the stage floor
WALL_GREY = 0.35         # how far the back wall is pulled toward grey
FLOOR_LIFT = 0.075       # the floor plane's own light, so stage and wall read as two planes
BEHIND_CLEAR = 0.75      # share of the back wall removed in the object's own box
SAME_COLOUR = 95.0       # RGB distance under which the set would blend with the object


def separate(col: np.ndarray, object_rgb: tuple | None) -> np.ndarray:
    """The set colour, moved to the cool colour farthest from the object when the two are close."""
    if object_rgb is None:
        return col
    obj = np.array(object_rgb, np.float32)
    if float(np.linalg.norm(col - obj)) >= SAME_COLOUR:
        return col
    far = max((np.array(c, np.float32) for k, c in COOL.items() if k != "ivory"),
              key=lambda c: float(np.linalg.norm(c - obj)))
    return far


def set_colour(accent_rgb: tuple) -> np.ndarray:
    """The scene's accent if it is cool, otherwise teal (warm colours never fill a set)."""
    r, g, b = (float(c) for c in accent_rgb)
    if r > b + 25 and r > g - 10:      # gold, copper, rose
        return np.array(COOL["teal"], np.float32)
    return np.array((r, g, b), np.float32)


class Stages:
    def __init__(self, layout, format_name: str):
        from .ambience import text_safe
        from .illustrate import REGIONS

        self.layout = layout
        self.format = format_name
        w, h = layout.width, layout.height
        self.w, self.h = w, h
        _, top, _, bottom = REGIONS[format_name]
        caption_top = layout.caption_y - layout.caption_size * 2.2
        self.floor = min(layout.cy + bottom * layout.size / 2, caption_top - h * 0.02)
        if format_name == "short":
            # A short's picture sits small and high in its area: the floor comes up to meet it.
            self.floor = layout.cy + layout.size * 0.16
        self.top = layout.cy + top * layout.size / 2
        self.cx = layout.cx
        self.mask = (UNDER_TEXT + (1 - UNDER_TEXT) * text_safe(layout, 0.06))[..., None].astype(np.float32)
        # 2026-10-27 (owner: candles showed through a coin): the set stays behind the object.
        # Line art is see-through, so the set is held back where the drawing sits.
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        ocy = (self.top + self.floor) / 2
        rx = layout.size * (0.55 if format_name == "short" else 0.62)
        ry = (self.floor - self.top) * 0.42
        hold = 1 - HOLD_OUT * np.exp(-(((xx - layout.cx) / rx) ** 2 + ((yy - ocy) / ry) ** 2) ** 1.6)
        self.mask = (self.mask * hold[..., None]).astype(np.float32)
        self.base_floor = self.floor
        self.caption_top = caption_top
        self.mid, self.span, self.fallbacks = self.cx, w * 0.3, 0
        self._cache: dict[tuple, np.ndarray] = {}

    # ------------------------------------------------------------- public
    def image(self, kind: str, accent_rgb: tuple, footprint: tuple | None = None) -> np.ndarray | None:
        """The set for one scene. footprint: (left, right, bottom) of the object in px; the
        floor starts where the object stands and the light pool and shadow sit under it."""
        kind = ALIASES.get(kind, kind)
        kind = kind if kind in KINDS else "grid"
        if kind == "none":
            return None
        col = separate(set_colour(accent_rgb), accent_rgb)
        floor = self.base_floor
        if footprint is not None:
            low = self.top + (self.base_floor - self.top) * 0.35
            floor = float(np.clip(footprint[2] + self.h * 0.004, low, self.caption_top - self.h * 0.02))
            floor = round(floor / 6) * 6
            top = footprint[3] if len(footprint) > 3 else self.top
            footprint = (round(footprint[0] / 24) * 24, round(footprint[1] / 24) * 24, floor, round(top / 24) * 24)
        key = (kind, tuple(int(c) for c in col), floor, footprint)
        if key not in self._cache:
            if len(self._cache) > 48:
                self._cache.pop(next(iter(self._cache)))
            self.floor, self.mid = floor, (self.cx if footprint is None else (footprint[0] + footprint[1]) / 2)
            self.span = self.w * 0.3 if footprint is None else max(self.w * 0.12, (footprint[1] - footprint[0]) / 2)
            try:
                art = self._planes(getattr(self, "_" + kind)(col), col, footprint, floor_set=True)
                if kind != "grid" and self.collides(art, footprint):
                    self.fallbacks += 1
                    art = self._planes(self._grid(col), col, footprint, floor_set=True)
            finally:
                self.floor, self.mid = self.base_floor, self.cx
            self._cache[key] = (art * self.mask * STRENGTH).astype(np.float32)
        return self._cache[key]

    def _planes(self, art: np.ndarray, col: np.ndarray, footprint, floor_set: bool = True) -> np.ndarray:
        """Background behind, stage below: dim and grey the wall, light the floor, draw the horizon."""
        h, w, fy = self.h, self.w, self.floor
        yy, xx = self._grid_xy()
        if not floor_set:
            grey = art.mean(axis=2, keepdims=True)
            return (art * (1 - WALL_GREY) + grey * WALL_GREY) * 0.8
        soft = np.clip((yy - fy) / (h * 0.006) + 0.5, 0, 1)[..., None]       # 0 on the wall, 1 on the floor
        grey = art.mean(axis=2, keepdims=True)
        wall_k = WALL
        wall = (art * (1 - WALL_GREY) + grey * WALL_GREY) * wall_k
        if footprint is not None:
            # The wall frames the object from the sides; right behind it the wall is cleared, so a
            # drawing that brings its own setting (people at a counter) never sits on a second one.
            x0, x1, _, top = footprint
            pad = w * 0.08
            inside = (np.clip((xx - (x0 - pad)) / pad, 0, 1) * np.clip(((x1 + pad) - xx) / pad, 0, 1)
                      * np.clip((yy - (top - pad)) / pad, 0, 1)
                      * np.clip((fy - h * 0.05 - yy) / (h * 0.06), 0, 1))   # the horizon glow stays whole
            wall = wall * (1 - BEHIND_CLEAR * inside)[..., None]
        out = wall * (1 - soft) + art * soft
        depth = max(1.0, h - fy)
        sides = np.exp(-((xx - self.cx) / (w * 0.55)) ** 2)
        lift = np.clip(1 - (yy - fy) / depth, 0, 1) ** 0.7 * (yy >= fy) * (0.55 + 0.45 * sides)
        line = np.exp(-((yy - fy) / (h * 0.0022)) ** 2) * (0.25 + 0.75 * sides)
        out = out + (lift * FLOOR_LIFT + line * 0.42)[..., None] * col
        if footprint is not None:
            x0, x1 = footprint[0], footprint[1]
            mid, half = (x0 + x1) / 2, max(w * 0.04, (x1 - x0) / 2)
            pool = np.exp(-(((xx - mid) / (half * 1.25)) ** 2 + ((yy - fy) / (h * 0.05)) ** 2)) * (yy >= fy)
            shadow = np.exp(-(((xx - mid) / (half * 0.95)) ** 2 + ((yy - fy - h * 0.006) / (h * 0.012)) ** 2))
            out = out + (pool * 0.16)[..., None] * col
            # Negative values darken the ambience under the object's base (the frame is clipped later).
            out = out * (1 - 0.95 * shadow)[..., None] - (shadow * 20)[..., None]
        return np.clip(out, -20, None)

    # ------------------------------------------------------------- helpers
    def _grid_xy(self):
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        return yy, xx

    def _lines(self, paint) -> np.ndarray:
        """Draw lines with cairo (white on black) and return a 0..1 coverage map with a soft glow."""
        import cairo
        from PIL import Image, ImageFilter

        s = cairo.ImageSurface(cairo.FORMAT_A8, self.w, self.h)
        c = cairo.Context(s)
        c.set_source_rgba(1, 1, 1, 1)
        paint(c)
        stride = s.get_stride()
        a = np.ndarray((self.h, stride), np.uint8, s.get_data())[:, :self.w].astype(np.float32) / 255
        blur = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(max(2, self.h / 360))), np.float32) / 255
        return a + blur * 0.8

    def _floor_grid(self, col, strength=0.95) -> np.ndarray:
        h, w, fy, cx = self.h, self.w, self.floor, self.cx
        depth = h - fy

        def paint(c):
            c.set_line_width(max(1.0, h / 900))
            for i in range(-30, 31):
                c.move_to(cx + i * w * 0.011, fy)
                c.line_to(cx + i * w * 0.12, h + depth)
            for j in range(1, 14):
                y = fy + depth * (j / 13) ** 2
                c.move_to(0, y)
                c.line_to(w, y)
            c.stroke()
        yy, xx = self._grid_xy()
        fade = np.clip((yy - fy) / max(1, depth * 0.5), 0, 1) * 0.65 + 0.35
        # Right under the horizon the lines bunch up into a bright band that fights the object's
        # base: they fade in over the first stretch of floor instead.
        near = 0.2 + 0.8 * np.clip((yy - fy) / max(h * 0.09, depth * 0.4), 0, 1) ** 1.3
        return (self._lines(paint) * fade * near * (yy >= fy))[..., None] * col * strength

    def _horizon_glow(self, col, k=0.35, spread=0.11) -> np.ndarray:
        yy, xx = self._grid_xy()
        g = np.exp(-((yy - self.floor) / (self.h * spread)) ** 2) * np.exp(-((xx - self.cx) / (self.w * 0.62)) ** 2)
        return g[..., None] * col * k

    # ------------------------------------------------------------- sets
    def _grid(self, col, strength: float = 1.0):
        return self._floor_grid(col, 0.95 * strength) + self._horizon_glow(col, 0.5)

    def collides(self, art: np.ndarray, footprint) -> bool:
        """True when the set puts light inside the object's own box (above its floor)."""
        if footprint is None:
            return False
        x0, x1, fy, top = (int(v) for v in footprint)
        box = art[max(0, top):max(1, fy - int(self.h * 0.05)), max(0, x0):max(1, x1)]
        return box.size > 0 and float(box.mean()) > COLLISION

    def _pedestal(self, col):
        """The grid floor plus glowing rings lying on it under the object."""
        h, fy, mid, span = self.h, self.floor, self.mid, self.span

        def paint(c):
            c.set_line_width(max(1.5, h / 600))
            for k in (1.15, 0.9, 0.65):
                c.save()
                c.translate(mid, fy + h * 0.012)
                c.scale(1, 0.16)
                c.arc(0, 0, span * k, 0, 2 * math.pi)
                c.restore()
                c.stroke()
        yy, xx = self._grid_xy()
        rings = self._lines(paint) * (yy >= fy - h * 0.004)        # only the half lying on the floor shows
        return self._grid(col) * 0.8 + rings[..., None] * col * 0.85

    def _factory(self, col):
        h, w, fy = self.h, self.w, self.floor
        roof = max(h * 0.10, self.top - h * 0.12)

        def trusses(c):
            c.set_line_width(max(1.0, h / 1000))
            c.move_to(0, roof)
            c.line_to(w, roof)
            c.move_to(0, roof + h * 0.05)
            c.line_to(w, roof + h * 0.05)
            step = w / 16
            x = 0.0
            while x < w + step:
                c.move_to(x, roof)
                c.line_to(x + step / 2, roof + h * 0.05)
                c.line_to(x + step, roof)
                x += step
            c.stroke()
        yy, xx = self._grid_xy()
        lamps = np.zeros((h, w), np.float32)
        for lx in (w * 0.09, w * 0.91):          # at the sides, never over the object
            width = w * 0.012 + np.clip(yy - roof, 0, None) * 0.28
            lamps += np.exp(-((xx - lx) / width) ** 2) * ((yy > roof) & (yy < fy)) * np.clip(1 - (yy - roof) / max(1, fy - roof), 0, 1)
            lamps += np.exp(-(((xx - lx) / (w * 0.012)) ** 2 + ((yy - roof - h * 0.065) / (h * 0.008)) ** 2)) * 4
        air = np.clip((yy - roof) / max(1, fy - roof), 0, 1) ** 2 * 0.18 * (yy < fy)
        grey = np.array((150, 160, 175), np.float32)
        return self._lines(trusses)[..., None] * grey * 0.18 + lamps[..., None] * np.array(WARM, np.float32) * 0.22 \
            + air[..., None] * col + self._floor_grid(col, 0.85) + self._horizon_glow(col, 0.25)

    def _market(self, col):
        """The grid floor plus faint candle bands standing at the far left and right."""
        h, w, fy = self.h, self.w, self.floor
        rng = np.random.default_rng(4)
        tall = min(h * 0.22, (fy - self.top) * 0.55)

        def candles(c):
            c.set_line_width(max(1.0, h / 900))
            step = w * 0.018
            for x_start, x_end in ((w * 0.02, w * 0.17), (w * 0.83, w * 0.98)):
                x, level = x_start, 0.5
                while x < x_end:
                    level = float(np.clip(level + rng.normal(0.04, 0.12), 0.1, 0.95))
                    body = tall * rng.uniform(0.08, 0.2)
                    y = fy - h * 0.02 - level * tall
                    c.move_to(x, y - h * 0.012)
                    c.line_to(x, y + body + h * 0.012)
                    c.rectangle(x - step * 0.25, y, step * 0.5, body)
                    x += step
            c.stroke()
        return self._grid(col) + self._lines(candles)[..., None] * col * 0.32

    def _space(self, col):
        """The grid floor, a planet curve far behind the horizon and a faint nebula above."""
        h, w, fy = self.h, self.w, self.floor
        yy, xx = self._grid_xy()
        R = w * 1.6
        pcy = fy + R - h * 0.05                                    # the planet's top just clears the horizon
        d = np.sqrt((xx - self.cx) ** 2 + (yy - pcy) ** 2)
        limb = (np.exp(-((d - R) / (h * 0.003)) ** 2) * 0.6 + np.clip(1 - np.abs(d - R) / (h * 0.05), 0, 1) ** 2
                * (d > R) * 0.25) * (yy < fy)
        limb = limb * np.clip((np.abs(xx - self.mid) - self.span * 1.1) / (w * 0.06), 0, 1)   # only beside the object
        sky = np.exp(-((yy - h * 0.12) / (h * 0.08)) ** 2) * (0.6 + 0.4 * np.sin(xx / w * 7.0)) * 0.10
        violet = np.array(COOL["violet"], np.float32)
        return self._grid(col, 0.85) + limb[..., None] * col + sky[..., None] * (violet * 0.6 + col * 0.4)
