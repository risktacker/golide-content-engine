"""The pictures a storyboard scene needs, and how each one is made.

A scene has one picture, or two for a duo (long videos). Each picture is an
exact figure drawn in code when the scene carries a figure spec (math and
physics layer), otherwise an image-model line drawing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .layouts import art_size, figure_size, second_id


@dataclass(frozen=True)
class Part:
    picture_id: str   # file stem in the illustrations folder
    drawing: str
    gold: str
    figure: str
    layout: str


def parts(scene: dict) -> list[Part]:
    layout = str(scene.get("layout") or "single")
    out = [Part(scene["id"], str(scene.get("drawing", "")), str(scene.get("gold_element", "")),
                str(scene.get("figure") or "").strip(), layout)]
    if layout == "duo":
        out.append(Part(second_id(scene["id"]), str(scene.get("drawing_b", "")),
                        str(scene.get("gold_element_b", "")), str(scene.get("figure_b") or "").strip(), layout))
    return out


def try_figure(part: Part, target: Path, format_name: str) -> bool:
    """Draw the part's exact figure; False (with a warning) when there is none or it cannot be drawn."""
    if not part.figure:
        return False
    from .figures import FigureError, render_figure

    try:
        render_figure(part.figure, target, figure_size(format_name, part.layout))
    except FigureError as exc:
        # A spec the engine cannot draw falls back to the sketch; never a failed video.
        print(f"::warning title=Figure fell back to a sketch::{part.picture_id}: {exc}")
        return False
    print(json.dumps({"status": "figure_drawn", "picture": part.picture_id, "figure": part.figure}))
    return True


def picture_size(format_name: str, part: Part) -> str:
    return art_size(format_name, part.layout)
