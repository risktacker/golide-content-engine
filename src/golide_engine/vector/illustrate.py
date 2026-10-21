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
from dataclasses import dataclass, field
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
                "colors": {"type": "array", "items": {"type": "string", "enum": list(ACCENTS)}},
                "thumbnail_text": {"type": "string"},
                "thumbnail_punch": {"type": "string"},
            },
            "required": ["text", "gold", "scene", "thumbnail_moment", "colors", "thumbnail_text",
                         "thumbnail_punch"],
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
                    "figure": {"type": "string"},
                    "layout": {"type": "string", "enum": ["single", "wide", "duo"]},
                    "drawing_b": {"type": "string"},
                    "gold_element_b": {"type": "string"},
                    "figure_b": {"type": "string"},
                    "label": {"type": "string"},
                    "label_b": {"type": "string"},
                },
                "required": ["first_line", "last_line", "drawing", "gold_element", "accent", "sound", "sound_word",
                             "figure", "layout", "drawing_b", "gold_element_b", "figure_b", "label", "label_b"],
            },
        },
    },
    "required": ["cover", "scenes"],
}


def scene_plan_instructions(format_name: str, duration: float | None = None) -> str:
    from .figures import EXAMPLES
    from .pacing import scene_range, storyboard_rules

    low, high = SCENE_COUNTS.get(format_name, SCENE_COUNTS["short"])
    pacing = ""
    if duration:  # the recording's real length decides how many pictures (2026-10-18)
        low, high = scene_range(format_name, duration)
        pacing = storyboard_rules(format_name, duration)
    from .layouts import STORYBOARD_RULES

    figure_menu = "\n".join("  " + example for example in EXAMPLES.values())
    layout_rules = STORYBOARD_RULES
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

DEFINED, NEVER VAGUE (owner direction 2026-10-20: "we need definition"; this is
industry-level illustration). Any kind of picture is welcome, but every one is
built with clear structure so a viewer reads it instantly:
- an object or scene: a bold, clean outline of a real thing, its key parts clear;
- a network: a few clear nodes (circles or boxes) joined by clean straight lines,
  one node clearly the centre;
- roots, a tree or branches: one trunk and a few deliberate branches, each ending
  in something you can name;
- a map: the clean outline of a real, recognisable place with a few clear marks;
- dots or a constellation: dots that form a recognisable shape or pattern.
Never vague blobs, tangles, random branches, textures or clutter. When an
abstract idea (a fund, shares, a vote, control) needs a picture, give it a
concrete form: a jar of coins, a pie with one slice lifted out, a balance scale,
a ballot box, a vault door, or an exact diagram (see DIAGRAMS below).

LABELS (owner direction 2026-10-20: a label must be clean and sit on the thing it
names). "label": one or two short words printed on the glowing part, like a word
on a jar ("BONDS"), a sign or a box, or "" for none. The engine prints it in sharp
type on that part, so "gold_element" must be the part that carries the label (for
example "the label panel on the jar"). Most scenes need no label; use one only
when the word makes the picture clearer. "label_b": the same for "drawing_b".

VARIETY (owner direction 2026-10-07: the visuals must feel vast, never repeated):
every scene uses a different kind of shot from the one before, mixing across
the video: a wide scene with people in a place, a close-up of one object, a
visual metaphor (a key, a bridge, a scale, a jar, a seed growing), a before
and after side by side, a clearly built network or constellation, a symbol
drawn large (an eye, a clock, a lock), an overhead or cross-section view. Never draw the same main object in two scenes in a row, and never use
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
- "thumbnail_moment": one sentence for the YouTube thumbnail artist (owner
  direction 2026-10-20: the same kind of picture as our static posts). ONE object
  or ONE visual metaphor that captures the story's tension, chosen by the topic,
  understood in one second, and name the ONE part of it that glows. Examples: "a
  house key on a ring whose teeth glow" (leaked API keys); "an old balance scale,
  a glowing chip in one pan outweighing a lump of coal in the other" (a market
  record); "a glass padlock with a crack running through its glowing keyhole" (an
  attack path); "a film reel whose single glowing frame unspools" (AI in video
  editing). Never a face, avatar or character; a hand only if the metaphor needs it.
