"""The whole 3D path for one video: director -> blueprints -> shots -> render -> clips.
Any single failure drops that shot and the video carries on illustrated."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from . import blueprint, catalog, director

CONFIG = Path(__file__).resolve().parents[1] / "config.json"


def settings() -> dict[str, Any]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def enabled() -> bool:
    return bool(settings().get("enabled"))


def blender_python() -> str:
    return os.environ.get("WORLD3D_PYTHON", sys.executable)


def render_shot(shot_path: str, folder: Path, quality: str, python: str | None = None) -> None:
    python = python or blender_python()
    tools = catalog.WORLD3D
    subprocess.run([python, str(tools / "render_shot.py"), shot_path, "--out", str(folder), "--quality", quality], check=True)
    subprocess.run([python, str(tools / "post.py"), str(folder)], check=True)


def run(folder: Path, format_name: str, lines: list[str], times: list[tuple[float, float]],
        words: list[dict[str, Any]], facts: str, text: Any, record: Callable[[str, Any], None],
        render: Callable[[str, Path, str], None] = render_shot) -> list[dict[str, Any]]:
    cfg = settings()
    max_shots = cfg["max_shots"][format_name]
    max_seconds = cfg["max_seconds"][format_name]
    output = text.generate_json(director.instructions(format_name, max_shots, max_seconds),
                                f"{facts}\nLINES\n{director.rows(lines, times)}", director.PLAN_SCHEMA,
                                max_output_tokens=4000)
    record("world3d-director", output)
    shots = director.accepted(output.value["shots"], times, max_shots, max_seconds)
    blueprints = folder / "blueprints"
    clips: list[dict[str, Any]] = []
    for index, plan in enumerate(shots):
        try:
            path, used = blueprint.obtain(plan["subject"], facts, text, blueprints)
            for item in used:
                record("world3d-blueprint", item)
            shot = director.compile_shot(plan, json.loads(path.read_text(encoding="utf-8")), path.parent.name,
                                         str(path.parent.parent), plan["start"], plan["end"], words,
                                         vertical=format_name == "short")
            shot_path = director.save_shots([shot], folder / f"shot{index}")[0]
            frames = folder / f"shot{index}" / "frames"
            render(shot_path, frames, cfg["quality"])
            clips.append({"start": plan["start"], "end": plan["end"], "frames": str(frames / "final"),
                          "fps": shot["fps"], "subject": plan["subject"], "focus": plan.get("focus", "")})
        except Exception as error:  # noqa: BLE001 - one shot must never stop a video
            print(json.dumps({"status": "world3d_shot_skipped", "subject": plan["subject"], "reason": str(error)[:300]}))
    return clips
