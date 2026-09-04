from __future__ import annotations

import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path

from .captions import scenes_to_srt
from .models import Annotation, Project
from .motion import annotation_filter, scene_filter


def _run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr[-4000:])


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])
    return float(result.stdout.strip())


def _escape_subtitle(path: Path) -> str:
    return str(path.resolve()).replace("'", "\\'").replace(":", "\\:")


def _layer_position(position: str, entrance: str) -> tuple[str, str]:
    positions = {
        "top": ("(main_w-overlay_w)/2", "main_h*0.08"),
        "center": ("(main_w-overlay_w)/2", "(main_h-overlay_h)/2"),
        "bottom": ("(main_w-overlay_w)/2", "main_h*0.82-overlay_h"),
        "left": ("main_w*0.08", "(main_h-overlay_h)/2"),
        "right": ("main_w*0.92-overlay_w", "(main_h-overlay_h)/2"),
    }
    x, y = positions[position]
    if entrance == "drift-left":
        x = f"({x})-12*sin(2*PI*t/2.8)"
    elif entrance == "drift-right":
        x = f"({x})+12*sin(2*PI*t/2.8)"
    else:
        y = f"({y})+6*sin(2*PI*t/3.2)"
    return x, y


def _render_scene_clips(project: Project, output_dir: Path) -> list[Path]:
    scene_dir = output_dir / "scenes"
    scene_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []
    for index, scene in enumerate(project.scenes):
        # Scene clips are authoritative editorial units. Do not append transition tails:
        # the previous xfade compositor accumulated timestamp rounding across a long
        # episode and silently stopped after the first few scenes. Fast hard cuts are
        # intentional for the explainer style and keep every narration beat visible.
        clip_duration = scene.duration
        destination = scene_dir / f"{index:03d}.mp4"

        # Correction runs restore the already-rendered editorial scene cache. Reuse a
        # valid clip instead of re-encoding the same motion/annotation scene again.
        # The original flagship failure was in final composition, not these clips.
        if destination.is_file() and destination.stat().st_size > 0:
            try:
                cached_duration = _probe_duration(destination)
            except Exception:
                cached_duration = 0.0
            tolerance = max(0.18, 3 / project.fps)
            if abs(cached_duration - clip_duration) <= tolerance:
                rendered.append(destination)
                continue

        command = ["ffmpeg", "-y"]
        still_image = scene.media.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        if still_image:
            command += [
                "-loop", "1", "-framerate", str(project.fps),
                "-t", f"{clip_duration:.3f}", "-i", str(scene.media),
            ]
        else:
            command += ["-stream_loop", "-1", "-t", f"{clip_duration:.3f}", "-i", str(scene.media)]
        for layer in scene.layers:
            command += ["-loop", "1", "-t", f"{clip_duration:.3f}", "-i", str(layer.media)]

        if scene.layers:
            filters = [
                "[0:v]"
                + scene_filter(
                    scene.motion, Annotation(), project.width, project.height,
                    project.fps, clip_duration, still_image=still_image,
                )
                + "[base]"
            ]
            current = "base"
            for layer_index, layer in enumerate(scene.layers, 1):
                label = f"layer{layer_index}"
                output_label = f"overlay{layer_index}"
                pixel_width = max(1, round(project.width * layer.scale))
                fade_out = max(layer.start_offset, layer.start_offset + layer.duration - 0.15)
                filters.append(
                    f"[{layer_index}:v]scale={pixel_width}:-1,format=rgba,"
                    f"fade=t=in:st={layer.start_offset:.3f}:d=0.15:alpha=1,"
                    f"fade=t=out:st={fade_out:.3f}:d=0.15:alpha=1[{label}]"
                )
                x, y = _layer_position(layer.position, layer.entrance)
                end_time = layer.start_offset + layer.duration
                filters.append(
                    f"[{current}][{label}]overlay=x='{x}':y='{y}':"
                    f"enable='between(t,{layer.start_offset:.3f},{end_time:.3f})'"
                    f"[{output_label}]"
                )
                current = output_label
            annotation = annotation_filter(scene.annotation, project.width, project.height)
            if annotation:
                filters.append(f"[{current}]{annotation}[vout]")
            else:
                filters.append(f"[{current}]null[vout]")
            command += [
                "-filter_complex", ";".join(filters), "-map", "[vout]", "-an",
                "-t", f"{clip_duration:.3f}",
            ]
        else:
            command += [
                "-an",
                "-vf", scene_filter(
                    scene.motion, scene.annotation, project.width, project.height,
                    project.fps, clip_duration, still_image=still_image,
                ),
                "-t", f"{clip_duration:.3f}",
            ]
        command += [
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", str(destination),
        ]
        _run(command)
        rendered.append(destination)
    return rendered