- "thumbnail_text": ONE TO THREE words printed huge on the YouTube thumbnail (owner
  direction 2026-10-21). A curiosity gap the title does NOT answer, never a summary
  and never the title's words: "WHO GETS IT?", "KEYS LEAKED", "NOT FLYING", "OUTWEIGHED".
  "thumbnail_punch": the one word of it shown in the glow colour, copied exactly.
- "colors": two or three accent colours for the cover and thumbnail, chosen by
  meaning from gold, rose, teal, ivory and copper (owner direction 2026-10-18:
  not always gold; 2026-10-20: not always teal either). The first is the glow of
  the thumbnail's key element and colours the punch words.

If the lines are divided into chapters (marked "== CHAPTER ... =="), a scene
never runs across a chapter mark: every chapter starts with a new scene.

EXACT FIGURES (the math and physics layer, owner direction 2026-10-16): a
drawn sketch guesses angles and lengths. When a scene's lines teach exact
maths, physics or engineering with real numbers (vectors, Pythagoras,
trigonometry, graphs, slope or area, motion and Newton's laws, forces, beams,
lenses, reflection, refraction, prisms, waves, the electromagnetic spectrum,
gas laws, heat engines, relativity), set "figure" to ONE line in one of these
forms, using the numbers spoken in those lines, and the engine draws it
precisely instead of the sketch:
{figure_menu}
Never invent numbers the lines do not give.

DIAGRAMS (owner direction 2026-10-20): when a scene explains who connects to
whom, how something flows step by step, or who sits above whom (a fund and the
people it serves, money moving from shares to grants, a company and its
board), use the "network", "flow" or "tree" figure above with the real names
from the lines. The engine draws it exactly, with clean labels.

Everywhere else, and in every plain story scene, "figure" is "" and the drawing is used. Still write
"drawing" and "gold_element" for a figure scene (they are the fallback).

