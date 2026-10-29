"""Transcripts of the videos a script is modelled on (owner direction 2026-10-29).

"Those successful videos... they are like that because it works, so why not model them."
The script writer reads what successful videos actually SAY, not just their titles.

YouTube blocks transcript downloads from GitHub's servers (tested 2026-10-29: both the
transcript API and yt-dlp were refused), so the engine fetches them through Supadata
(SUPADATA_API_KEY), a transcript service that handles that. Without the key it tries
the direct way (works from home connections) and otherwise goes on without transcripts.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

SUPADATA = "https://api.supadata.ai/v1/transcript"
MODEL_VIDEOS_FILE = Path(__file__).resolve().parents[3] / "config" / "model-videos.txt"
WORD_CAP = {"short": 450, "long": 1500}   # how much of each model transcript the writer reads
TAIL_WORDS = 250                           # long videos: the ending is read too


def video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url or "")
    return m.group(1) if m else (url if re.fullmatch(r"[A-Za-z0-9_-]{11}", url or "") else "")


def _clean(text: str) -> str:
    text = re.sub(r"\[[^\]]{1,20}\]", " ", text)           # [Music], [Applause]
    return re.sub(r"\s+", " ", text).strip()


def _supadata(url: str, key: str) -> str:
    query = urllib.parse.urlencode({"url": url, "text": "true", "lang": "en"})
    headers = {"x-api-key": key, "User-Agent": "golide-engine"}

    def get(address: str) -> dict:
        with urllib.request.urlopen(urllib.request.Request(address, headers=headers), timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))

    data = get(f"{SUPADATA}?{query}")
    for _ in range(12):                                     # long videos come back as a job
        if not data.get("jobId") or data.get("content"):
            break
        time.sleep(5)
        data = get(f"{SUPADATA}/{data['jobId']}")
    content = data.get("content", "")
    if isinstance(content, list):
        content = " ".join(str(s.get("text", "")) for s in content)
    return _clean(str(content))


def _direct(vid: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi
    fetched = YouTubeTranscriptApi().fetch(vid, languages=["en", "en-US", "en-GB"])
    return _clean(" ".join(s.text for s in fetched))


def fetch(url: str) -> str:
    """The video's spoken words, or "" when no source can get them."""
    vid = video_id(url)
    if not vid:
        return ""
    key = os.getenv("SUPADATA_API_KEY", "").strip()
    full = f"https://www.youtube.com/watch?v={vid}"
    for attempt in ((lambda: _supadata(full, key)) if key else None, lambda: _direct(vid)):
        if attempt is None:
            continue
        try:
            text = attempt()
        except Exception as exc:  # noqa: BLE001 - a missing transcript never stops production
            print(json.dumps({"status": "transcript_unavailable", "video": vid, "error": str(exc)[:200]}))
            continue
        if len(text.split()) >= 40:
            return text
    return ""


def trim(text: str, fmt: str) -> str:
    words = text.split()
    cap = WORD_CAP.get(fmt, 600)
    if len(words) <= cap + TAIL_WORDS:
        return text
    if fmt == "long":
        return " ".join(words[:cap]) + " [...] " + " ".join(words[-TAIL_WORDS:])
    return " ".join(words[:cap])


def owner_picks(fmt: str) -> list[str]:
    """Videos the owner chose as references (config/model-videos.txt: "short <url>" / "long <url>")."""
    try:
        lines = MODEL_VIDEOS_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    picks = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and not line.startswith("#") and parts[0] in (fmt, "any"):
            picks.append(parts[1])
    return picks


def choose_models(source: dict | None, breakouts: list[dict], fmt: str, limit: int = 3) -> list[dict]:
    """The video we model first, then the strongest other breakouts of this format (one per
    channel), then the owner's own picks; at most ``limit`` with a transcript."""
    chosen: list[dict] = []
    seen_channels: set[str] = set()
    pool = ([source] if source and source.get("url") else []) + sorted(
        (b for b in breakouts if b.get("format", fmt) == fmt and b.get("url")),
        key=lambda b: float(b.get("score", 0)), reverse=True)
    pool += [{"url": u, "title": "", "channel": "owner pick"} for u in owner_picks(fmt)]
    for video in pool:
        if len(chosen) >= limit:
            break
        channel = str(video.get("channel", ""))
        if channel in seen_channels and channel != "owner pick":
            continue
        if any(video_id(c["url"]) == video_id(video["url"]) for c in chosen):
            continue
        text = fetch(video["url"])
        if not text:
            continue
        seen_channels.add(channel)
        chosen.append({"url": video["url"], "title": video.get("title", ""), "channel": channel,
                       "views": video.get("views"), "transcript": trim(text, fmt)})
    return chosen
