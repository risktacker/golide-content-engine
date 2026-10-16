"""Scene layouts for long videos (owner direction 2026-10-16).

A 16:9 frame is about twice as wide as it is tall, while one picture is
scaled to fit the drawing area's height, so a single compact drawing leaves
empty bands on the left and right. Long videos therefore mix three layouts:

* ``single``: one centred drawing (a close-up, a symbol): the bands are fine.
* ``wide``:   one panoramic drawing, composed left to right across the frame.
* ``duo``:    two drawings side by side (before/after, cause/effect, two
              sides of a comparison), the right one drawn after the left.

Shorts are always ``single``: a 9:16 frame is already filled by one drawing.
Captions are unchanged and stay centred under the drawing area.
"""

from __future__ import annotations

LAYOUTS = ("single", "wide", "duo")
DUO_GUTTER = 0.16          # gap between the two halves, in drawing units
DUO_SHARE = 3              # at most one scene in this many is a duo (each costs a second picture)
DUO_SECOND_START = 0.40    # the right drawing starts at this share of the scene
DUO_SECOND_REVEAL = 0.45   # ... and takes this share of the scene to draw


def second_id(scene_id: str) -> str:
    """The id (and picture name) of a duo scene's right-hand drawing."""
    return f"{scene_id}-b"


def has_second(scene: dict) -> bool:
    return bool(str(scene.get("drawing_b") or "").strip() or str(scene.get("figure_b") or "").strip())


def normalize(scenes: list[dict], format_name: str) -> list[dict]:
    """Every scene gets a valid layout; shorts and incomplete duos become single."""
    duo_budget = max(1, len(scenes) // DUO_SHARE)
    out = []
    for scene in scenes:
        layout = str(scene.get("layout") or "single").strip().lower()
        if format_name != "long" or layout not in LAYOUTS:
            layout = "single"
        if layout == "duo":
            if not has_second(scene) or duo_budget <= 0:
                layout = "wide" if format_name == "long" else "single"
            else:
                duo_budget -= 1
        fixed = {**scene, "layout": layout}
        if layout != "duo":
            fixed.update({"drawing_b": "", "gold_element_b": "", "figure_b": ""})
        out.append(fixed)
    return out


def duo_regions(region: tuple[float, float, float, float]):
    """Left and right halves of a drawing region, with a gutter between them."""
    x0, y0, x1, y1 = region
    mid = (x0 + x1) / 2
    return (x0, y0, mid - DUO_GUTTER / 2, y1), (mid + DUO_GUTTER / 2, y0, x1, y1)


def art_size(format_name: str, layout: str) -> str:
    """Picture size to ask the image model for."""
    if format_name == "short":
        return "1024x1536"
    return "1024x1024" if layout == "duo" else "1536x1024"


def figure_size(format_name: str, layout: str) -> tuple[int, int]:
    """Canvas for a code-drawn figure. Not bound to image-model sizes, so a wide
    scene gets the drawing area's own shape (about 2.1:1) and graphs fill it."""
    if format_name == "long" and layout == "wide":
        return 2100, 1000
    width, height = art_size(format_name, layout).split("x")
    return int(width), int(height)


def composition(format_name: str, layout: str) -> str:
    """The composition sentence of the image prompt for this layout."""
    if format_name == "short":
        return ("Portrait composition: one compact scene in the centre with wide empty black "
                "margins on the left and right; nothing touches the edges, and any ground line is "
                "short, not edge to edge.")
    if layout == "wide":
        return ("Panoramic composition: a wide horizontal scene arranged from left to right across "
                "the whole width, like a long strip; the top and bottom quarters stay empty black, "
                "the left and right ends carry part of the scene, and nothing touches the edges.")
    if layout == "duo":
        return ("Square composition: one compact scene in the centre with empty black margins on "
                "every side; nothing touches the edges, and any ground line stays inside the margins.")
    return ("Landscape composition: the scene centred with empty black margins on every side; "
            "nothing touches the edges, and any ground line stays inside the margins.")


STORYBOARD_RULES = """\
LAYOUT (long videos only; owner direction 2026-10-16: no wide empty bands at
the sides of the 16:9 frame). Give every scene a "layout":
- "wide": one panoramic drawing composed left to right across the frame (a
  street, a production line, a timeline, a landscape, a row of things). Use it
  for most scenes.
- "duo": two drawings side by side, for a before and after, a cause and its
  effect, two rivals, or two sides of a comparison. Write the left one in
  "drawing" / "gold_element" (and "figure") and the right one in "drawing_b" /
  "gold_element_b" (and "figure_b"); the right one is drawn after the left.
  At most one scene in three is a duo.
- "single": one centred drawing, for a close-up or a large symbol.
In shorts every scene is "single". Whenever the layout is not "duo",
"drawing_b", "gold_element_b" and "figure_b" are "".
"""