{layout_rules}
{pacing}"""


def validate_scenes(scenes: list[dict], line_count: int, breaks: set[int] | frozenset[int] = frozenset(),
                    max_scenes: int | None = None) -> list[dict]:
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
    # Never more pictures than the budget plans for (2026-10-08 audit): merge
    # the shortest neighbouring scenes until the count fits.
    limit = max_scenes or len(fixed)
    while len(fixed) > limit:
        sizes = [s["last_line"] - s["first_line"] for s in fixed]
        i = min(range(len(fixed) - 1), key=lambda k: sizes[k] + sizes[k + 1]
                if not (breaks and fixed[k + 1]["first_line"] in breaks) else 10 ** 6)
        if breaks and fixed[i + 1]["first_line"] in breaks:
            break  # every remaining join would cross a chapter
        fixed[i] = {**fixed[i], "last_line": fixed[i + 1]["last_line"]}
        del fixed[i + 1]
    for index, scene in enumerate(fixed):
        scene["id"] = f"scene-{index + 1:02d}"
    return fixed


def illustration_prompt(drawing: str, gold: str, format_name: str, layout: str = "single",
                        label: str = "") -> str:
    from .layouts import composition

    area = composition(format_name, layout)
    return (
        "Minimal elegant line illustration: thin, clean white lines on a pure flat black "
        "background, like a confident hand-drawn ink sketch made with a fine glowing pen. "
        "Main shapes in a steady line with a bold, instantly recognisable outline; a few small "
        "inner details (a seam, a button, a window, a fold) in finer lines so the drawing has "
        "depth without clutter. Networks, branches, maps and dot patterns are welcome when "
        "asked for, but always clearly structured. No textures, hatching, cracks, mosaics or "
        "random scribbles. Give the scene a simple ground line or soft horizon so objects sit somewhere, "
        "one clear focal point, and generous empty space around it. Every line closed and "
        "deliberate; no sketchy double lines, no stray dots. Outlines only: no fills, no solid "
        "shapes, no shading, no gradients, no glow halos, no colour except one part. Draw the "
        "following as one composed scene: "
        f"{drawing.strip()} Draw only this part in warm gold lines: {gold.strip()}. "
        + (f"Give {gold.strip()} a clean, empty label panel (a plain outlined rectangle) where a "
           "word will be printed later. " if label.strip() else "")
        + "No text, letters, numbers, labels, logos, watermarks or user-interface elements anywhere; "
        "any sign, label or screen is left empty. "
        f"{area}"
    )


# --------------------------------------------------------------------------
# Vectorising a line drawing into ordered pen strokes
# --------------------------------------------------------------------------

DIM_PACE = 0.35


@dataclass
class Stroke:
    points: np.ndarray  # (n, 2) in image pixels
    gold: bool
    width: float  # in image pixels
    dim: bool = False  # secondary lines (axes, ticks, guides) drawn softer
    rgb: tuple | None = None  # a true colour (a spectrum), 0-255

    @property
    def length(self) -> float:
        # Pen time: guide lines (axes, ticks) are drawn quickly so the pen spends
        # its time on what the scene is about.
        return float(np.sum(np.linalg.norm(np.diff(self.points, axis=0), axis=1))) * (DIM_PACE if self.dim else 1.0)


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
    # Exact figures (vector.figures): crisp labels, each shown once the pen has
    # drawn this share of the figure: (cairo surface, x, y, after).
    labels: list = field(default_factory=list)
    keep_order: bool = False
    # Duo layout (long videos): the right-hand drawing, drawn after this one.
    companion: "Drawing | None" = None
    clip: bool = False  # a pacing shot: framed on part of the picture, clipped to the drawing area
    figure: bool = False  # an exact figure (maths, physics): the background shows the lesson grid
    traced: int = 0       # strokes found by the tracer before clean-up (a clutter measure)

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


CLUTTER_STROKES = 110     # above this many traced strokes, a picture is cluttered
MAX_STROKES = 170         # never draw more than this many
MAX_GOLD = 60             # glowing strokes kept at most, so the outline always has room
SHORT_SHARE = 0.03        # in a cluttered picture, white strokes shorter than this share of
                          # the drawing's diagonal are texture, not shape


def declutter(strokes: list[Stroke]) -> list[Stroke]:
    """Drop traced texture (hatching, cracks, mosaics) so the shape reads (2026-10-20).

    A clean line drawing traces into a few dozen strokes; texture traces into
    hundreds of tiny ones. When a picture is cluttered, short strokes go and only
    the longest are kept. The glow is capped too (2026-10-21: a mostly-gold picture
    lost its whole white outline and became a gold tangle), so the outline that
    says what the object is always survives.
    """
    if len(strokes) <= CLUTTER_STROKES:
        return strokes
    pts = np.vstack([s.points for s in strokes])
    diag = float(np.hypot(*(pts.max(axis=0) - pts.min(axis=0)))) or 1.0
    gold = sorted((s for s in strokes if s.gold), key=lambda s: -s.length)[:MAX_GOLD]
    white = [s for s in strokes if not s.gold and s.length >= SHORT_SHARE * diag]
    white.sort(key=lambda s: -s.length)
    return gold + white[:MAX_STROKES - len(gold)]


GOLD_SHARE_MAX = 0.5      # more glowing line than this and the picture has no clear focus
MIN_STROKES = 5


def picture_problems(drawing: "Drawing") -> list[str]:
    """Why a traced picture would read as an undefined block on screen ([] when it is fine)."""
    total = sum(s.length for s in drawing.strokes) or 1.0
    gold = sum(s.length for s in drawing.strokes if s.gold)
    problems = []
    if gold / total > GOLD_SHARE_MAX:
        problems.append("almost everything glows; draw the object in thin white lines and make only ONE "
                        "small part glow gold")
    if len(drawing.strokes) < MIN_STROKES:
        problems.append("the drawing is nearly empty; draw the whole object with a clear outline")
    if drawing.traced > CLUTTER_STROKES * 2:
        problems.append("the drawing is a tangle of tiny lines; use fewer, longer, cleaner lines and no texture")
    return problems


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
    traced = len(strokes)
    strokes = declutter(strokes)
    allpts = np.vstack([s.points for s in strokes])
    x0, y0 = allpts.min(axis=0)
    x1, y1 = allpts.max(axis=0)
    fill, accent_fill = _fills(mask, goldness)
    return Drawing(_order(strokes), image.width, image.height, (float(x0), float(y0), float(x1), float(y1)),
                   fill, accent_fill, traced=traced)


def accent_box(drawing: Drawing) -> tuple[float, float, float, float] | None:
    """Bounding box of the drawing's accent (gold) strokes, in image pixels."""
    pts = [s.points for s in drawing.strokes if s.gold]
    if not pts:
        return None
    allpts = np.vstack(pts)
    (x0, y0), (x1, y1) = allpts.min(axis=0), allpts.max(axis=0)
    return float(x0), float(y0), float(x1), float(y1)


