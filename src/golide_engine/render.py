from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .models import Project


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def _escape_concat(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def render(project: Project, root: Path) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is required but was not found on PATH")

    output_dir = root / "build" / project.id
    scene_dir = output_dir / "scenes"
    scene_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []

    for index, scene in enumerate(project.scenes):
        destination = scene_dir / f"{index:03d}.mp4"
        vf = (
            f"scale={project.width}:{project.height}:force_original_aspect_ratio=increase,"
            f"crop={project.width}:{project.height},fps={project.fps},format=yuv420p"
        )
        command = ["ffmpeg", "-y"]
        if scene.media.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            command += ["-loop", "1", "-t", str(scene.duration), "-i", str(scene.media)]
        else:
            command += ["-stream_loop", "-1", "-t", str(scene.duration), "-i", str(scene.media)]
        command += ["-an", "-vf", vf, "-c:v", "libx264", "-preset", "medium", str(destination)]
        _run(command)
        rendered.append(destination)

    concat = output_dir / "concat.txt"
    concat.write_text("".join(f"file '{_escape_concat(x)}'\n" for x in rendered), encoding="utf-8")
    silent = output_dir / "silent.mp4"
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(silent)])

    final = output_dir / "video.mp4"
    command = ["ffmpeg", "-y", "-i", str(silent), "-i", str(project.narration)]
    if project.music:
        command += ["-i", str(project.music), "-filter_complex", "[2:a]volume=0.10[m];[1:a][m]amix=inputs=2:duration=first[a]", "-map", "0:v", "-map", "[a]"]
    else:
        command += ["-map", "0:v", "-map", "1:a"]
    command += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(final)]
    _run(command)

    metadata = {
        "id": project.id,
        "title": project.title,
        "format": project.format,
        "duration": sum(x.duration for x in project.scenes),
        "max_cost_usd": project.max_cost_usd,
        "publish_approved": project.approved,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return final

