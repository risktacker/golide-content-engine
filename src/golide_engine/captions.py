from __future__ import annotations


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

