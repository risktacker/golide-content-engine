from __future__ import annotations

from typing import Any


def _timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def scenes_to_srt(scenes: list[dict]) -> str:
    cursor = 0.0
    blocks = []
    for index, scene in enumerate(scenes, 1):
        duration = float(scene["duration"])
        caption = str(scene.get("caption", "")).strip()
        if caption:
            blocks.append(f"{index}\n{_timestamp(cursor)} --> {_timestamp(cursor + duration)}\n{caption}\n")
        cursor += duration
    return "\n".join(blocks)


def words_to_srt(words: list[dict[str, Any]], min_words: int = 2, max_words: int = 5, max_seconds: float = 1.8) -> str:
    """Group timestamped spoken words into short, readable caption phrases."""
    if min_words < 1 or max_words < min_words:
        raise ValueError("invalid word grouping")
    normalized = []
    for raw in words:
        word = str(raw["word"]).strip()
        start, end = float(raw["start"]), float(raw["end"])
        if not word or start < 0 or end <= start:
            raise ValueError(f"invalid timed word: {raw!r}")
        normalized.append({"word": word, "start": start, "end": end})
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for item in normalized:
        current.append(item)
        elapsed = current[-1]["end"] - current[0]["start"]
        punctuation = current[-1]["word"].endswith((".", "?", "!", ",", ";", ":"))
        if len(current) >= max_words or (len(current) >= min_words and (elapsed >= max_seconds or punctuation)):
            groups.append(current)
            current = []
    if current:
        if groups and len(current) < min_words:
            groups[-1].extend(current)
        else:
            groups.append(current)
    blocks = []
    for index, group in enumerate(groups, 1):
        caption = " ".join(item["word"] for item in group)
        blocks.append(f"{index}\n{_timestamp(group[0]['start'])} --> {_timestamp(group[-1]['end'])}\n{caption}\n")
    return "\n".join(blocks)
