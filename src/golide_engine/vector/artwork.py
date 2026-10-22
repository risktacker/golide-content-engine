"""Show the real illustration, revealed along the pen (owner direction 2026-10-22).

"All these broken blocks in a long form video... let the illustrations be more
real and of quality." The image model draws good line art; the old renderer threw
that picture away and redrew it from a 1-pixel skeleton of every bright area.
A thin line survives that; anything shaded, glowing or filled (a car body, a
window, a halo) turned into a stick figure with spurs.

Now the picture on screen IS the illustration:

* ``line_layer`` lifts the line work out of the image with a morphological
  top-hat: thin lines stay, broad glow halos, haze and filled panels drop out.
  Even a blurry, over-glowing picture comes back as crisp line art.
* ``time_map`` gives every inked pixel the moment the pen reaches it, from the
  traced strokes (which now only decide the ORDER things appear in). A pixel the
  trace missed still appears, with the stroke nearest to it, so a weak trace can
  never delete part of a picture.
* ``frame_surfaces`` paints the line layer up to the pen's progress, in the
  theme's line colour with the accent part in the scene's accent colour, plus
  a glow pass.

The same approach as professional whiteboard-animation tools: the art is the
artist's, the animation only decides when each part shows.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

ART_MAX_SIDE = 1280        # art resolution kept for the screen (long videos fill ~1000 px)
TOPHAT_SHARE = 0.015       # top-hat window as a share of the shorter side (15 px at 1024)
GRAIN_SIGMA = 1.0          # softening before the top-hat: blurry, glowing pictures came back speckled
LINE_FLOOR = 0.16          # share of the strongest line below which a pixel is haze, not line
ALL_ACCENT_TINT = 0.35     # all-gold pictures: lines tinted this much toward the accent colour
REVEAL_SOFT = 0.012        # share of the pen's work over which a pixel fades in
GOLD_HUE = 0.28            # warm hue threshold, same as the tracer
ALL_ACCENT = 0.6           # above this share of gold ink the whole picture was drawn gold
HAZE_LEVEL = 25.0          # brightness above the background that counts as "lit"
EDGE_FADE = 0.06           # share of each side over which the art fades out at the picture border


@dataclass
class Artwork:
    alpha: np.ndarray          # (h, w) float32, line strength 0..1
    accent: np.ndarray         # (h, w) bool, pixels of the accent part
    scale: float               # art pixels per drawing (tracer) pixel
    haze: float = 0.0          # share of lit pixels that are glow or blur, not line
    all_accent: bool = False   # the model drew everything gold
    tmap: np.ndarray | None = None  # (h, w) float32, pen progress (0..1) when each pixel appears
    _cache: dict = field(default_factory=dict, repr=False)

    @property
    def shape(self) -> tuple[int, int]:
        return self.alpha.shape


def _luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb.max(axis=2).astype(np.float32)


def line_layer(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, bool]:
    """(alpha, accent mask, haze, all_accent) of an RGB line illustration on a dark ground."""
    from scipy import ndimage

    lum = _luminance(rgb)
    h, w = lum.shape
    k = max(9, int(round(min(h, w) * TOPHAT_SHARE)) | 1)
    soft = ndimage.gaussian_filter(lum, GRAIN_SIGMA)
    tophat = soft - ndimage.grey_opening(soft, size=(k, k))
    hi = float(np.percentile(tophat, 99.7))
    if hi <= 1.0:
        return np.zeros_like(lum), np.zeros(lum.shape, bool), 0.0, False
    lo = max(6.0, LINE_FLOOR * hi)
    alpha = np.clip((tophat - lo) / max(1.0, 0.8 * hi - lo), 0.0, 1.0).astype(np.float32)
    # Dust and speckles: drop tiny isolated bits.
    ink = alpha > 0.25
    labels, count = ndimage.label(ink)
    if count:
        sizes = ndimage.sum(ink, labels, range(1, count + 1))
        small = np.isin(labels, np.nonzero(sizes < 10)[0] + 1)
        alpha[small] = 0.0
    r, b = rgb[..., 0].astype(np.float32), rgb[..., 2].astype(np.float32)
    goldness = (r - b) / (lum + 1.0)
    accent = (alpha > 0.15) & (goldness > GOLD_HUE)
    accent = ndimage.binary_dilation(accent, iterations=1) & (alpha > 0.05)
    inked = alpha > 0.15
    share = float(accent[inked].mean()) if inked.any() else 0.0
    all_accent = share > ALL_ACCENT
    if all_accent:
        accent = np.zeros_like(accent)  # one colour for everything; the redraw check reports it
    background = float(np.median(lum))
    lit = lum > background + HAZE_LEVEL
    haze = float(((alpha < 0.1) & lit).sum() / max(1, lit.sum()))
    return alpha, accent, haze, all_accent


def load_artwork(image, drawing_width: int) -> Artwork:
    """The art layer of a PIL image, at screen resolution, tied to the tracer's coordinates."""
    from PIL import Image

    image = image.convert("RGB")
    scale = min(1.0, ART_MAX_SIDE / max(image.size))
    if scale < 1.0:
        image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    rgb = np.asarray(image, np.float32)
    alpha, accent, haze, all_accent = line_layer(rgb)
    return Artwork(edge_fade(alpha), accent, image.width / max(1, drawing_width), haze, all_accent)


