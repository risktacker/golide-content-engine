"""What the channel has already done (owner direction 2026-11-05).

Never model the same source video twice (the same channel is fine, a different video), and
never publish the same title twice. The record is the production queue in the repo: every
spec the engine ever made stays there (renamed .completed / .topic-rejected), with its title
and the video it modelled.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

QUEUE = Path("production-queue")


def video_key(url: str) -> str:
    """The YouTube video id in a watch, shorts or youtu.be link; else the link itself."""
    found = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url or "")
    return found.group(1) if found else (url or "").strip()


def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def _specs(exclude_id: str, queue: Path):
    for path in sorted(queue.glob("*.json")):
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(spec, dict) and spec.get("id") != exclude_id:
            yield spec


def used_source_videos(exclude_id: str, queue: Path = QUEUE) -> set[str]:
    return {video_key((s.get("source_breakout") or {}).get("url", ""))
            for s in _specs(exclude_id, queue) if (s.get("source_breakout") or {}).get("url")}


def used_titles(exclude_id: str, queue: Path = QUEUE) -> set[str]:
    """Titles of videos that were actually made (a rejected topic's title was never used)."""
    keys = set()
    for spec in _specs(exclude_id, queue):
        if spec.get("platform_demand", {}).get("verdict") == "pass":
            keys |= {title_key(spec.get(k, "")) for k in ("title", "model_title") if spec.get(k)}
    return keys - {""}
