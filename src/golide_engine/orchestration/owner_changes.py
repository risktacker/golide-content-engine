"""Two things the owner does to a script in Studio before it is read (owner 2026-11-10).

Replace script: he pastes a YouTube link. That video becomes today's model and its subject today's
title; the engine researches the subject from other sources and writes a new script, the way it
does every day. Used rarely, when the day's script is not right.

Edit script: he edits the words in Studio's editor and taps Done. His words are the script from then
on; the pictures and gold words are picked again for them.

Both apply only while the recording has not been processed, never to a video already built.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# What a new script makes stale: the research, the script, its model transcripts, and the pause.
REPLACE_FILES = ("research.json", "script.txt", "scene-plan.json", "model-scripts.json", "spoken-pass.json",
                 "rescript-done.txt", "script-edit.txt")
REPLACE_STAGES = ("research", "script")
REPLACE_DONE = "replace-done.txt"
EDIT_DONE = "script-edit.txt"


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", str(text).lower()))


def replace_pending(spec: dict[str, Any], work: Path) -> bool:
    ask = spec.get("replace_model") or {}
    if not ask.get("url") or (work / "timed-words-owner.json").exists():
        return False
    done = work / REPLACE_DONE
    return not done.exists() or done.read_text(encoding="utf-8").strip() != str(ask.get("requested_at", ""))


def model_from_link(youtube: Any, url: str) -> dict[str, Any]:
    """The pasted video as the engine's model (title, channel, length, description, views)."""
    from ..youtube.breakouts import duration_seconds
    from ..youtube.transcripts import video_id

    vid = video_id(url)
    if not vid:
        raise ValueError("that is not a YouTube video link")
    model: dict[str, Any] = {"url": f"https://www.youtube.com/watch?v={vid}", "title": "", "channel": ""}
    if youtube is not None:
        items = youtube.videos().list(part="snippet,statistics,contentDetails", id=vid).execute().get("items", [])
        if items:
            v = items[0]
            snippet, stats = v.get("snippet", {}), v.get("statistics", {})
            model.update(
                title=snippet.get("title", ""), channel=snippet.get("channelTitle", ""),
                views=int(stats.get("viewCount", 0) or 0),
                duration_seconds=duration_seconds((v.get("contentDetails") or {}).get("duration", "")),
                description=str(snippet.get("description", ""))[:600])
    return model


def apply_replace(spec: dict[str, Any], spec_path: Path, work: Path, database, production_id: str,
                  youtube: Any, transcript=None) -> bool:
    """Make the pasted video today's model and clear the old research and script. True when applied."""
    if not replace_pending(spec, work):
        return False
    ask = spec["replace_model"]
    model = model_from_link(youtube, str(ask["url"]))
    if transcript is None:
        from ..youtube.transcripts import fetch as transcript
    words = transcript(model["url"]) or ""
    if not model["title"] and not words:
        raise RuntimeError("the pasted video could not be read (no title and no transcript)")
    subject = model["title"] or " ".join(words.split()[:40])
    spec["title"] = model["title"] or spec.get("title", production_id)
    spec["model_title"] = model["title"] or spec.get("title", "")
    spec["source_breakout"] = {k: v for k, v in model.items()}
    spec["brief"] = (
        f"Today's video is modelled on the YouTube video \"{subject}\" by {model.get('channel') or 'its creator'} "
        f"({model['url']}), chosen by the owner. Explain the same subject: what happened, how it works and what "
        f"the viewer can do with it. Gather the facts from other credible sources, not only that video.\n"
        f"What that video says (for the subject only, never its sentences): {' '.join(words.split()[:350])}")
    spec["platform_demand"] = {"verdict": "pass", "signal_type": "owner-replace", "query": subject}
    spec["selected_topic_source"] = model["url"]
    spec.pop("topic_candidates", None)
    spec.pop("script_edit", None)          # an edit of the old script never lands on the new one
    spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    for name in REPLACE_FILES:
        (work / name).unlink(missing_ok=True)
    for stage in REPLACE_STAGES:
        database.execute("DELETE FROM stage_runs WHERE production_id=? AND stage=?", (production_id, stage))
    (work / REPLACE_DONE).write_text(str(ask.get("requested_at", "")) + "\n", encoding="utf-8")
    print(json.dumps({"status": "script_replaced", "production_id": production_id, "model": model["url"],
                      "title": spec["title"]}))
    return True


def story_from_reading(text: str, chapters: list[dict]) -> dict[str, Any]:
    """The owner's reading copy ("[1 · TITLE]" headings over paragraphs) back into a story the
    engine cuts into screen lines. Headings keep their chapter; a renamed heading renames it."""
    chapters = [dict(c) for c in chapters or []]
    parts: list[str] = []
    index = -1
    for raw in str(text).splitlines():
        line = raw.strip()
        heading = re.fullmatch(r"\[(.+)\]", line)
        if heading:
            index += 1
            title = heading.group(1).split("·", 1)[-1].strip()
            if index >= len(chapters):
                chapters.append({"number": str(index + 1), "title": title.title()})
            elif _norm(title) != _norm(chapters[index].get("title", "")):
                chapters[index]["title"] = title.title()
            parts.append(f"[[{index}]]")
        elif line:
            parts.append(line)
    if index < 0:
        chapters = chapters[:1] if chapters else []
        script = ("[[0]] " if chapters else "") + " ".join(parts)
    else:
        chapters = chapters[: index + 1]
        script = " ".join(parts)
    return {"script": script, "chapters": chapters}


def edit_pending(spec: dict[str, Any], work: Path, current_display: str) -> str:
    """The owner's edited words when they differ from the script on disk and are not applied yet."""
    edited = str(spec.get("script_edit") or "").strip()
    if not edited or (work / "timed-words-owner.json").exists():
        return ""
    done = work / EDIT_DONE
    if done.exists() and _norm(done.read_text(encoding="utf-8")) == _norm(edited):
        return ""
    if _norm(edited) == _norm(current_display):
        done.write_text(edited + "\n", encoding="utf-8")
        return ""
    return edited


def mark_edit_done(work: Path, edited: str) -> None:
    (work / EDIT_DONE).write_text(edited + "\n", encoding="utf-8")
