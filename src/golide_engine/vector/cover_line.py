"""The one line that sells the video (owner direction 2026-10-25).

The opening card's line ("The Robot Wasn't the Story", "Five Percent Is Not Public
Money") is also the thumbnail text. It is a 3 to 6 word claim or question about THIS
story that adds to the title, never repeats it, never falls back on the worn "Who ___?"
shape, never opens like a recent line, and a short and a long on the same topic never
share one. The lines used are kept in data/thumbnail-lines.json (committed with each run).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

LOG = Path("data") / "thumbnail-lines.json"
KEEP = 40
STOP = {"the", "a", "an", "of", "to", "in", "on", "and", "or", "is", "it", "its", "it's", "for", "at",
        "by", "with", "this", "that", "be", "are", "was", "can", "really", "just", "how", "why", "what"}


def _words(text: str) -> list[str]:
    return [w for w in re.sub(r"[^a-z0-9' ]", " ", text.lower().replace("’", "'")).split() if w]


def _opening(text: str) -> str:
    return " ".join(_words(text)[:2])


def recent_lines(root: Path, production_id: str, limit: int = 10) -> list[dict]:
    try:
        rows = json.loads((root / LOG).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [r for r in rows if r.get("production_id") != production_id][-limit:]


def line_problems(text: str, title: str, recent: list[dict], topic: str = "") -> list[str]:
    words = _words(text)
    problems: list[str] = []
    if not 3 <= len(words) <= 6:
        problems.append(f"the line has {len(words)} words; use 3 to 6")
    if words[:1] == ["who"]:
        problems.append('never the "Who ...?" shape; make a claim or a sharper question about this story')
    title_words = {w for w in _words(title) if w not in STOP}
    own = [w for w in words if w not in STOP]
    shared = [w for w in own if w in title_words]
    if own and len(shared) * 2 > len(own):
        problems.append("the line repeats the title (" + ", ".join(shared) + "); say what the title does not")
    if " ".join(words) == " ".join(_words(title)):
        problems.append("the line is the title")
    opening = _opening(text)
    for row in recent:
        if opening and _opening(row.get("text", "")) == opening:
            problems.append(f'a recent video already opened with "{opening}"; open differently')
            break
    for row in recent:
        if topic and row.get("topic") == topic and _words(row.get("text", "")) == words:
            problems.append("the other video on this topic already uses this line; write a different one")
            break
    return problems


def record_line(root: Path, production_id: str, format_name: str, title: str, text: str, topic: str = "") -> None:
    path = root / LOG
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rows = []
    rows = [r for r in rows if r.get("production_id") != production_id]
    rows.append({"production_id": production_id, "format": format_name, "title": title, "text": text,
                 "topic": topic, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows[-KEEP:], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def recent_block(recent: list[dict]) -> str:
    if not recent:
        return ""
    return ("RECENT THUMBNAIL LINES (never open the same way, never reuse one):\n"
            + "\n".join(f"- {r.get('text', '')}" for r in recent) + "\n")
