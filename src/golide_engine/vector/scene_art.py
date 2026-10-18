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
    if scene.get("picture_of"):
        return []  # a pacing shot reuses its parent scene's picture (no extra image)
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


def calm_prompt(prompt: str, part: Part) -> str:
    """The retry after a safety refusal: the same scene told as a plain symbol."""
    from ..providers.openai_media import SAFE_RETRY

    focus = part.gold or part.drawing
    return prompt.replace(part.drawing.strip(), f"a simple, friendly symbolic drawing of {focus}") + SAFE_RETRY


def fill_from_neighbours(pictures: list[Path], missing: set[Path]) -> None:
    """Give each picture the image model refused the nearest picture that exists, so
    one refused drawing never stops a video (owner rule: unattended, never blocked)."""
    import shutil

    have = [p for p in pictures if p not in missing and p.exists()]
    if not have:
        raise RuntimeError("every picture for this video was refused by the image safety filter")
    for target in missing:
        index = pictures.index(target)
        nearest = min(have, key=lambda p: (abs(pictures.index(p) - index), pictures.index(p) > index))
        shutil.copyfile(nearest, target)
        sidecar = nearest.with_suffix(".figure.json")
        if sidecar.exists():  # a copied figure keeps its exact strokes and labels
            shutil.copyfile(sidecar, target.with_suffix(".figure.json"))
        print(f"::warning title=Picture reused::{target.stem} was refused by the image safety filter; "
              f"it shows {nearest.stem} instead")
