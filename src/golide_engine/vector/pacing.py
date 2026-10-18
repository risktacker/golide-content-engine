"""Picture pacing (owner direction 2026-10-18).

"I'm entering with energy and catching voices but the visuals are not fast...
one block spending 20-30 seconds." A viewer decides in the first seconds, so:

* HOOK WINDOW (shorts: first 30 s, long videos: first 60 s): a new picture every
  few seconds, close to one per spoken line.
* After the hook the pace stays brisk: no picture holds longer than BODY_MAX.
* The pen still draws every picture, but at the speed of the voice: a fast,
  dense line gets a fast pen (see ``reveal_seconds``).

The storyboard is told these targets with each line's real time. Anything it
still leaves too long is split here at line boundaries into extra SHOTS of the
same picture (a zoom onto another part of the drawing), so pacing never costs
an extra image.
"""

from __future__ import annotations

HOOK_SECONDS = {"short": 30.0, "long": 60.0}
HOOK_MAX = {"short": 3.6, "long": 5.0}     # longest a picture may hold in the hook
BODY_MAX = {"short": 8.0, "long": 14.0}    # ... and after it
TARGET = {"short": (3.0, 6.5), "long": (4.0, 11.0)}  # seconds per picture: hook, body
MAX_PICTURES = {"short": 16, "long": 34}   # image budget (about $0.015 each)


def scene_range(format_name: str, duration: float) -> tuple[int, int]:
    """How many scenes to ask the storyboard for, from the recording's length."""
    hook = min(duration, HOOK_SECONDS.get(format_name, 30.0))
    per_hook, per_body = TARGET.get(format_name, TARGET["short"])
    ideal = hook / per_hook + max(0.0, duration - hook) / per_body
    high = min(MAX_PICTURES.get(format_name, 16), max(4, round(ideal * 1.15)))
    low = max(3, min(high, round(ideal * 0.85)))
    return low, high


def limit_for(format_name: str, start: float) -> float:
    in_hook = start < HOOK_SECONDS.get(format_name, 30.0)
    return (HOOK_MAX if in_hook else BODY_MAX).get(format_name, 8.0)


def pace_scenes(scenes: list[dict], line_times: list[tuple[float, float]], format_name: str) -> list[dict]:
    """Split any scene that holds too long into shots of the same picture.

    ``line_times[i]`` is (start, end) of spoken line i. A split never breaks a
    line; the extra parts carry ``picture_of`` (the scene whose picture they
    reuse) and ``shot`` (1, 2, ... which part of the drawing to frame).
    """
    out: list[dict] = []
    for scene in scenes:
        first, last = int(scene["first_line"]), int(scene["last_line"])
        parts: list[tuple[int, int]] = []
        start_line = first
        for index in range(first, last + 1):
            span_start = line_times[start_line][0]
            if index > start_line and line_times[index][1] - span_start > limit_for(format_name, span_start):
                parts.append((start_line, index - 1))
                start_line = index
        parts.append((start_line, last))
        for k, (a, b) in enumerate(parts):
            piece = {**scene, "first_line": a, "last_line": b}
            if k:
                piece["id"] = f"{scene['id']}-s{k}"
                piece["picture_of"] = scene["id"]
                piece["shot"] = k
            out.append(piece)
    return out


def reveal_seconds(span: float, words: int, in_hook: bool) -> float:
    """How long the pen takes to draw a picture: quick in the hook, and quicker
    when the voice is fast (more words per second)."""
    rate = words / max(0.5, span)                 # words per second in this scene
    voice = min(1.35, max(0.6, 2.6 / max(0.5, rate)))  # 2.6 w/s is a normal pace
    if in_hook:
        base = min(max(0.45 * span, 0.9), 2.4)
    else:
        base = min(max(0.55 * span, 1.6), 7.0)
    return min(span, base * voice)


def storyboard_rules(format_name: str, duration: float) -> str:
    """The pacing paragraph of the storyboard instructions."""
    hook = HOOK_SECONDS.get(format_name, 30.0)
    per_hook, per_body = TARGET.get(format_name, TARGET["short"])
    return f"""\
PACING (owner direction 2026-10-18: the opening must move as fast as the voice).
Each line shows its start time in seconds, like [12.4s]. The recording is
{duration:.0f} seconds long.
- HOOK: in the first {hook:.0f} seconds start a new scene every {per_hook:.0f} seconds or
  so, close to one scene per line. Never hold one picture longer than
  {HOOK_MAX.get(format_name, 3.6):.0f} seconds inside the hook.
- After the hook, a new scene every {per_body:.0f} seconds or so; never longer than
  {BODY_MAX.get(format_name, 8.0):.0f} seconds on one picture.
- Hook pictures are simple and bold (one big object or symbol), so they read
  instantly; the richer scenes come after the hook.
"""