def edge_fade(alpha: np.ndarray, share: float = EDGE_FADE) -> np.ndarray:
    """Fade the art out towards the picture border (2026-10-22): when the image model cuts an
    object with the border, the cut ends in a soft fade instead of a hard chop on screen."""
    h, w = alpha.shape
    def ramp(n: int) -> np.ndarray:
        band = max(1, int(round(n * share)))
        r = np.ones(n, np.float32)
        t = np.linspace(0.0, 1.0, band, dtype=np.float32)
        r[:band] = t * t * (3 - 2 * t)
        r[n - band:] = np.minimum(r[n - band:], r[:band][::-1])
        return r
    return (alpha * ramp(h)[:, None] * ramp(w)[None, :]).astype(np.float32)


def time_map(art: Artwork, strokes) -> np.ndarray:
    """When the pen reaches each pixel: the drawing order of the nearest traced stroke."""
    from scipy import ndimage

    h, w = art.shape
    seeds = np.zeros((h, w), bool)
    value = np.zeros((h, w), np.float32)
    total = sum(s.length for s in strokes) or 1.0
    walked = 0.0
    for stroke in strokes:
        pts = np.asarray(stroke.points, np.float64) * art.scale
        if len(pts) < 2:
            continue
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        steps = max(2, int(cum[-1]) + 1)
        along = np.linspace(0.0, cum[-1], steps)
        xs = np.interp(along, cum, pts[:, 0])
        ys = np.interp(along, cum, pts[:, 1])
        ix = np.clip(np.round(xs).astype(int), 0, w - 1)
        iy = np.clip(np.round(ys).astype(int), 0, h - 1)
        frac = (walked + along / art.scale) / total
        seeds[iy, ix] = True
        value[iy, ix] = frac
        walked += stroke.length
    if not seeds.any():
        return np.zeros((h, w), np.float32)
    _, (ny, nx) = ndimage.distance_transform_edt(~seeds, return_indices=True)
    return np.clip(value[ny, nx], 0.0, 1.0).astype(np.float32)


def _pack(rgb: np.ndarray, a: np.ndarray) -> bytearray:
    """Premultiplied BGRA bytes for cairo."""
    h, w = a.shape
    out = np.empty((h, w, 4), np.uint8)
    out[..., 0] = np.clip(rgb[..., 2] * a * 255, 0, 255)
    out[..., 1] = np.clip(rgb[..., 1] * a * 255, 0, 255)
    out[..., 2] = np.clip(rgb[..., 0] * a * 255, 0, 255)
    out[..., 3] = np.clip(a * 255, 0, 255)
    return bytearray(out.tobytes())


def frame_surfaces(art: Artwork, done: float, line_rgb: tuple, accent_rgb: tuple,
                   glow_line: float = 0.22, glow_accent: float = 0.6):
    """(main surface, glow surface) of the art revealed up to ``done`` (0..1 of the pen's work)."""
    import cairo

    done = float(min(1.0, max(0.0, done)))
    finished = done >= 1.0
    key = ("full", line_rgb, accent_rgb)
    if finished and key in art._cache:
        return art._cache[key][:2]
    h, w = art.shape
    colours = art._cache.get(("rgb", line_rgb, accent_rgb))
    if colours is None:
        colours = np.empty((h, w, 3), np.float32)
        base = np.asarray(line_rgb, np.float32)
        if art.all_accent:
            # The model drew everything gold: keep the scene's meaning colour as a tint
            # over the whole drawing instead of losing it.
            base = base * (1 - ALL_ACCENT_TINT) + np.asarray(accent_rgb, np.float32) * ALL_ACCENT_TINT
        colours[:] = base
        colours[art.accent] = accent_rgb
        weight = np.where(art.accent, glow_accent, glow_accent * 0.6 if art.all_accent else glow_line)
        weight = weight.astype(np.float32)
        art._cache[("rgb", line_rgb, accent_rgb)] = colours = (colours, weight)
    rgb, weight = colours
    if finished or art.tmap is None:
        a = art.alpha
    else:
        a = art.alpha * np.clip((done + REVEAL_SOFT - art.tmap) / REVEAL_SOFT, 0.0, 1.0)
    main_bytes, glow_bytes = _pack(rgb, a), _pack(rgb, a * weight)
    main = cairo.ImageSurface.create_for_data(main_bytes, cairo.FORMAT_ARGB32, w, h, w * 4)
    glow = cairo.ImageSurface.create_for_data(glow_bytes, cairo.FORMAT_ARGB32, w, h, w * 4)
    if finished:
        art._cache[key] = (main, glow, main_bytes, glow_bytes)  # bytes kept alive with the surfaces
    else:
        art._cache["last"] = (main_bytes, glow_bytes)
    return main, glow