COMPACT = 0.45   # a part smaller than this share of the drawing (each way) is an object, kept whole


def _whole_objects(drawing: Drawing, box: tuple) -> tuple:
    x0, y0, x1, y1 = drawing.bbox
    w, h = max(1.0, x1 - x0), max(1.0, y1 - y0)
    for _round in range(3):  # widening can touch a neighbour; settle in a few passes
        grown = box
        for s in drawing.strokes:
            (sx0, sy0), (sx1, sy1) = s.points.min(axis=0), s.points.max(axis=0)
            if sx1 - sx0 > w * COMPACT or sy1 - sy0 > h * COMPACT:
                continue
            inside = sx0 >= grown[0] and sx1 <= grown[2] and sy0 >= grown[1] and sy1 <= grown[3]
            touches = sx0 < grown[2] and sx1 > grown[0] and sy0 < grown[3] and sy1 > grown[1]
            if touches and not inside:
                grown = (min(grown[0], sx0), min(grown[1], sy0), max(grown[2], sx1), max(grown[3], sy1))
        if grown == box:
            break
        box = grown
    return box


def shot_of(drawing: Drawing, shot: int) -> Drawing:
    """Another shot of the same picture (owner direction 2026-10-18, more flips in the
    hook for free): odd shots frame the glowing accent, even shots the other half."""
    import dataclasses

    if drawing.keep_order:
        # An exact figure is never cropped: its labels would be cut. The shot shows
        # the whole figure again, already drawn, with its accent lighting up.
        return dataclasses.replace(drawing, entrance="fade", companion=None)
    x0, y0, x1, y1 = drawing.bbox
    w, h = x1 - x0, y1 - y0
    focus = accent_box(drawing) if shot % 2 == 1 else None
    if focus is None:
        # Alternate halves of the drawing: right, left, top...
        half = (shot // 2) % 3
        focus = ((x0 + w * 0.45, y0, x1, y1) if half == 0 else
                 (x0, y0, x1 - w * 0.45, y1) if half == 1 else (x0, y0, x1, y1 - h * 0.4))
    fx0, fy0, fx1, fy1 = focus
    # 2026-10-20: never closer than about 1.5x, so a shot always still shows the object
    # (2.2x cut vague pictures into meaningless fragments).
    min_w, min_h = w * 0.68, h * 0.68
    cx, cy = (fx0 + fx1) / 2, (fy0 + fy1) / 2
    fw, fh = max(fx1 - fx0, min_w) * 1.25, max(fy1 - fy0, min_h) * 1.25
    box = (cx - fw / 2, cy - fh / 2, cx + fw / 2, cy + fh / 2)
    # 2026-10-20: a zoom never slices an object. Any compact part the shot cuts through
    # (a tree, a window, a coin) is taken in whole; long lines (a ground line, a wall)
    # may still run off the edge, as they would in any close-up.
    box = _whole_objects(drawing, box)
    # A printed label the shot touches is kept whole: the shot widens to include it.
    for surface, lx, ly, _after, _keep in drawing.labels:
        lx1, ly1 = lx + surface.get_width(), ly + surface.get_height()
        if lx < box[2] and lx1 > box[0] and ly < box[3] and ly1 > box[1]:
            box = (min(box[0], lx), min(box[1], ly), max(box[2], lx1), max(box[3], ly1))
    return dataclasses.replace(drawing, bbox=box, entrance="fade", companion=None, clip=True)


def load_figure(image_path: Path) -> Drawing | None:
    """The exact strokes and labels of a code-drawn figure, or None for a normal picture."""
    import json

    import cairo

    from .figures import sidecar_path

    meta_path = sidecar_path(Path(image_path))
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    strokes = [Stroke(np.array(item["points"], np.float64), bool(item["gold"]), float(item["width"]),
                      bool(item.get("dim")), tuple(item["rgb"]) if item.get("rgb") else None)
               for item in meta["strokes"] if len(item["points"]) >= 2]
    if not strokes:
        return None
    labels = []
    xs = [p[0] for st in strokes for p in st.points]
    ys = [p[1] for st in strokes for p in st.points]
    for item in meta.get("labels", []):
        from PIL import Image

        crop = Image.open(meta_path.parent / item["file"]).convert("RGBA")
        rgba = np.asarray(crop, np.float32) / 255.0
        alpha = rgba[..., 3:4]
        bgra = np.concatenate([rgba[..., 2:3] * alpha, rgba[..., 1:2] * alpha, rgba[..., 0:1] * alpha, alpha], axis=2)
        data = bytearray((bgra * 255).astype(np.uint8).tobytes())
        surface = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, crop.width, crop.height,
                                                     crop.width * 4)
        labels.append((surface, float(item["x"]), float(item["y"]), float(item["after"]), data))
        xs += [float(item["x"]), float(item["x"]) + crop.width]
        ys += [float(item["y"]), float(item["y"]) + crop.height]
    bbox = (min(xs), min(ys), max(xs), max(ys))
    return Drawing(strokes, int(meta["width"]), int(meta["height"]), bbox, None, None,
                   accent="gold", entrance="pen", labels=labels, keep_order=True, figure=True)


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


