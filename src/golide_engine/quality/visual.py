from __future__ import annotations

import json
import subprocess
from pathlib import Path


def probe_video(path: str | Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])
    return json.loads(result.stdout)


def check_video(path: str | Path, format_name: str, policy: dict) -> list[str]:
    data = probe_video(path)
    stream = next((item for item in data["streams"] if item.get("codec_type") == "video"), None)
    audio = next((item for item in data["streams"] if item.get("codec_type") == "audio"), None)
    if not stream:
        return ["no video stream"]
    expected = policy["visual"][f"{format_name}_dimensions"]
    failures = []
    if [int(stream["width"]), int(stream["height"])] != expected:
        failures.append(f"dimensions must be {expected[0]}x{expected[1]}")
    rate = stream.get("avg_frame_rate", "0/1").split("/")
    fps = float(rate[0]) / float(rate[1]) if float(rate[1]) else 0
    if fps < float(policy["visual"]["minimum_fps"]):
        failures.append(f"frame rate {fps:.2f} below policy")
    if not audio:
        failures.append("no audio stream")
    else:
        video_duration = float(data.get("format", {}).get("duration", 0) or 0)
        audio_duration = float(audio.get("duration", video_duration) or video_duration)
        tolerance = float(policy["visual"]["duration_tolerance_seconds"])
        if abs(video_duration - audio_duration) > tolerance:
            failures.append(f"audio/video duration mismatch exceeds {tolerance}s")
    return failures


def check_safe_zones(storyboard: dict, policy: dict) -> list[str]:
    margin = float(policy["visual"]["safe_margin_percent"]) / 100
    failures = []
    for scene in storyboard.get("scenes", []):
        for subject in scene.get("subject_bounds", []):
            x, y, width, height = (float(subject[key]) for key in ("x", "y", "width", "height"))
            if x < margin or y < margin or x + width > 1 - margin or y + height > 1 - margin:
                failures.append(f"scene {scene.get('id')} subject outside {margin:.0%} safe zone")
    return failures


def normalize_thumbnail(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(source), "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720", "-frames:v", "1", str(target)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])


def check_thumbnail(path: Path) -> list[str]:
    data = probe_video(path)
    stream = next((item for item in data["streams"] if item.get("codec_type") == "video"), None)
    if not stream or [int(stream["width"]), int(stream["height"])] != [1280, 720]:
        return ["thumbnail must be exactly 1280x720"]
    return []
