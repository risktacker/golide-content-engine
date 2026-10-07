"""Animated line illustrations (GOLIDE Black, owner direction 2026-10-05).

The reference videos are not icons moving around; each idea is one drawn
scene that builds while the narrator speaks and then turns into the next.
This module provides that:

* ``scene_plan_instructions`` / ``VISUAL_PLAN_SCHEMA``: the text model groups
  the spoken lines into a few scenes and describes one composed illustration
  per scene (the words are never changed).
* ``illustration_prompt``: the locked image prompt (thin white line art on
  pure black, exactly one gold element, no text).
* ``vectorize``: turns the generated picture into ordered pen strokes.
* ``illustration`` primitive: draws those strokes on with a travelling pen
  light, completing over the scene, then lets the gold part breathe.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------
# Planning (text model)
# --------------------------------------------------------------------------

# Owner review 2026-10-07 (reference channel): many visual ideas per video,
# a new picture every line or two.
SCENE_COUNTS = {"short": (7, 10), "long": (12, 18)}

# Accent colours, taken from the reference channel's palette. The picture is
# always generated with the accent part in gold (so tracing can find it); the
# renderer draws that part in the scene's accent colour.
ACCENTS = {
    "gold": (233, 196, 106),
    "rose": (240, 138, 128),
    "teal": (127, 224, 210),
    "ivory": (246, 238, 222),
    "copper": (217, 140, 85),
}

# Action sounds a scene may ask for (see vector.sfx).
SCENE_SOUNDS = ("none", "bling", "chime", "phone_ring", "notify", "door_open", "door_shut",
                "car", "blips", "coin", "typing", "clock", "camera")

VISUAL_PLAN_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "cover": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "text": {"type": "string"},
                "gold": {"type": "string"},
                "scene": {"type": "integer"},
                "thumbnail_moment": {"type": "string"},
            },
            "required": ["text", "gold", "scene", "thumbnail_moment"],
        },
        "scenes": {
            "type": "array",
            "minItems": 2,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "first_line": {"type": "integer"},
                    "last_line": {"type": "integer"},
                    "drawing": {"type": "string"},
                    "gold_element": {"type": "string"},
                    "accent": {"type": "string", "enum": list(ACCENTS)},
                    "sound": {"type": "string", "enum": list(SCENE_SOUNDS)},
                    "sound_word": {"type": "string"},
                },
                "required": ["first_line", "last_line", "drawing", "gold_element", "accent", "sound", "sound_word"],
            },
        },
    },
    "required": ["cover", "scenes"],
}


def scene_plan_instructions(format_name: str) -> str:
    low, high = SCENE_COUNTS.get(format_name, SCENE_COUNTS["short"])
    return f"""\
You are the storyboard artist for a narrated explainer video in the style of
animated line-illustration channels: on a black screen, one hand-drawn white
line illustration builds while the narrator speaks, then fades into the
next. Show many different visual ideas: a new picture for every new thought. You receive the spoken lines, numbered from 0. Do not change any words.

Group consecutive lines into {low} to {high} scenes. Every line belongs to
exactly one scene, in order, with no gaps or overlaps (scene 1 starts at line
0, each next scene starts right after the previous one ends, the last scene
ends at the last line). Start a new scene only when the idea changes.