def _compose_scene_clips(project: Project, rendered: list[Path], destination: Path) -> None:
    if not rendered:
        raise RuntimeError("cannot compose an empty scene list")

    command = ["ffmpeg", "-y"]
    for item in rendered:
        command += ["-i", str(item)]

    filters: list[str] = []
    labels: list[str] = []
    for index, scene in enumerate(project.scenes):
        label = f"v{index}"
        filters.append(
            f"[{index}:v]fps={project.fps},trim=duration={scene.duration:.5f},"
            f"setpts=PTS-STARTPTS[{label}]"
        )
        labels.append(f"[{label}]")

    total = sum(scene.duration for scene in project.scenes)
    filters.append(
        "".join(labels)
        + f"concat=n={len(labels)}:v=1:a=0,"
        + f"trim=duration={total:.5f},setpts=PTS-STARTPTS[vout]"
    )
    command += [
        "-filter_complex", ";".join(filters), "-map", "[vout]", "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", str(destination),
    ]
    _run(command)

    # Never let the final mux hide a broken compositor by cloning one last frame for
    # minutes. A long edit must contain the complete silent visual timeline first.
    actual = _probe_duration(destination)
    tolerance = max(0.15, 3 / project.fps)
    if abs(actual - total) > tolerance:
        raise RuntimeError(
            f"scene compositor duration mismatch: expected {total:.3f}s, got {actual:.3f}s"
        )


def _generate_sfx(kind: str, output: Path) -> None:
    # Small procedural library: clearly audible in the mix, but short enough not to
    # compete with narration. Each cue is tied to a visible editorial action.
    sources = {
        "tick": (
            "sine=frequency=1450:duration=0.075:sample_rate=48000",
            "volume=0.18,afade=t=out:st=0.02:d=0.055",
        ),
        "soft-trace": (
            "sine=frequency=780:duration=0.30:sample_rate=48000",
            "highpass=f=500,lowpass=f=4200,volume=0.13,afade=t=in:st=0:d=0.04,afade=t=out:st=0.12:d=0.18",
        ),
        "paper": (
            "anoisesrc=color=pink:duration=0.20:sample_rate=48000",
            "highpass=f=900,lowpass=f=6200,volume=0.12,afade=t=in:st=0:d=0.02,afade=t=out:st=0.05:d=0.15",
        ),
        "swipe": (
            "anoisesrc=color=white:duration=0.24:sample_rate=48000",
            "highpass=f=1100,lowpass=f=7500,volume=0.09,afade=t=in:st=0:d=0.05,afade=t=out:st=0.10:d=0.14",
        ),
        "impact": (
            "sine=frequency=82:duration=0.30:sample_rate=48000",
            "volume=0.24,lowpass=f=180,afade=t=out:st=0.035:d=0.265",
        ),
    }
    source, audio_filter = sources[kind]
    output.parent.mkdir(parents=True, exist_ok=True)
    _run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", source,
        "-af", audio_filter + ",pan=stereo|c0=c0|c1=c0",
        "-ar", "48000", "-c:a", "pcm_s16le", str(output),
    ])


def _build_sfx_track(project: Project, output_dir: Path) -> tuple[Path | None, int]:
    events = []
    cursor = 0.0
    last_high_salience = -10.0
    for scene in project.scenes:
        cue = scene.motion.audio_cue
        event_time = cursor + min(max(scene.annotation.start_offset, 0.03), scene.duration * 0.5)
        if cue == "impact" and event_time - last_high_salience < 2.5:
            cue = "tick"
        if cue != "none":
            events.append((event_time, cue))
            if cue == "impact":
                last_high_salience = event_time
        cursor += scene.duration
    if not events:
        return None, 0

    library = output_dir / "procedural-sfx"
    for cue in sorted({cue for _, cue in events}):
        _generate_sfx(cue, library / f"{cue}.wav")

    track = output_dir / "sfx-track.wav"
    command = ["ffmpeg", "-y"]
    for _, cue in events:
        command += ["-i", str(library / f"{cue}.wav")]
    filters = []
    labels = []
    for index, (when, _) in enumerate(events):
        label = f"s{index}"
        delay = round(when * 1000)
        filters.append(f"[{index}:a]adelay={delay}|{delay}[{label}]")
        labels.append(f"[{label}]")
    total = sum(scene.duration for scene in project.scenes)
    filters.append(
        "".join(labels)
        + f"amix=inputs={len(labels)}:duration=longest:normalize=0,"
        + f"apad=pad_dur={total:.3f},atrim=duration={total:.3f}[sfx]"
    )
    command += [
        "-filter_complex", ";".join(filters), "-map", "[sfx]",
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(track),
    ]
    _run(command)
    return track, len(events)