FIT_INSET = 0.05  # share of the area kept free on each side for the push-in and drift


def inset(region: tuple[float, float, float, float], share: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = region
    dx, dy = (x1 - x0) * share, (y1 - y0) * share
    return x0 + dx, y0 + dy, x1 - dx, y1 - dy


def fit(drawing: Drawing, region: tuple[float, float, float, float]):
    x0, y0, x1, y1 = drawing.bbox
    rx0, ry0, rx1, ry1 = region
    w, h = max(1.0, x1 - x0), max(1.0, y1 - y0)
    s = min((rx1 - rx0) / w, (ry1 - ry0) / h)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ox, oy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
    return s, cx, cy, ox, oy


def draw_illustration(d, drawing: Drawing, region, reveal: float, breathe: float = 0.0, zoom: float = 1.0,
                      linear: bool = False, settled: float = -1.0) -> None:
    """settled: seconds since the drawing finished (-1 while it is still drawing)."""
    from .primitives import pen_light

    # Fit inside a slightly smaller area so the push-in, drift and transitions grow the
    # drawing back to its area without ever crossing the edge (2026-10-18: no cut labels).
    s, cx, cy, ox, oy = fit(drawing, region if drawing.clip else inset(region, FIT_INSET))
    # Owner direction 2026-10-13: a finished drawing never sits still. A steady
    # push-in over the scene plus a slow, small drift keeps it alive.
    s *= (1.0 + LIFE_PUSH * breathe) * zoom
    if settled > 0:
        ease_in = min(1.0, settled / 1.5)
        span_x, span_y = (region[2] - region[0]), (region[3] - region[1])
        ox += LIFE_DRIFT * span_x * ease_in * math.sin(d.t * 0.33 + 0.7)
        oy += LIFE_DRIFT * 0.7 * span_y * ease_in * math.sin(d.t * 0.27 + 2.1)
    accent = "accent_" + drawing.accent if ("accent_" + drawing.accent) in d.colors else "gold"
    if d.marking > 0 and not drawing.clip and not drawing.keep_order:
        # A spoken number: push in toward the accent while its card is on screen.
        box = accent_box(drawing)
        if box is not None:
            push = 0.14 * math.sin(math.pi * min(1.0, d.marking)) ** 0.6
            ax, ay = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            s *= 1 + push
            ox -= (ax - cx) * s * push / (1 + push)
            oy -= (ay - cy) * s * push / (1 + push)
    # 2026-10-18: a drawing never leaves its area (push-ins, drift and zooms included), so it
    # can never run into the captions, the tag or the spoken-number zone. Shots are cut
    # exactly at the area's edge; whole drawings get a little room to breathe.
    clipped = True
    room = 0.0 if drawing.clip else 0.04
    w_r, h_r = region[2] - region[0], region[3] - region[1]
    for ctx in (d.main, d.glow):
        ctx.save()
        # No room above: the spoken-number zone sits right over the drawing area.
        ctx.rectangle(region[0] - w_r * room, region[1], w_r * (1 + 2 * room), h_r * (1 + room))
        ctx.clip()
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
        elif stroke.rgb:
            key = "rgb_%d_%d_%d" % stroke.rgb
            if key not in d.colors:
                d.colors[key] = tuple(v / 255 for v in stroke.rgb)
            d.stroke(path, key, width_px, alpha=0.95)
            d.stroke(path, key, width_px * 0.8, alpha=0.4, hot=True)
        elif stroke.dim:
            d.stroke(path, "line", width_px * 0.8, alpha=0.42)
        else:
            d.stroke(path, "line", width_px, alpha=0.92)
            d.stroke(path, "line", width_px, alpha=0.18, hot=True)
    if drawing.labels:
        done = target / drawing.total
        for surface, lx, ly, after, _keep in drawing.labels:
            a = max(0.0, min(1.0, (done - after) / 0.06 + 1.0)) if done < 1.0 else 1.0
            if a <= 0.0:
                continue
            ctx = d.main
            ctx.save()
            ctx.translate(ox, oy)
            ctx.scale(s, s)
            ctx.translate(-cx, -cy)
            ctx.set_source_surface(surface, lx, ly)
            ctx.paint_with_alpha(a)
            ctx.restore()
    if tip is not None and reveal < 1.0:
        pen_light(d, tip[0], tip[1])
    if settled > SHIMMER_START:
        _shimmer(d, drawing, accent, tx, s, settled - SHIMMER_START)
    if d.marking > 0 and not drawing.keep_order:
        _mark_ring(d, drawing, accent, tx)
    if clipped:
        for ctx in (d.main, d.glow):
            ctx.restore()


def _mark_ring(d, drawing: Drawing, accent: str, tx) -> None:
    """A highlight ring drawn around the accent while a spoken number is on screen."""
    box = accent_box(drawing)
    if box is None:
        return
    bx0, by0, bx1, by1 = drawing.bbox
    share = ((box[2] - box[0]) * (box[3] - box[1])) / max(1.0, (bx1 - bx0) * (by1 - by0))
    if share > 0.35:
        return  # the accent is most of the picture: a ring would just circle everything
    (x0, y0), (x1, y1) = tx([(box[0], box[1]), (box[2], box[3])])
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = max(0.07, abs(x1 - x0) * 0.62), max(0.07, abs(y1 - y0) * 0.62)
    sweep = min(1.0, d.marking * 2.2)                 # drawn on quickly, then held
    fade = min(1.0, (1.0 - d.marking) * 5.0)          # gone as the card leaves

    def path(c):
        c.save()
        c.translate(cx, cy)
        c.scale(rx, ry)
        c.arc(0, 0, 1.0, -math.pi / 2, -math.pi / 2 + math.tau * sweep)
        c.restore()
    d.stroke(path, accent, 3.2, alpha=0.95 * fade, hot=True)


# Life after the drawing is finished (owner direction 2026-10-13).
LIFE_PUSH = 0.06        # push-in across the scene (was 0.025)
LIFE_DRIFT = 0.012      # drift, as a share of the drawing region
SHIMMER_START = 0.8     # seconds after the drawing settles
SHIMMER_PERIOD = 3.6    # a light runs through the drawing this often
SHIMMER_RUN = 1.8       # ... taking this long, end to end


def _shimmer(d, drawing: Drawing, accent: str, tx, s: float, t: float) -> None:
    """A soft light that runs along the finished drawing's strokes, again and again."""
    phase = (t % SHIMMER_PERIOD) / SHIMMER_RUN
    if phase >= 1.0 or not drawing.strokes:
        return
    head = phase * drawing.total
    tail = head - drawing.total * 0.18
    walked = 0.0
    for stroke in drawing.strokes:
        start, end = walked, walked + (stroke.length or 1.0)
        walked = end
        if end < tail or start > head:
            continue
        mid = (start + end) / 2
        k = max(0.0, 1.0 - abs(head - mid) / (drawing.total * 0.18 + 1e-6))
        if k <= 0.02:
            continue
        mapped = tx(stroke.points)
        width_px = max(1.6, min(3.4, stroke.width * s * d.unit_px * 0.9))

        def path(c, mapped=mapped):
            c.move_to(*mapped[0])
            for p in mapped[1:]:
                c.line_to(*p)

        color = accent if stroke.gold else "line"
        d.stroke(path, color, width_px * 1.1, alpha=0.55 * k, hot=True)


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
    """Primitive: the scene's drawing (or its duo pair), revealed over the scene."""
    drawing = SCENES.get(d.icons[0]) if d.icons else None
    if drawing is None:
        return
    if drawing.companion is None:
        _reveal(d, drawing, d.region, d.t, max(1.0, d.span))
        return
    from .layouts import DUO_SECOND_REVEAL, DUO_SECOND_START, duo_regions

    span = max(1.0, d.span)
    left, right = duo_regions(d.region)
    # The left idea is drawn first, in the first part of the scene ...
    _reveal(d, drawing, left, d.t, span * DUO_SECOND_START + 1.0, breathe_span=span)
    # ... then the right one is drawn by the pen while the left one breathes.
    start = span * DUO_SECOND_START
    if d.t > start:
        _reveal(d, drawing.companion, right, d.t - start, span * DUO_SECOND_REVEAL / 0.72,
                breathe_span=span, pen=True)
    mid = (d.region[0] + d.region[2]) / 2
    a = min(1.0, d.t / 1.2) * 0.22
    d.stroke(lambda c: (c.move_to(mid, d.region[1] + 0.2), c.line_to(mid, d.region[3] - 0.2)),
             "line_dim", 1.0, alpha=a)


def _reveal(d, drawing: Drawing, region, t: float, span: float, breathe_span: float | None = None,
            pen: bool = False) -> None:
    """One drawing in one region: faded in with its accent lighting up, or drawn by the pen."""
    breathe = min(1.0, t / (breathe_span or span))
    if drawing.entrance == "fade" and not pen:
        # Already drawn as it fades in; the accent part then lights up, drawn by
        # the pen light, a moment after the scene starts (the "bling" moment).
        gold = sum(s.length for s in drawing.strokes if s.gold)
        lit = max(0.0, min(1.0, (t - ACCENT_DELAY) / ACCENT_DRAW))
        reveal = (drawing.total - gold + gold * lit) / drawing.total
        settled = t - (ACCENT_DELAY + ACCENT_DRAW) if lit >= 1.0 else -1.0
        draw_illustration(d, drawing, region, reveal, breathe=breathe, zoom=d.zoom, linear=True,
                          settled=settled)
        return
    from .pacing import reveal_seconds

    # 2026-10-18: the pen keeps the voice's pace (fast speech, fast pen; quick in the hook).
    reveal_time = reveal_seconds(span, d.words, d.hook)
    reveal = t / reveal_time
    settled = t - reveal_time if reveal >= 1.0 else -1.0
    draw_illustration(d, drawing, region, reveal, breathe=breathe, zoom=d.zoom, settled=settled)


# When the accent of a faded-in scene lights up (seconds after the scene starts).
ACCENT_DELAY = 0.45
ACCENT_DRAW = 1.1
