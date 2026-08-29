from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .captions import scenes_to_srt


ALIASES = {
    "chip-cutaway": "charge-bloom",
    "bit-cell": "healthy-chip-wrong-data",
}


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def render_animatic(storyboard_path: Path, asset_dir: Path, output: Path) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is required")
    board = json.loads(storyboard_path.read_text(encoding="utf-8"))
    scenes = board["scenes"]
    output.parent.mkdir(parents=True, exist_ok=True)
    scene_dir = output.parent / "animatic-scenes"
    scene_dir.mkdir(exist_ok=True)
    clips: list[Path] = []

    for index, scene in enumerate(scenes):
        asset_name = ALIASES.get(scene["asset"], scene["asset"])
        asset = asset_dir / f"{asset_name}.webp"
        if not asset.exists():
            raise FileNotFoundError(asset)
        clip = scene_dir / f"{index:03d}.mp4"
        frames = round(float(scene["duration"]) * 30)
        if index % 2:
            zoom = "max(1.08-on*0.0008,1.0)"
        else:
            zoom = "min(1.0+on*0.0008,1.08)"
        vf = (
            "scale=1200:2134:force_original_aspect_ratio=increase,"
            "crop=1200:2134,"
            f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s=1080x1920:fps=30,format=yuv420p"
        )
        _run([
            "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(asset),
            "-vf", vf, "-frames:v", str(frames), "-an", "-c:v", "libx264",
            "-preset", "medium", "-crf", "19", str(clip),
        ])
        clips.append(clip)

    concat = output.parent / "animatic-concat.txt"
    concat.write_text("".join(f"file '{clip.resolve()}'\n" for clip in clips), encoding="utf-8")
    raw = output.parent / "animatic-raw.mp4"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(raw)])

    srt = output.parent / "captions-draft.srt"
    srt.write_text(scenes_to_srt(scenes), encoding="utf-8")
    subtitle_path = str(srt.resolve()).replace("'", "\\'").replace(":", "\\:")
    style = "FontName=DejaVu Sans,FontSize=18,Bold=1,PrimaryColour=&H00F5F1E8,OutlineColour=&H00111B36,BorderStyle=1,Outline=3,Shadow=0,Alignment=2,MarginV=190"
    _run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
        "-vf", f"subtitles='{subtitle_path}':force_style='{style}'",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19", str(output),
    ])
    return output

