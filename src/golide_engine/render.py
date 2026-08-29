from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .models import Project
from .captions import scenes_to_srt


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def _escape_concat(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def _escape_subtitle(path: Path) -> str:
    return str(path.resolve()).replace("'", "\\'").replace(":", "\\:")


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

    visual_srt = output_dir / "visual-labels.srt"
    visual_srt.write_text(
        scenes_to_srt([
            {"duration": scene.duration, "caption": scene.caption}
            for scene in project.scenes
        ]),
        encoding="utf-8",
    )
    video_filters = [
        "subtitles='{}':force_style='FontName=DejaVu Sans,FontSize=18,Bold=1,"
        "PrimaryColour=&H00F5F1E8,OutlineColour=&H00111B36,Outline=2,"
        "Shadow=0,Alignment=8,MarginV=250'".format(_escape_subtitle(visual_srt))
    ]
    if project.spoken_captions:
        video_filters.append(
            "subtitles='{}':force_style='FontName=DejaVu Sans,FontSize=12,Bold=1,"
            "PrimaryColour=&H00F5F1E8,OutlineColour=&H00111B36,Outline=2,"
            "Shadow=0,Alignment=2,MarginV=120'".format(_escape_subtitle(project.spoken_captions))
        )

    final = output_dir / "video.mp4"
    command = ["ffmpeg", "-y", "-i", str(silent), "-i", str(project.narration)]
    if project.music:
        if project.music_ducking:
            audio_filter = (
                f"[2:a]volume={project.music_volume}[music];"
                "[music][1:a]sidechaincompress=threshold=0.02:ratio=8:"
                "attack=20:release=350[ducked];"
                "[1:a][ducked]amix=inputs=2:duration=first:normalize=0[a]"
            )
        else:
            audio_filter = (
                f"[2:a]volume={project.music_volume}[music];"
                "[1:a][music]amix=inputs=2:duration=first:normalize=0[a]"
            )
        command += ["-stream_loop", "-1", "-i", str(project.music)]
        filter_complex = f"[0:v]{','.join(video_filters)}[v];{audio_filter}"
        command += ["-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]"]
    else:
        command += ["-vf", ",".join(video_filters), "-map", "0:v", "-map", "1:a"]
    command += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-shortest", str(final)]
    _run(command)

    metadata = {
        "id": project.id,
        "title": project.title,
        "format": project.format,
        "duration": sum(x.duration for x in project.scenes),
        "max_cost_usd": project.max_cost_usd,
        "publish_approved": project.approved,
        "music_source": project.music_source,
        "music_license": project.music_license,
        "dual_caption_tracks": bool(project.spoken_captions),
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return final
