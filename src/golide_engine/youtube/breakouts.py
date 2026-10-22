"""YouTube decides the topic (owner direction 2026-10-21).

"Our go for videos is YouTube and that's the final decider and first decider and
base of our so-called trend. You don't go against the trend, you join it."

Every topic search starts here: tech videos from the last 48 hours that are
taking numbers right now, measured two ways:
* views per hour since upload (momentum), and
* breakout: views against the channel's own average per video, so a small
  channel beating its normal 50x counts as much as a giant channel's hit.
The planner then builds our candidates on these videos: the same topic, a title
modelled on the winning one with a few words changed, and our own script
structure and visuals. News is only used for the facts.

2026-10-22 (owner: "how do you model from a short? That is referencing, not
modelling"): a long video models a long video and a short models a short; a
source must clear the numbers bar; our title keeps the source title and changes
one to three words, checked here in code, not left to the model.
"""

from __future__ import annotations

import difflib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any

FRESH_HOURS = 48
WIDER_HOURS = 96          # when the last 48 hours are thin, look a little further back
MIN_RESULTS = 6
SEED_QUERIES = (
    "AI", "Tesla", "Elon Musk", "iPhone Apple", "robot", "ChatGPT OpenAI", "Nvidia",
    "new technology", "gadget", "Google AI", "SpaceX", "hacker cybersecurity",
)
SKIP_CATEGORIES = {"10", "17", "20"}   # music, sport, gaming: not our lane

# Same format only. YouTube's search filter: "medium" is 4 to 20 minutes, "short" under 4.
SEARCH_DURATION = {"long": "medium", "short": "short"}
LONG_MIN_SECONDS = 240
SHORT_MAX_SECONDS = 180

# The numbers bar: a source must be taking numbers right now (owner: "this is the game of numbers").
MIN_VIEWS_PER_HOUR = 2000
MIN_BREAKOUT = 5.0

# Our title is their title with one to three words changed.
MAX_TITLE_CHANGES = 3


def duration_seconds(iso: str) -> int:
    """YouTube's ISO 8601 duration (PT1H2M3S) in seconds; 0 when unreadable."""
    match = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", str(iso or ""))
    if not match:
        return 0
    d, h, m, s = (int(x or 0) for x in match.groups())
    return d * 86400 + h * 3600 + m * 60 + s


def fits_format(seconds: int, fmt: str) -> bool:
    if fmt == "short":
        return 0 < seconds <= SHORT_MAX_SECONDS
    return seconds >= LONG_MIN_SECONDS


def passes_bar(item: dict[str, Any]) -> bool:
    return (float(item.get("views_per_hour", 0)) >= MIN_VIEWS_PER_HOUR
            or float(item.get("breakout", 0)) >= MIN_BREAKOUT)


def _title_words(title: str) -> list[str]:
    text = re.sub(r"#\w+", " ", str(title))          # hashtags are dropped for free
    return re.findall(r"[a-z0-9']+", text.lower().replace("’", "'"))


def title_changes(source: str, ours: str) -> int:
    """Words changed between the source title and ours (replaced, added or removed)."""
    a, b = _title_words(source), _title_words(ours)
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    return sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in ops if tag != "equal")


def title_tweak_problem(source: str, ours: str) -> str:
    """Empty when ours is the source title with one to MAX_TITLE_CHANGES words changed."""
    if not str(ours).strip():
        return "no title"
    if len(str(ours)) > 100:
        return "longer than 100 characters"
    changed = title_changes(source, ours)
    if changed == 0:
        return "identical to the source title; change one to three words"
    if changed > MAX_TITLE_CHANGES:
        return f"changes {changed} words of the source title; keep it and change one to {MAX_TITLE_CHANGES}"
    return ""


def _age_hours(published: str, now: datetime) -> float:
    at = datetime.fromisoformat(published.replace("Z", "+00:00"))
    return max(1.0, (now - at).total_seconds() / 3600)


def score(vph: float, breakout: float) -> float:
    """0 to about 100: momentum and breakout both count (log-scaled)."""
    return round(min(60.0, math.log10(1 + vph) * 15) + min(40.0, math.log10(1 + breakout) * 20), 1)


