"""Chapters of a long video, timed from the owner's real recording.

A long script carries ``chapters`` (number + title) and each line names its
chapter. Once the recording is aligned we know when each chapter starts, which
drives two things: the chapter card drawn in the video, and the YouTube
chapter list in the description (real timestamps, never guessed).

Scripts without chapters fall back to their structural sections so a long
video always has honest chapter timestamps.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

SECTION_TITLES = {
    "claim": "The idea",
    "proof": "An example",
    "pattern": "The pattern",
    "cost": "The cost",
    "reframe": "Remember this",
    "cta": "What to do",
}

MIN_CHAPTER_SECONDS = 10.0


@dataclass(frozen=True)
class ChapterMark:
    start: float
    number: str  # "01".."NN", or "" for the intro and close
    title: str

    @property
    def tag(self) -> str:
        return f"{self.number}  {self.title}".strip().upper() if self.number else ""


def chapter_marks(plan: dict[str, Any], timed_lines: Sequence[Any]) -> list[ChapterMark]:
    spoken = [line for line in plan.get("lines", []) if str(line.get("text", "")).strip()]
    chapters = plan.get("chapters") or []
    marks: list[ChapterMark] = []
    previous: object = object()
    for timed in timed_lines:
        source = spoken[timed.index] if timed.index < len(spoken) else {}
        if chapters:
            key = source.get("chapter")
            if not isinstance(key, int) or not 0 <= key < len(chapters):
                continue
            chapter = chapters[key]
            number, title = str(chapter.get("number", "")).strip(), str(chapter.get("title", "")).strip()
        else:
            key = source.get("section", timed.section)
            number, title = "", SECTION_TITLES.get(str(key), str(key).title())
        if key != previous:
            marks.append(ChapterMark(float(timed.start), number, title))
            previous = key
    return marks


def line_chapters(plan: dict[str, Any]) -> list[int | None]:
    """Chapter index of every spoken line (None when the plan has no chapters)."""
    spoken = [line for line in plan.get("lines", []) if str(line.get("text", "")).strip()]
    count = len(plan.get("chapters") or [])
    return [line.get("chapter") if isinstance(line.get("chapter"), int) and 0 <= line["chapter"] < count else None
            for line in spoken]


def _stamp(seconds: float) -> str:
    whole = int(seconds)
    return f"{whole // 60}:{whole % 60:02d}"


def youtube_chapters(marks: Sequence[ChapterMark], duration: float) -> list[str]:
    """YouTube rules: starts at 0:00, at least three, each at least 10 seconds."""
    kept: list[ChapterMark] = []
    for mark in marks:
        start = 0.0 if not kept else float(int(mark.start))
        if kept and start - kept[-1].start < MIN_CHAPTER_SECONDS:
            continue  # too short; it folds into the previous chapter
        if duration - start < MIN_CHAPTER_SECONDS:
            break
        kept.append(ChapterMark(start, mark.number, mark.title or "Intro"))
    if len(kept) < 3:
        return []
    return [f"{_stamp(mark.start)} {mark.title}" for mark in kept]


_TIMESTAMP_LINE = re.compile(r"^\s*\(?\d{1,2}:\d{2}(?::\d{2})?\)?\s*[-–:]?\s*\S")


def with_chapters(description: str, chapters: list[str]) -> str:
    """Replace any guessed timestamps in a description with the real chapters."""
    kept = [row for row in description.splitlines() if not _TIMESTAMP_LINE.match(row)]
    cleaned: list[str] = []
    for row in kept:  # drop a dangling "Chapters" heading left behind
        if row.strip().rstrip(":").lower() in {"chapters", "timestamps"}:
            continue
        cleaned.append(row)
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned)).strip()
    if not chapters:
        return body
    block = "Chapters\n" + "\n".join(chapters)
    # Hashtags stay at the very end of the description.
    lines = body.splitlines()
    tail: list[str] = []
    while lines and lines[-1].strip().startswith("#"):
        tail.insert(0, lines.pop())
    head = "\n".join(lines).rstrip()
    return head + "\n\n" + block + ("\n\n" + "\n".join(tail) if tail else "")
