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

SCENE_COUNTS = {"short": (4, 6), "long": (8, 14)}

VISUAL_PLAN_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
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
                },
                "required": ["first_line", "last_line", "drawing", "gold_element"],
            },
        },
    },
    "required": ["scenes"],
}


def scene_plan_instructions(format_name: str) -> str:
    low, high = SCENE_COUNTS.get(format_name, SCENE_COUNTS["short"])
    return f"""\
You are the storyboard artist for a narrated explainer video in the style of
animated line-illustration channels: on a black screen, one hand-drawn white
line illustration builds while the narrator speaks, then dissolves into the
next. You receive the spoken lines, numbered from 0. Do not change any words.

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

"gold_element": the single part of the drawing that should glow gold because
it carries the meaning of the scene (for example: "the heat lines").

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
    area = ("Keep the whole drawing in the upper two thirds of the tall frame; "
            "the bottom third stays empty black." if format_name == "short" else
            "Keep the drawing centred with empty black margins; the bottom fifth stays empty black.")
    return (
        "Minimal elegant line illustration: thin, clean, single-weight white lines on a pure "
        "flat black background, like a confident hand-drawn ink sketch made with a fine glowing "
        "pen. Outlines only: no fills, no shading, no hatching, no gradients, no textures, no "
        "glow halos, no colour except one part. Draw the following as one composed scene: "
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
    return Drawing(_order(strokes), image.width, image.height, (float(x0), float(y0), float(x1), float(y1)))


# --------------------------------------------------------------------------
# Drawing on screen
# --------------------------------------------------------------------------

# Filled by the renderer before frames are drawn: scene id -> Drawing.
SCENES: dict[str, Drawing] = {}

# Region the illustration may occupy, in the renderer's unit coordinates.
REGIONS = {"short": (-1.18, -1.42, 1.18, 1.22), "long": (-2.0, -0.95, 2.0, 1.12)}


def fit(drawing: Drawing, region: tuple[float, float, float, float]):
    x0, y0, x1, y1 = drawing.bbox
    rx0, ry0, rx1, ry1 = region
    w, h = max(1.0, x1 - x0), max(1.0, y1 - y0)
    s = min((rx1 - rx0) / w, (ry1 - ry0) / h)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ox, oy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
    return s, cx, cy, ox, oy


def draw_illustration(d, drawing: Drawing, region, reveal: float, breathe: float = 0.0) -> None:
    from .primitives import pen_light

    s, cx, cy, ox, oy = fit(drawing, region)
    s *= 1.0 + 0.025 * breathe  # slow push-in over the scene

    def tx(points):
        return [((x - cx) * s + ox, (y - cy) * s + oy) for x, y in points]

    target = drawing.total * max(0.0, min(1.0, reveal))
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

        def path(c, mapped=mapped):
            c.move_to(*mapped[0])
            for p in mapped[1:]:
                c.line_to(*p)

        if stroke.gold:
            d.stroke(path, "gold", width_px, alpha=0.85 + 0.15 * pulse, hot=True)
        else:
            d.stroke(path, "line", width_px, alpha=0.92)
            d.stroke(path, "line", width_px, alpha=0.18, hot=True)
    if tip is not None and reveal < 1.0:
        pen_light(d, tip[0], tip[1])


def illustration(d) -> None:
    """Primitive: the scene's drawing, revealed over most of the scene."""
    drawing = SCENES.get(d.icons[0]) if d.icons else None
    if drawing is None:
        return
    span = max(1.0, d.span)
    reveal_time = min(max(0.72 * span, 2.5), 16.0, span)
    reveal = d.t / reveal_time
    draw_illustration(d, drawing, d.region, reveal, breathe=min(1.0, d.t / span))