For each scene write "drawing": one composed illustration that SHOWS the idea
of those lines as a small visual story or metaphor, the way an illustrator
would, not a list of objects or icons. Name the concrete things, how they are
arranged, and what is happening between them (for example: "a tall server
rack in cross-section, heat rising from each shelf as wavy lines into a small
room, a technician's silhouette beside it holding a clipboard"). Real objects,
people and places drawn simply. If people appear they are Black. One clear
focal point. No text, labels, numbers, logos or screens with readable content.

VARIETY (owner direction 2026-10-07: the visuals must feel vast, never repeated):
every scene uses a different kind of shot from the one before, mixing across
the video: a wide scene with people in a place, a close-up of one object, a
visual metaphor (a key, a bridge, a scale, a maze, a seed growing), a before
and after side by side, a network or constellation of connected dots, a
symbol drawn large (an eye, a clock, a lock), an overhead or cross-section
view. Never draw the same main object in two scenes in a row, and never use
the same composition twice in a short.

"gold_element": the single part of the drawing that should glow because it
carries the meaning of the scene (for example: "the heat lines").

"accent": the colour that glowing part is shown in, chosen by meaning:
gold (value, money, success, the key idea), rose (risk, warning, emotion, a
problem), teal (technology, AI, data, calm), ivory (soft light, neutral, hope),
copper (warm everyday things, wood, home, people at work). Vary it: never the
same accent more than two scenes in a row.

"sound": one short sound for the main action you drew, ONLY when the lines
describe that action: bling (something lights up or a key idea lands), chime
(a gentle reveal), phone_ring (a call), notify (a message or alert), door_open,
door_shut (blocked, closed, rejected), car (driving, travel, moving fast),
blips (AI, a computer or robot working, scanning, searching), coin (paying,
buying, money), typing (writing, prompting), clock (time, waiting, deadlines),
camera (a photo, being watched). Otherwise "none". At most every other scene has
a sound; most explainer scenes need none. "sound_word": the exact word from the
scene's lines when the sound should play (for example "blocked"), or "" for none.

COVER (the picture people see before they press play; owner direction 2026-10-07):
- "text": a 3 to 7 word hook for the cover, the most curious way to say what the
  video is about. Not the title word for word. Plain words, no hashtags, no emoji.
  Example: "Meta's AI shops for you. Amazon said no."
- "gold": the 1 to 3 words of that hook that carry the punch, copied exactly.
- "scene": the number (1 = first scene) of the scene whose drawing best stands for
  the whole video.
- "thumbnail_moment": one vivid sentence for the YouTube thumbnail artist: the
  decisive, slightly playful moment of the story, not the topic (for example "a
  robot hand reaching for a shopping cart just as a store shutter slams down on
  it"). One hero subject, a clear action, a little irony or surprise.

If the lines are divided into chapters (marked "== CHAPTER ... =="), a scene
never runs across a chapter mark: every chapter starts with a new scene.
"""


def validate_scenes(scenes: list[dict], line_count: int, breaks: set[int] | frozenset[int] = frozenset()) -> list[dict]:
    """Make the model's grouping cover every line exactly once, in order.

    ``breaks`` are line indices where a chapter starts: a scene never runs
    across one, so every chapter opens on a fresh drawing.
    """
    ordered = sorted(scenes, key=lambda s: int(s["first_line"]))
    fixed: list[dict] = []
    cursor = 0
    for scene in ordered:
        last = min(int(scene["last_line"]), line_count - 1)
        if last < cursor:
            continue
        fixed.append({**scene, "first_line": cursor, "last_line": last})
        cursor = last + 1
        if cursor >= line_count:
            break
    if not fixed:
        raise ValueError("visual plan produced no usable scenes")
    if cursor < line_count:
        fixed[-1]["last_line"] = line_count - 1
    split: list[dict] = []
    for scene in fixed:
        first, last = scene["first_line"], scene["last_line"]
        cuts = sorted(i for i in breaks if first < i <= last)
        for start, end in zip([first, *cuts], [c - 1 for c in cuts] + [last]):
            split.append({**scene, "first_line": start, "last_line": end})
    fixed = split
    for index, scene in enumerate(fixed):
        scene["id"] = f"scene-{index + 1:02d}"
    return fixed


def illustration_prompt(drawing: str, gold: str, format_name: str) -> str:
    area = ("Portrait composition: one compact scene in the centre with wide empty black "
            "margins on the left and right; nothing touches the edges, and any ground line is "
            "short, not edge to edge." if format_name == "short" else
            "Landscape composition: the scene centred with empty black margins on every side; "
            "nothing touches the edges, and any ground line stays inside the margins.")
    return (
        "Minimal elegant line illustration: thin, clean white lines on a pure flat black "
        "background, like a confident hand-drawn ink sketch made with a fine glowing pen. "
        "Main shapes in a steady line; a few small inner details (a seam, a button, a window, "
        "a fold, a texture mark) in finer, shorter lines so the drawing has depth without "
        "clutter. Give the scene a simple ground line or soft horizon so objects sit somewhere, "
        "one clear focal point, and generous empty space around it. Every line closed and "
        "deliberate; no sketchy double lines, no stray dots. Outlines only: no fills, no solid "
        "shapes, no shading, no gradients, no glow halos, no colour except one part. Draw the "
        "following as one composed scene: "
        f"{drawing.strip()} Draw only this part in warm gold lines: {gold.strip()}. "
        "No text, letters, numbers, labels, logos, watermarks or user-interface elements anywhere. "
        f"{area}"
    )


# --------------------------------------------------------------------------
# Vectorising a line drawing into ordered pen strokes
# --------------------------------------------------------------------------

@dataclass
class Stroke:
    points: np.ndarray  # (n, 2) in image pixels
    gold: bool
    width: float  # in image pixels

    @property
    def length(self) -> float:
        return float(np.sum(np.linalg.norm(np.diff(self.points, axis=0), axis=1)))


@dataclass
class Drawing:
    strokes: list[Stroke]
    width: int
    height: int
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1 of the ink
    # Closed shapes, filled softly like the reference (0..1 per pixel): one
    # mask for the white parts and one for the accent part.
    fill: np.ndarray | None = None
    accent_fill: np.ndarray | None = None
    accent: str = "gold"
    entrance: str = "pen"  # "pen": drawn line by line; "fade": appears drawn, accent lights up

    @property
    def total(self) -> float:
        return sum(s.length for s in self.strokes) or 1.0


_NEIGHBOURS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _trace(skeleton: np.ndarray) -> list[list[tuple[int, int]]]:
    """Walk a 1-px skeleton into polylines (split at junctions)."""
    ys, xs = np.nonzero(skeleton)
    pixels = set(zip(ys.tolist(), xs.tolist()))

    def nbrs(p):
        y, x = p
        return [(y + dy, x + dx) for dy, dx in _NEIGHBOURS if (y + dy, x + dx) in pixels]

    degree = {p: len(nbrs(p)) for p in pixels}
    visited_edges: set[tuple] = set()
    paths: list[list[tuple[int, int]]] = []

    def edge(a, b):
        return (a, b) if a < b else (b, a)

    def walk(start, nxt):
        path = [start, nxt]
        visited_edges.add(edge(start, nxt))
        prev, cur = start, nxt
        while degree[cur] == 2:
            options = [q for q in nbrs(cur) if q != prev and edge(cur, q) not in visited_edges]
            if not options:
                break
            prev, cur = cur, options[0]
            visited_edges.add(edge(prev, cur))
            path.append(cur)
        return path

    nodes = [p for p in pixels if degree[p] != 2]
    for node in sorted(nodes):
        for q in nbrs(node):
            if edge(node, q) not in visited_edges:
                paths.append(walk(node, q))
    # Closed loops have no endpoints or junctions.
    for p in sorted(pixels):
        for q in nbrs(p):
            if edge(p, q) not in visited_edges:
                paths.append(walk(p, q))
    return paths


def _simplify(points: np.ndarray, tolerance: float) -> np.ndarray:
    """Ramer-Douglas-Peucker."""
    if len(points) < 3:
        return points
    start, end = points[0], points[-1]
    line = end - start
    norm = np.hypot(*line)
    if norm == 0:
        dists = np.hypot(*(points - start).T)
    else:
        rel = points - start
        dists = np.abs(line[0] * rel[:, 1] - line[1] * rel[:, 0]) / norm
    index = int(np.argmax(dists))
    if dists[index] > tolerance:
        left = _simplify(points[: index + 1], tolerance)
        right = _simplify(points[index:], tolerance)
        return np.vstack([left[:-1], right])
    return np.vstack([start, end])


def _smooth(points: np.ndarray, passes: int = 2) -> np.ndarray:
    for _ in range(passes):
        if len(points) < 3:
            return points
        inner = (points[:-2] + 2 * points[1:-1] + points[2:]) / 4
        points = np.vstack([points[0], inner, points[-1]])
    return points


def _order(strokes: list[Stroke]) -> list[Stroke]:
    """Pen order: start with the longest line, then always the nearest next
    stroke (reversing it if its far end is closer), gold strokes last."""
    def chain(items: list[Stroke]) -> list[Stroke]:
        if not items:
            return []
        remaining = sorted(items, key=lambda s: -s.length)
        out = [remaining.pop(0)]
        while remaining:
            tip = out[-1].points[-1]
            best, best_d, flip = 0, float("inf"), False
            for i, s in enumerate(remaining):
                d0 = float(np.hypot(*(s.points[0] - tip)))
                d1 = float(np.hypot(*(s.points[-1] - tip)))
                if d0 < best_d:
                    best, best_d, flip = i, d0, False
                if d1 < best_d:
                    best, best_d, flip = i, d1, True
            nxt = remaining.pop(best)
            if flip:
                nxt = Stroke(nxt.points[::-1].copy(), nxt.gold, nxt.width)
            out.append(nxt)
        return out

    return chain([s for s in strokes if not s.gold]) + chain([s for s in strokes if s.gold])


def vectorize(image_path: Path, max_side: int = 900) -> Drawing:
    from PIL import Image
    from scipy import ndimage
    from skimage.morphology import skeletonize

    image = Image.open(image_path).convert("RGB")
    scale = min(1.0, max_side / max(image.size))
    if scale < 1.0:
        image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    rgb = np.asarray(image, np.float32)
    lum = rgb.max(axis=2)
    # Lines are bright on black: threshold relative to the background and the
    # brightest ink, so both crisp white and softer grey line art trace.
    background = float(np.median(lum))
    ink = float(np.percentile(lum, 99.5))
    threshold = background + max(30.0, 0.35 * (ink - background))
    mask = lum > threshold
    mask = ndimage.binary_closing(mask, iterations=1)
    labels, count = ndimage.label(mask)
    if count:
        sizes = ndimage.sum(mask, labels, range(1, count + 1))
        keep = np.isin(labels, np.nonzero(sizes >= 12)[0] + 1)
        mask = mask & keep
    distance = ndimage.distance_transform_edt(mask)
    skeleton = skeletonize(mask)

    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    goldness = (r - b) / (lum + 1)  # warm hue: red/green high, blue low

    strokes: list[Stroke] = []
    for path in _trace(skeleton):
        if len(path) < 6:
            continue
        pts = np.array([(x, y) for y, x in path], np.float64)
        ys, xs = np.array([p[0] for p in path]), np.array([p[1] for p in path])
        gold = float(np.median(goldness[ys, xs])) > 0.28
        width = float(np.clip(np.median(distance[ys, xs]) * 2.0, 1.2, 6.0))
        pts = _simplify(_smooth(pts, 3), 0.6)
        stroke = Stroke(pts, gold, width)
        if stroke.length >= 6:
            strokes.append(stroke)
    if not strokes:
        raise ValueError(f"no line art found in {image_path}")
    allpts = np.vstack([s.points for s in strokes])
    x0, y0 = allpts.min(axis=0)
    x1, y1 = allpts.max(axis=0)
    fill, accent_fill = _fills(mask, goldness)
    return Drawing(_order(strokes), image.width, image.height, (float(x0), float(y0), float(x1), float(y1)),
                   fill, accent_fill)


def _fills(mask: np.ndarray, goldness: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Enclosed areas of the line art (a body, a door, a screen), not the background.

    Very small pockets and very large areas (a room outline) stay empty so the
    fill reads as shading, never as a solid block.
    """
    from scipy import ndimage

    h, w = mask.shape
    holes, count = ndimage.label(~mask)
    fill = np.zeros((h, w), np.float32)
    accent = np.zeros((h, w), np.float32)
    if not count:
        return fill, accent
    border = set(np.unique(np.concatenate([holes[0], holes[-1], holes[:, 0], holes[:, -1]])))
    sizes = ndimage.sum(np.ones_like(holes), holes, range(1, count + 1))
    area = float(h * w)
    ring_gold = goldness > 0.28
    for label in range(1, count + 1):
        if label in border:
            continue
        share = sizes[label - 1] / area
        if share < 0.0006 or share > 0.12:
            continue
        region = holes == label
        ring = ndimage.binary_dilation(region, iterations=3) & mask
        warm = ring_gold[ring].mean() if ring.any() else 0.0
        (accent if warm > 0.5 else fill)[region] = 1.0
    return fill, accent


# --------------------------------------------------------------------------
# Drawing on screen
# --------------------------------------------------------------------------

# Filled by the renderer before frames are drawn: scene id -> Drawing.
SCENES: dict[str, Drawing] = {}

# Region the illustration may occupy, in the renderer's unit coordinates.
# Where an illustration may sit, in drawing units around the layout centre.
# Owner review 2026-10-07: drawings ran off the sides on tall phones (Shorts
# are cropped left and right) and collided with the tag above them.
# short: x within the middle 68% of the width, y from 17% to 58% of the height,
#        below the tag/pill zone and above the captions.
# long:  y from 19% to 76% of the height, below the chapter card.
REGIONS = {"short": (-0.92, -1.10, 0.92, 0.87), "long": (-2.0, -0.77, 2.0, 1.12)}


def fit(drawing: Drawing, region: tuple[float, float, float, float]):
    x0, y0, x1, y1 = drawing.bbox
    rx0, ry0, rx1, ry1 = region
    w, h = max(1.0, x1 - x0), max(1.0, y1 - y0)
    s = min((rx1 - rx0) / w, (ry1 - ry0) / h)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ox, oy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
    return s, cx, cy, ox, oy


def draw_illustration(d, drawing: Drawing, region, reveal: float, breathe: float = 0.0, zoom: float = 1.0,
                      linear: bool = False) -> None:
    from .primitives import pen_light

    s, cx, cy, ox, oy = fit(drawing, region)
    s *= (1.0 + 0.025 * breathe) * zoom  # slow push-in over the scene
    accent = "accent_" + drawing.accent if ("accent_" + drawing.accent) in d.colors else "gold"
    _paint_fills(d, drawing, accent, s, cx, cy, ox, oy, reveal)

    def tx(points):
        return [((x - cx) * s + ox, (y - cy) * s + oy) for x, y in points]

    # Ease the pen: it starts gently, travels, and settles, instead of a flat speed.
    r = max(0.0, min(1.0, reveal))
    target = drawing.total * (r if linear else (r * r * (3 - 2 * r) * 0.35 + r * 0.65))
    lengths = sorted(st.length for st in drawing.strokes) or [1.0]
    long_cut = lengths[int(len(lengths) * 0.6)]
    short_cut = lengths[int(len(lengths) * 0.25)]
    walked = 0.0
    tip = None
    pulse = 0.5 + 0.5 * math.sin(d.t * 1.8)
    for stroke in drawing.strokes:
        if walked >= target:
            break
        length = stroke.length or 1.0
        frac = min(1.0, (target - walked) / length)
        walked += length
        pts = stroke.points
        if frac < 1.0:
            seglens = np.linalg.norm(np.diff(pts, axis=0), axis=1)
            cum = np.concatenate([[0.0], np.cumsum(seglens)])
            cut = frac * cum[-1]
            j = int(np.searchsorted(cum, cut) - 1)
            j = max(0, min(j, len(pts) - 2))
            f = (cut - cum[j]) / (seglens[j] or 1.0)
            end = pts[j] + (pts[j + 1] - pts[j]) * f
            pts = np.vstack([pts[: j + 1], end])
            tip = tx([end])[0]
        mapped = tx(pts)
        width_px = max(1.6, min(3.4, stroke.width * s * d.unit_px * 0.9))
        # Line hierarchy: main contours a touch heavier, small details finer.
        if stroke.length >= long_cut:
            width_px = min(3.8, width_px * 1.15)
        elif stroke.length <= short_cut:
            width_px = max(1.2, width_px * 0.75)

        def path(c, mapped=mapped):
            # Smooth curves through the traced points (midpoint quadratic splines),
            # so lines read as ink, not as joined segments.
            c.move_to(*mapped[0])
            if len(mapped) < 3:
                for p in mapped[1:]:
                    c.line_to(*p)
                return
            x0, y0 = mapped[0]
            for (x1, y1), (x2, y2) in zip(mapped[1:-1], mapped[2:]):
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                cx0, cy0 = c.get_current_point()
                c.curve_to(cx0 + 2 / 3 * (x1 - cx0), cy0 + 2 / 3 * (y1 - cy0),
                           mx + 2 / 3 * (x1 - mx), my + 2 / 3 * (y1 - my), mx, my)
            c.line_to(*mapped[-1])

        if stroke.gold:
            # Accent in the scene's colour; a softer glow so it never covers the drawing.
            d.stroke(path, accent, width_px, alpha=0.88 + 0.12 * pulse)
            d.stroke(path, accent, width_px * 0.8, alpha=0.45 + 0.1 * pulse, hot=True)
        else:
            d.stroke(path, "line", width_px, alpha=0.92)
            d.stroke(path, "line", width_px, alpha=0.18, hot=True)
    if tip is not None and reveal < 1.0:
        pen_light(d, tip[0], tip[1])


_FILL_CACHE: dict[tuple[int, str], object] = {}


def _fill_surface(mask: np.ndarray, rgb: tuple[float, float, float], key: tuple[int, str]):
    """A cairo surface of a fill mask with a light diagonal sketch texture."""
    import cairo

    if key in _FILL_CACHE:
        return _FILL_CACHE[key]
    h, w = mask.shape
    yy, xx = np.mgrid[0:h, 0:w]
    hatch = 0.55 + 0.45 * (np.sin((xx + yy) * 0.9) > 0.6)  # soft pencil strokes
    alpha = (mask * hatch * 255).astype(np.uint8)
    data = np.zeros((h, w, 4), np.uint8)
    for i, c in enumerate((rgb[2], rgb[1], rgb[0])):  # cairo is premultiplied BGRA
        data[..., i] = (alpha * c).astype(np.uint8)
    data[..., 3] = alpha
    surface = cairo.ImageSurface.create_for_data(bytearray(data.tobytes()), cairo.FORMAT_ARGB32, w, h, w * 4)
    if len(_FILL_CACHE) > 64:
        _FILL_CACHE.clear()
    _FILL_CACHE[key] = surface
    return surface


def _paint_fills(d, drawing: Drawing, accent: str, s, cx, cy, ox, oy, reveal: float) -> None:
    """Fill closed shapes softly once most of the drawing is on screen."""
    a = max(0.0, min(1.0, (reveal - 0.55) / 0.35))
    if a <= 0.0:
        return
    for mask, color, strength in ((drawing.fill, "line", 0.13), (drawing.accent_fill, accent, 0.26)):
        if mask is None or not mask.any():
            continue
        surface = _fill_surface(mask, d.colors[color], (id(mask), color))
        ctx = d.main
        ctx.save()
        ctx.translate(ox, oy)
        ctx.scale(s, s)
        ctx.translate(-cx, -cy)
        ctx.set_source_surface(surface, 0, 0)
        ctx.paint_with_alpha(strength * a * a * (3 - 2 * a))
        ctx.restore()


def illustration(d) -> None:
    """Primitive: the scene's drawing, revealed over most of the scene."""
    drawing = SCENES.get(d.icons[0]) if d.icons else None
    if drawing is None:
        return
    span = max(1.0, d.span)
    breathe = min(1.0, d.t / span)
    if drawing.entrance == "fade":
        # Already drawn as it fades in; the accent part then lights up, drawn by
        # the pen light, a moment after the scene starts (the "bling" moment).
        gold = sum(s.length for s in drawing.strokes if s.gold)
        lit = max(0.0, min(1.0, (d.t - ACCENT_DELAY) / ACCENT_DRAW))
        reveal = (drawing.total - gold + gold * lit) / drawing.total
        draw_illustration(d, drawing, d.region, reveal, breathe=breathe, zoom=d.zoom, linear=True)
        return
    reveal_time = min(max(0.72 * span, 2.5), 16.0, span)
    reveal = d.t / reveal_time
    draw_illustration(d, drawing, d.region, reveal, breathe=breathe, zoom=d.zoom)


# When the accent of a faded-in scene lights up (seconds after the scene starts).
ACCENT_DELAY = 0.45
ACCENT_DRAW = 1.1
