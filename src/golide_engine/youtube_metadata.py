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
    if sum(len(tag) + (2 if " " in tag else 0) for tag in tags) + max(0, len(tags) - 1) > 500:
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
        if chapters:  # chapters come from the real recording; none is allowed, wrong ones are not
            validate_chapters(chapters)
    elif chapters:
        raise YouTubeMetadataError("Shorts do not use manual chapters")


# ---------------------------------------------------------------------------
# SEO layout (owner direction 2026-10-13), the same on every platform:
#   summary paragraphs
#   10+ trending keywords, comma separated
#   chapters (long videos, added from the real recording)
#   hashtags
# YouTube also gets more than 20 tags.
# ---------------------------------------------------------------------------

def _clean_hashtags(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        word = "".join(ch for ch in str(item) if ch.isalnum())
        if word and ("#" + word).casefold() not in {h.casefold() for h in out}:
            out.append("#" + word)
    return out[:8]  # YouTube ignores every hashtag when there are more than 15


def _clean_keywords(items: list[str], limit: int = 20) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        word = " ".join(str(item).replace(",", " ").replace("#", "").split())
        if word and word.casefold() not in seen:
            seen.add(word.casefold())
            out.append(word)
    return out[:limit]


def seo_body(description: str) -> str:
    """The summary paragraphs only: no hashtag lines, no keyword or chapter lines."""
    rows = [r for r in description.splitlines() if not r.strip().startswith("#")]
    return "\n".join(rows).strip()


def compose_description(body: str, keywords: list[str], hashtags: list[str]) -> str:
    parts = [seo_body(body)]
    keys = _clean_keywords(keywords)
    if keys:
        parts.append(", ".join(keys))
    tags = _clean_hashtags(hashtags)
    if tags:
        parts.append(" ".join(tags))
    return "\n\n".join(p for p in parts if p)


def youtube_tag_cost(tag: str) -> int:
    """YouTube counts a tag with a space as if it were quoted (+2 characters)."""
    return len(tag) + (2 if " " in tag else 0)


def clean_tag(tag: str) -> str:
    """Only characters YouTube accepts in a tag (2026-10-14: an upload failed with invalidTags)."""
    text = "".join(ch for ch in str(tag) if ch.isalnum() or ch in " -&.'")
    return " ".join(text.replace("'", "").split())[:30].strip()


def fit_tags(tags: list[str], keywords: list[str], limit_chars: int = 460, minimum: int = 21) -> list[str]:
    """More than 20 unique tags, safely inside YouTube's 500-character budget,
    counted the way YouTube counts them (quotes around multi-word tags, commas)."""
    pool = _clean_keywords(list(tags) + list(keywords) + ["GOLIDE", "AI news", "tech news", "artificial intelligence",
                                                          "AI explained", "automation", "technology", "AI tools",
                                                          "AI trends", "future of AI", "tech explained",
                                                          "machine learning", "AI update", "AI technology",
                                                          "new technology", "AI for beginners"], limit=60)
    out: list[str] = []
    seen: set[str] = set()
    for raw in pool:
        tag = clean_tag(raw)
        if len(tag) < 2 or tag.casefold() in seen:
            continue
        cost = sum(youtube_tag_cost(t) for t in out) + max(0, len(out) - 1)
        if cost + youtube_tag_cost(tag) + (1 if out else 0) <= limit_chars:
            out.append(tag)
            seen.add(tag.casefold())
    return out


def social_caption(title: str, metadata: dict, limit: int) -> str:
    """Title, summary, keywords, chapters and hashtags, trimming only the summary to fit."""
    keys = ", ".join(_clean_keywords(metadata.get("keywords") or []))
    tags = " ".join(_clean_hashtags(metadata.get("hashtags") or []))
    chapters = "\n".join(metadata.get("chapters") or [])
    body = seo_body(str(metadata.get("seo_body") or metadata.get("description", "")))
    if not keys and not tags:  # older metadata: keep the full description as it was
        return (title.strip() + "\n\n" + str(metadata.get("description", "")).strip())[:limit]
    tail = "\n\n".join(p for p in (keys, ("Chapters\n" + chapters) if chapters else "", tags) if p)
    room = max(0, limit - len(title) - len(tail) - 6)
    if len(body) > room:
        body = body[:room].rsplit(" ", 1)[0].rstrip(",.;:") + "..."
    return "\n\n".join(p for p in (title.strip(), body, tail) if p)[:limit]
