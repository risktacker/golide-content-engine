"""The set every drawing stands in (owner direction 2026-10-27).

"Our illustrations... feel naked because the video has no frames and boldness... the
rest is black, almost showing nothing happening in background." The pen still draws the
object; behind it, each scene now gets a set that frames and contains it, drawn in code
(no image cost), chosen by the storyboard per scene:

* grid      a floor grid running to a glowing horizon (cars, robots, anything on the ground)
* pedestal  glowing rings on the floor under a soft beam (a product reveal)
* studio    a curved studio backdrop with two lights on stands aimed at the object
* wall      a blueprint wall behind the object (how it works, specs)
* orbit     rings and a halo around the object (AI, data, networks: nothing to stand on)
* horizon   the glowing curve of a planet below (space, launches, scale)
* space     a nebula band, a distant sun and a bending space grid (gravity, physics, cosmos)
* factory   roof trusses, hanging lamps and a floor grid (industry, machines, tanks)
* market    a faint chart wall and a ticker strip on the floor (prices, stocks, the economy)
* storefront a shop front with windows and an awning (selling, retail, small business)
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

KINDS = ("grid", "pedestal", "studio", "wall", "orbit", "horizon", "space", "factory", "market", "storefront",
         "none")
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
        self._cache: dict[tuple, np.ndarray] = {}

    # ------------------------------------------------------------- public
    def image(self, kind: str, accent_rgb: tuple, footprint: tuple | None = None) -> np.ndarray | None:
        """The set for one scene. footprint: (left, right, bottom) of the object in px; the
        floor starts where the object stands and the light pool and shadow sit under it."""
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
            self.floor = floor
            try:
                art = getattr(self, "_" + kind)(col)
                art = self._planes(art, col, footprint, floor_set=kind not in ("orbit", "space", "horizon"),
                                   near_fade=kind != "pedestal")
            finally:
                self.floor = self.base_floor
            self._cache[key] = (art * self.mask * STRENGTH).astype(np.float32)
        return self._cache[key]

    def _planes(self, art: np.ndarray, col: np.ndarray, footprint, floor_set: bool,
                near_fade: bool = True) -> np.ndarray:
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
        # Right under the horizon the floor lines bunch up into a bright band that fights the
        # object's base: they fade in over the first stretch of floor instead.
        near = 1.0 if not near_fade else (0.2 + 0.8 * np.clip((yy - fy) / max(h * 0.09, (h - fy) * 0.4), 0, 1) ** 1.3)[..., None]
        out = wall * (1 - soft) + art * soft * near
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
            out = out * (1 - 0.85 * shadow)[..., None] - (shadow * 16)[..., None]
        return np.clip(out, -16, None)

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
        return (self._lines(paint) * fade * (yy >= fy))[..., None] * col * strength

    def _horizon_glow(self, col, k=0.35, spread=0.11) -> np.ndarray:
        yy, xx = self._grid_xy()
        g = np.exp(-((yy - self.floor) / (self.h * spread)) ** 2) * np.exp(-((xx - self.cx) / (self.w * 0.62)) ** 2)
        return g[..., None] * col * k

    # ------------------------------------------------------------- sets
    def _grid(self, col):
        return self._floor_grid(col) + self._horizon_glow(col, 0.5)

    def _pedestal(self, col):
        h, w, fy, cx = self.h, self.w, self.floor, self.cx
        rmax = min(w * 0.30, h * 0.45)

        def paint(c):
            c.set_line_width(max(1.5, h / 600))
            for r in (rmax, rmax * 0.77, rmax * 0.54):
                c.save()
                c.translate(cx, fy)
                c.scale(1, 0.18)
                c.arc(0, 0, r, 0, 2 * math.pi)
                c.restore()
                c.stroke()
        yy, xx = self._grid_xy()
        pool = np.exp(-(((xx - cx) / (rmax * 0.9)) ** 2 + ((yy - fy) / (h * 0.045)) ** 2))
        width = w * 0.06 + np.clip(fy - yy, 0, None) * 0.35
        beam = np.exp(-((xx - cx) / width) ** 2) * (yy < fy) * np.clip((yy - self.top * 0.2) / max(1, fy), 0, 1) * 0.55
        return self._lines(paint)[..., None] * col * 0.45 + (pool * 0.45 + beam * 0.35)[..., None] * col

    def _studio(self, col):
        h, w, fy, cx = self.h, self.w, self.floor, self.cx

        def paint(c):
            c.set_line_width(max(1.0, h / 900))
            for i in range(5):
                c.save()
                c.translate(cx, fy)
                c.scale(1, 0.55)
                c.arc(0, 0, w * (0.44 + i * 0.031), math.pi * 1.02, math.pi * 1.98)
                c.restore()
                c.stroke()
        stands = self._stands()
        yy, xx = self._grid_xy()
        sweep = np.clip((yy - h * 0.15) / max(1, fy - h * 0.15), 0, 1) ** 1.4 * np.exp(-((xx - cx) / (w * 0.48)) ** 2)
        rim = np.exp(-((yy - fy) / (h * 0.01)) ** 2) * np.exp(-((xx - cx) / (w * 0.44)) ** 2)
        return (self._lines(paint) * 0.22 + sweep * 0.22 + rim * 0.35)[..., None] * col + stands

    def _stands(self) -> np.ndarray:
        """Two studio lights on stands at the sides, aimed at the centre (grey stands, cool heads)."""
        h, w, fy = self.h, self.w, self.floor
        if self.format == "short":
            return np.zeros((h, w, 3), np.float32)
        tall = (fy - self.top) * 0.75

        def paint(c):
            c.set_line_width(max(1.5, h / 540))
            for sx, d in ((w * 0.045, 1), (w * 0.955, -1)):
                c.move_to(sx, fy)
                c.line_to(sx, fy - tall)
                c.move_to(sx - h * 0.035, fy)
                c.line_to(sx, fy - h * 0.05)
                c.line_to(sx + h * 0.035, fy)
                c.save()
                c.translate(sx, fy - tall - h * 0.02)
                c.rotate(d * 0.5)
                c.rectangle(-h * 0.04, -h * 0.03, h * 0.08, h * 0.06)
                c.restore()
            c.stroke()
        return self._lines(paint)[..., None] * np.array((150, 160, 175), np.float32) * 0.35

    def _wall(self, col):
        h, w = self.h, self.w
        step = h / 27

        def paint(c):
            c.set_line_width(max(1.0, h / 1080))
            x = 0.0
            while x < w:
                c.move_to(x, 0)
                c.line_to(x, h)
                x += step
            y = 0.0
            while y < h:
                c.move_to(0, y)
                c.line_to(w, y)
                y += step
            c.stroke()
        yy, xx = self._grid_xy()
        m = np.exp(-((xx - self.cx) / (w * 0.42)) ** 2) * np.exp(-((yy - (self.top + self.floor) / 2) / (h * 0.45)) ** 2)
        return (self._lines(paint) * m * 0.22)[..., None] * col + self._horizon_glow(col, 0.18)

    def _orbit(self, col):
        h, w = self.h, self.w
        cy = (self.top + self.floor) / 2
        r0 = min(w, h) * 0.30

        def paint(c):
            c.set_line_width(max(1.0, h / 800))
            for r in (r0, r0 * 1.33, r0 * 1.7):
                c.new_sub_path()
                c.arc(self.cx, cy, r, 0, 2 * math.pi)
            c.stroke()
            for ang in (0.6, 2.4, 4.1):
                c.new_sub_path()
                c.arc(self.cx + r0 * 1.33 * math.cos(ang), cy + r0 * 1.33 * math.sin(ang), h / 200, 0, 2 * math.pi)
                c.fill()
        yy, xx = self._grid_xy()
        halo = np.exp(-(((xx - self.cx) ** 2 + (yy - cy) ** 2) / (r0 * 1.3) ** 2))
        return (self._lines(paint) * 0.35 + halo * 0.12)[..., None] * col

    def _horizon(self, col):
        h, w = self.h, self.w
        R = w * 1.0
        pcy = self.floor + R - h * 0.04
        yy, xx = self._grid_xy()
        d = np.sqrt((xx - self.cx) ** 2 + (yy - pcy) ** 2)
        atm = np.clip(1 - np.abs(d - R) / (h * 0.08), 0, 1) ** 2 * (d > R)
        edge = np.exp(-((d - R) / (h * 0.003)) ** 2)
        return (atm * 0.45 + edge * 0.9)[..., None] * col

    def _space(self, col):
        h, w = self.h, self.w
        yy, xx = self._grid_xy()
        rng = np.random.default_rng(7)
        noise = np.zeros((h // 16 + 1, w // 16 + 1), np.float32)
        for sc in (1, 2, 4):
            small = rng.random((h // (16 * sc) + 2, w // (16 * sc) + 2)).astype(np.float32)
            noise += np.kron(small, np.ones((sc, sc), np.float32))[:noise.shape[0], :noise.shape[1]] / sc
        from PIL import Image, ImageFilter
        n = np.asarray(Image.fromarray((noise / noise.max() * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
                       .filter(ImageFilter.GaussianBlur(h / 40)), np.float32) / 255
        band = np.exp(-((yy - self.top - 0.12 * (xx - self.cx)) / (h * 0.16)) ** 2)
        neb = np.clip(n - 0.4, 0, 1) * band
        sun = np.exp(-(((xx - w * 0.84) ** 2 + (yy - h * 0.16) ** 2) / (h * 0.09) ** 2))
        violet = np.array(COOL["violet"], np.float32)
        return neb[..., None] * (violet * 0.6 + col * 0.4) * 0.9 + sun[..., None] * np.array(WARM, np.float32) * 0.5 \
            + self._floor_grid(col, 0.6)

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
        for lx in (w * 0.18, w * 0.5, w * 0.82):
            width = w * 0.012 + np.clip(yy - roof, 0, None) * 0.28
            lamps += np.exp(-((xx - lx) / width) ** 2) * ((yy > roof) & (yy < fy)) * np.clip(1 - (yy - roof) / max(1, fy - roof), 0, 1)
            lamps += np.exp(-(((xx - lx) / (w * 0.012)) ** 2 + ((yy - roof - h * 0.065) / (h * 0.008)) ** 2)) * 4
        air = np.clip((yy - roof) / max(1, fy - roof), 0, 1) ** 2 * 0.18 * (yy < fy)
        grey = np.array((150, 160, 175), np.float32)
        return self._lines(trusses)[..., None] * grey * 0.18 + lamps[..., None] * np.array(WARM, np.float32) * 0.22 \
            + air[..., None] * col + self._floor_grid(col, 0.85) + self._horizon_glow(col, 0.25)

    def _market(self, col):
        """A chart wall behind (faint candles and a trend) and a ticker strip on the floor."""
        h, w, fy = self.h, self.w, self.floor
        rng = np.random.default_rng(4)
        closes = np.cumsum(rng.normal(0.4, 1.0, 34))
        closes = (closes - closes.min()) / max(1e-6, np.ptp(closes))
        top = max(h * 0.08, self.top)
        span = (fy - top) * 0.75

        def candles(c):
            c.set_line_width(max(1.0, h / 900))
            step = w / 36
            prev = closes[0]
            for i, cl in enumerate(closes):
                x = step * (i + 1)
                y0, y1 = fy - h * 0.06 - prev * span, fy - h * 0.06 - cl * span
                c.move_to(x, min(y0, y1) - h * 0.012)
                c.line_to(x, max(y0, y1) + h * 0.012)
                c.rectangle(x - step * 0.22, min(y0, y1), step * 0.44, max(2.0, abs(y1 - y0)))
                prev = cl
            c.stroke()

        def ticker(c):
            c.set_line_width(max(1.0, h / 900))
            c.rectangle(w * 0.04, fy + h * 0.015, w * 0.92, h * 0.035)
            x = w * 0.06
            while x < w * 0.94:
                c.move_to(x, fy + h * 0.032)
                c.line_to(x + w * 0.03, fy + h * 0.032)
                x += w * 0.06
            c.stroke()
        yy, xx = self._grid_xy()
        m = np.exp(-((xx - self.cx) / (w * 0.5)) ** 2)
        return (self._lines(candles) * m * 0.30)[..., None] * col + self._lines(ticker)[..., None] * col * 0.35 \
            + self._horizon_glow(col, 0.3)

    def _storefront(self, col):
        """A shop front behind the object: windows, a door, an awning and a pavement line."""
        h, w, fy = self.h, self.w, self.floor
        top = max(h * 0.1, self.top - h * 0.05)
        left, right = w * 0.08, w * 0.92

        def front(c):
            c.set_line_width(max(1.0, h / 800))
            c.rectangle(left, top, right - left, fy - top)                 # the building face
            aw = top + (fy - top) * 0.18
            n = 10
            for i in range(n):                                             # scalloped awning
                x0 = left + (right - left) * i / n
                x1 = left + (right - left) * (i + 1) / n
                c.move_to(x0, aw)
                c.curve_to(x0, aw + h * 0.03, x1, aw + h * 0.03, x1, aw)
            c.move_to(left, aw)
            c.line_to(right, aw)
            win_top = aw + h * 0.06
            for x0, x1 in ((left + w * 0.03, w * 0.40), (w * 0.60, right - w * 0.03)):
                c.rectangle(x0, win_top, x1 - x0, fy - win_top - h * 0.06)
            c.rectangle(w * 0.44, win_top, w * 0.12, fy - win_top)          # the door
            c.move_to(0, fy)
            c.line_to(w, fy)
            c.stroke()
        yy, xx = self._grid_xy()
        glow = np.exp(-((xx - self.cx) / (w * 0.4)) ** 2) * ((yy > top) & (yy < fy)) * 0.12
        return self._lines(front)[..., None] * col * 0.30 + glow[..., None] * col + self._horizon_glow(col, 0.25)