def find_breakouts(youtube: Any, fmt: str = "long", now: datetime | None = None, hours: int = FRESH_HOURS,
                   queries: tuple = SEED_QUERIES, per_query: int = 15, limit: int = 25) -> list[dict[str, Any]]:
    """The tech videos in our format taking the most numbers right now, best first. Only
    videos that clear the numbers bar are returned. Best effort per query."""
    now = now or datetime.now(timezone.utc)
    after = (now - timedelta(hours=hours)).isoformat().replace("+00:00", "Z")
    ids: list[str] = []
    for query in queries:
        try:
            response = youtube.search().list(
                part="id", q=query, type="video", order="viewCount", publishedAfter=after,
                videoDuration=SEARCH_DURATION.get(fmt, "medium"), maxResults=per_query, regionCode="US", relevanceLanguage="en", safeSearch="moderate",
            ).execute()
        except Exception as exc:  # noqa: BLE001 - one failed query never stops the search
            print(json.dumps({"status": "breakout_query_failed", "query": query, "error": str(exc)[:160]}))
            continue
        for item in response.get("items", []):
            vid = item.get("id", {}).get("videoId")
            if vid and vid not in ids:
                ids.append(vid)
    videos: list[dict[str, Any]] = []
    for start in range(0, len(ids), 50):
        batch = youtube.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids[start:start + 50]),
                                      maxResults=50).execute()
        videos += batch.get("items", [])
    channel_ids = sorted({v["snippet"]["channelId"] for v in videos if v.get("snippet")})
    channels: dict[str, dict] = {}
    for start in range(0, len(channel_ids), 50):
        batch = youtube.channels().list(part="statistics,snippet", id=",".join(channel_ids[start:start + 50]),
                                        maxResults=50).execute()
        channels.update({c["id"]: c for c in batch.get("items", [])})
    out = []
    for v in videos:
        snippet, stats = v.get("snippet", {}), v.get("statistics", {})
        if str(snippet.get("categoryId", "")) in SKIP_CATEGORIES:
            continue
        seconds = duration_seconds((v.get("contentDetails") or {}).get("duration", ""))
        if not fits_format(seconds, fmt):
            continue
        views = int(stats.get("viewCount", 0) or 0)
        channel = channels.get(snippet.get("channelId", ""), {})
        cstats = channel.get("statistics", {})
        per_video = int(cstats.get("viewCount", 0) or 0) / max(1, int(cstats.get("videoCount", 0) or 1))
        vph = views / _age_hours(snippet.get("publishedAt", now.isoformat()), now)
        breakout = views / max(1.0, per_video)
        out.append({
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "subscribers": int(cstats.get("subscriberCount", 0) or 0),
            "views": views,
            "views_per_hour": round(vph, 1),
            "breakout": round(breakout, 1),
            "hours_old": round(_age_hours(snippet.get("publishedAt", now.isoformat()), now), 1),
            "duration_seconds": seconds,
            "format": fmt,
            "description": str(snippet.get("description", ""))[:300],
            "url": f"https://www.youtube.com/watch?v={v.get('id', '')}",
            "score": score(vph, breakout),
        })
    out = [b for b in out if passes_bar(b)]
    out.sort(key=lambda b: -b["score"])
    if len(out) < MIN_RESULTS and hours < WIDER_HOURS:
        return find_breakouts(youtube, fmt, now, WIDER_HOURS, queries, per_query, limit)
    return out[:limit]


BREAKOUT_RULES = """\
YOUTUBE DECIDES THE TOPIC (owner direction 2026-10-21: "you don't go against the
trend, you join it"). BREAKOUTS lists videos in OUR format (long models long, short
models short) from the last 48 hours that are taking numbers right now, best first:
views per hour, and "breakout" = views against that channel's own average (50
means 50 times its normal). Every one has already cleared the numbers bar.
- Every candidate MUST be built on one breakout: set "source_breakout" to its
  number in the list (0 = the first). Prefer the top of the list.
- MODEL it, do not just reference it: the topic, the angle and the order of the
  story are theirs (read their title and description). The words, the facts and the
  visuals are ours, told more clearly.
- "model_title": THEIR EXACT TITLE with one to three words changed, nothing more.
  Keep their structure, hook, keywords and capitals. Never identical, never
  rewritten. Example: "The NEW Tesla Roadster: My Honest Reaction" becomes
  "The NEW Tesla Roadster: My Honest Breakdown". Drop hashtags.
- A topic GOLIDE already covered is fine when it is taking numbers again: give it a
  new narrative.
- Skip a breakout that is music, sport, gaming, gossip, party politics or plain
  company paperwork with nothing to show or explain.
- Use web search only to get the real facts and one credible source for the topic.
"""