def render(project: Project, root: Path) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is required but was not found on PATH")
    if not shutil.which("ffprobe"):
        raise RuntimeError("FFprobe is required but was not found on PATH")

    output_dir = root / "build" / project.id
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered = _render_scene_clips(project, output_dir)
    silent = output_dir / "silent.mp4"
    _compose_scene_clips(project, rendered, silent)

    visual_srt = output_dir / "visual-labels.srt"
    visual_srt.write_text(
        scenes_to_srt([
            {"duration": scene.duration, "caption": scene.caption}
            for scene in project.scenes
        ]),
        encoding="utf-8",
    )
    video_filters = []
    if visual_srt.read_text(encoding="utf-8").strip():
        video_filters.append(
            "subtitles='{}':force_style='FontName=DejaVu Sans,FontSize=18,Bold=1,"
            "PrimaryColour=&H00F5F1E8,OutlineColour=&H00111B36,Outline=2,"
            "Shadow=0,Alignment=8,MarginV=250'".format(_escape_subtitle(visual_srt))
        )
    if project.spoken_captions:
        video_filters.append(
            "subtitles='{}':force_style='FontName=DejaVu Sans,FontSize=12,Bold=1,"
            "PrimaryColour=&H00F5F1E8,OutlineColour=&H00111B36,Outline=2,"
            "Shadow=0,Alignment=2,MarginV=120'".format(_escape_subtitle(project.spoken_captions))
        )

    sfx_track, sfx_events = _build_sfx_track(project, output_dir)
    final = output_dir / "video.mp4"
    command = ["ffmpeg", "-y", "-i", str(silent), "-i", str(project.narration)]
    music_index = None
    sfx_index = None
    if project.music:
        music_index = 2
        command += ["-stream_loop", "-1", "-i", str(project.music)]
    if sfx_track:
        sfx_index = 3 if project.music else 2
        command += ["-i", str(sfx_track)]

    total_duration = sum(scene.duration for scene in project.scenes)
    video_chain = ",".join(video_filters) if video_filters else "null"
    # Only permit a tiny two-frame pad for codec rounding. The previous full-duration
    # tpad concealed a 13-second compositor output by freezing its last frame to 4:45.
    rounding_pad = max(0.05, 2 / project.fps)
    filters = [
        f"[0:v]{video_chain},tpad=stop_mode=clone:stop_duration={rounding_pad:.3f},"
        f"trim=duration={total_duration:.3f},setpts=PTS-STARTPTS[v]"
    ]
    if music_index is not None:
        # Voice first. Even an old manifest that asks for a louder bed is clamped.
        music_volume = min(project.music_volume, 0.03)
        filters.append(f"[{music_index}:a]volume={music_volume}[music]")
        if project.music_ducking:
            filters.append(
                "[music][1:a]sidechaincompress=threshold=0.012:ratio=12:"
                "attack=12:release=420:makeup=1[ducked]"
            )
            filters.append("[1:a][ducked]amix=inputs=2:duration=first:normalize=0[base]")
        else:
            filters.append("[1:a][music]amix=inputs=2:duration=first:normalize=0[base]")
    else:
        filters.append("[1:a]anull[base]")
    if sfx_index is not None:
        filters.append(f"[base][{sfx_index}:a]amix=inputs=2:duration=first:normalize=0[mixed]")
    else:
        filters.append("[base]anull[mixed]")
    filters.append(
        f"[mixed]loudnorm=I=-16:TP=-1.5:LRA=11,"
        f"apad=pad_dur={total_duration:.3f},"
        f"atrim=duration={total_duration:.3f}[a]"
    )

    command += [
        "-filter_complex", ";".join(filters), "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-t", f"{total_duration:.3f}", str(final),
    ]
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
        "music_volume_requested": project.music_volume,
        "music_volume_effective": min(project.music_volume, 0.03),
        "dual_caption_tracks": bool(project.spoken_captions),
        "scene_compositor": "hard-cut-concat-v2",
        "motion_recipes": dict(Counter(scene.motion.type for scene in project.scenes)),
        "transition_recipes": dict(Counter(scene.motion.transition for scene in project.scenes)),
        "annotations": sum(scene.annotation.kind != "none" for scene in project.scenes),
        "procedural_sfx_events": sfx_events,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return final
