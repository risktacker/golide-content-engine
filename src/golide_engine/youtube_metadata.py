from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class YouTubeMetadataError(ValueError):
    pass


_TIMESTAMP = re.compile(r"^(?:(\d+):)?([0-5]?\d):([0-5]\d)\s+\S")


def load_metadata_policy(path: str | Path) -> dict[str, Any]:
    policy = json.loads(Path(path).read_text(encoding="utf-8"))
    if policy.get("titles", {}).get("short", {}).get("hashtags_in_title") is not False:
        raise YouTubeMetadataError("Short titles must not default to hashtags")
    if policy.get("upload_defaults", {}).get("video_language") != "en":
        raise YouTubeMetadataError("The current production language must remain English")
    return policy


def _seconds(timestamp: str) -> int:
    pieces = [int(piece) for piece in timestamp.split(":" )]
    if len(pieces) == 2:
        return pieces[0] * 60 + pieces[1]
    return pieces[0] * 3600 + pieces[1] * 60 + pieces[2]


def validate_chapters(lines: list[str]) -> None:
    stamps: list[int] = []
    for line in lines:
        match = _TIMESTAMP.match(line.strip())
        if not match:
            raise YouTubeMetadataError(f"Invalid chapter: {line}")
        stamp = line.strip().split(maxsplit=1)[0]
        stamps.append(_seconds(stamp))
    if len(stamps) < 3:
        raise YouTubeMetadataError("At least three chapters are required")
    if stamps[0] != 0:
        raise YouTubeMetadataError("The first chapter must start at 00:00")
    if stamps != sorted(set(stamps)):
        raise YouTubeMetadataError("Chapters must be unique and ascending")
    if any(b - a < 10 for a, b in zip(stamps, stamps[1:])):
        raise YouTubeMetadataError("Each chapter must last at least 10 seconds")


def validate_upload_metadata(metadata: dict[str, Any], policy: dict[str, Any]) -> None:
    fmt = metadata.get("format")
    if fmt not in {"short", "long"}:
        raise YouTubeMetadataError("format must be short or long")
    title = str(metadata.get("title", "")).strip()
    description = str(metadata.get("description", "")).strip()
    if not title or len(title) > 100:
        raise YouTubeMetadataError("title is required and cannot exceed 100 characters")
    if "#" in title:
        raise YouTubeMetadataError("hashtags belong at the end of the description, not the title")
    if len(description) > 5000:
        raise YouTubeMetadataError("description cannot exceed 5,000 characters")
    tags = [str(tag).strip() for tag in metadata.get("tags", []) if str(tag).strip()]
    if sum(len(tag) for tag in tags) + max(0, len(tags) - 1) > 500:
        raise YouTubeMetadataError("tags exceed YouTube's 500-character total")
    if len(tags) != len({tag.casefold() for tag in tags}):
        raise YouTubeMetadataError("tags must be unique")
    if metadata.get("video_language") != policy["upload_defaults"]["video_language"]:
        raise YouTubeMetadataError("video language does not match channel policy")
    if metadata.get("recording_location") and not metadata.get("location_is_material"):
        raise YouTubeMetadataError("do not use recording location as demographic targeting")
    altered = metadata.get("altered_content")
    if altered not in {True, False}:
        raise YouTubeMetadataError("altered_content must be explicitly reviewed")
    chapters = metadata.get("chapters", [])
    if fmt == "long":
        validate_chapters(chapters)
    elif chapters:
        raise YouTubeMetadataError("Shorts do not use manual chapters")
