"""Map the scripted lines onto the owner's real recording.

Whisper gives word timings for what was actually said. The scene plan gives
the lines that were meant to be said. A token-level alignment tells us when
each scripted line actually starts, so visuals follow the voice even when the
owner skips, adds or rephrases a few words.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Any

_TOKEN = re.compile(r"[a-z0-9']+")


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower().replace("’", "'"))


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class TimedLine:
    index: int
    text: str
    emphasis: str
    visual: str
    label: str
    section: str
    start: float
    end: float
    words: list[Word] = field(default_factory=list)


def align_lines(plan: dict[str, Any], words: list[dict[str, Any]], duration: float) -> list[TimedLine]:
    lines = [line for line in plan["lines"] if str(line.get("text", "")).strip()]
    if not lines:
        raise ValueError("scene plan has no spoken lines")
    spoken = [Word(str(w.get("word", "")).strip(), float(w["start"]), float(w["end"])) for w in words]
    spoken_tokens = [(tokens(w.text) or [""])[0] for w in spoken]

    script_tokens: list[str] = []
    owner: list[int] = []
    for index, line in enumerate(lines):
        for token in tokens(str(line["text"])):
            script_tokens.append(token)
            owner.append(index)

    matcher = difflib.SequenceMatcher(None, script_tokens, spoken_tokens, autojunk=False)
    first_hit: dict[int, float] = {}
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            line_index = owner[block.a + offset]
            if line_index not in first_hit:
                first_hit[line_index] = spoken[block.b + offset].start

    starts: list[float | None] = [first_hit.get(i) for i in range(len(lines))]
    starts[0] = 0.0
    # Fill unmatched lines by spreading them evenly between known neighbours.
    known = [i for i, value in enumerate(starts) if value is not None]
    for left, right in zip(known, known[1:] + [len(lines)]):
        right_time = starts[right] if right < len(lines) else duration
        gap = right - left
        for step in range(1, gap):
            starts[left + step] = starts[left] + (right_time - starts[left]) * step / gap
    # Enforce monotonic, minimum 0.6s per line where possible.
    fixed: list[float] = []
    for value in starts:
        value = float(value or 0.0)
        if fixed and value < fixed[-1] + 0.6:
            value = fixed[-1] + 0.6
        fixed.append(min(value, max(0.0, duration - 0.6)))

    timed: list[TimedLine] = []
    for index, line in enumerate(lines):
        start = fixed[index]
        end = fixed[index + 1] if index + 1 < len(lines) else duration
        timed.append(TimedLine(
            index=index,
            text=str(line["text"]).strip(),
            emphasis=str(line.get("emphasis", "")).strip(),
            visual=str(line.get("visual", "single_glow")).strip(),
            label=str(line.get("label", "")).strip().upper()[:28],
            section=str(line.get("section", "")),
            start=start,
            end=max(end, start + 0.1),
        ))
    for word in spoken:
        for line in timed:
            if line.start - 0.05 <= word.start < line.end:
                line.words.append(word)
                break
    return timed


@dataclass
class Group:
    visual: str
    lines: list[TimedLine]

    @property
    def start(self) -> float:
        return self.lines[0].start

    @property
    def end(self) -> float:
        return self.lines[-1].end


def group_lines(lines: list[TimedLine]) -> list[Group]:
    """Consecutive lines with the same visual share one growing animation."""
    groups: list[Group] = []
    for line in lines:
        if groups and groups[-1].visual == line.visual:
            groups[-1].lines.append(line)
        else:
            groups.append(Group(line.visual, [line]))
    return groups


@dataclass
class CaptionChunk:
    words: list[Word]
    emphasis: str
    start: float
    end: float


def caption_chunks(lines: list[TimedLine], max_words: int = 7) -> list[CaptionChunk]:
    chunks: list[CaptionChunk] = []
    for line in lines:
        words = line.words or [Word(t, line.start, line.end) for t in line.text.split()]
        size = max(1, -(-len(words) // max(1, -(-len(words) // max_words))))
        parts = [words[i:i + size] for i in range(0, len(words), size)]
        for position, part in enumerate(parts):
            start = line.start if position == 0 else part[0].start
            chunks.append(CaptionChunk(part, line.emphasis, start, line.end))
        # Each chunk ends when the next one starts.
    for current, following in zip(chunks, chunks[1:]):
        current.end = following.start
    return chunks
