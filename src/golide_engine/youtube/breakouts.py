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
"""

from __future__ import annotations

import json
import math
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


def _age_hours(published: str, now: datetime) -> float:
    at = datetime.fromisoformat(published.replace("Z", "+00:00"))
    return max(1.0, (now - at).total_seconds() / 3600)


def score(vph: float, breakout: float) -> float:
    """0 to about 100: momentum and breakout both count (log-scaled)."""
    return round(min(60.0, math.log10(1 + vph) * 15) + min(40.0, math.log10(1 + breakout) * 20), 1)


def find_breakouts(youtube: Any, now: datetime | None = None, hours: int = FRESH_HOURS,
                   queries: tuple = SEED_QUERIES, per_query: int = 15, limit: int = 25) -> list[dict[str, Any]]:
    """The tech videos taking the most numbers right now, best first. Best effort per query."""
    now = now or datetime.now(timezone.utc)
    after = (now - timedelta(hours=hours)).isoformat().replace("+00:00", "Z")
    ids: list[str] = []
    for query in queries:
        try:
            response = youtube.search().list(
                part="id", q=query, type="video", order="viewCount", publishedAfter=after,
                maxResults=per_query, regionCode="US", relevanceLanguage="en", safeSearch="moderate",
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
        batch = youtube.videos().list(part="snippet,statistics", id=",".join(ids[start:start + 50]),
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
            "description": str(snippet.get("description", ""))[:300],
            "url": f"https://www.youtube.com/watch?v={v.get('id', '')}",
            "score": score(vph, breakout),
        })
    out.sort(key=lambda b: -b["score"])
    if len(out) < MIN_RESULTS and hours < WIDER_HOURS:
        return find_breakouts(youtube, now, WIDER_HOURS, queries, per_query, limit)
    return out[:limit]


BREAKOUT_RULES = """\
YOUTUBE DECIDES THE TOPIC (owner direction 2026-10-21: "you don't go against the
trend, you join it"). BREAKOUTS lists tech videos from the last 48 hours that are
taking numbers right now, best first: views per hour, and "breakout" = views
against that channel's own average (50 means 50 times its normal).
- Every candidate MUST be built on one breakout: set "source_breakout" to its
  number in the list (0 = the first). Prefer the top of the list.
- Same topic, our own way: the topic and the moment are theirs, the script will be
  ours (our structure, the science of how it works, our visuals).
- "model_title": our YouTube title, modelled on that breakout's title. Keep its
  structure, its hook and its keywords; change a few words so it is ours, never
  identical (under 90 characters). Example: "The NEW Tesla Roadster: My Honest
  Reaction" becomes "The NEW Tesla Roadster: How It Actually Flies".
- A topic GOLIDE already covered is fine when it is taking numbers again: give it a
  new narrative.
- Skip a breakout that is music, sport, gaming, gossip, party politics or plain
  company paperwork with nothing to show or explain.
- Use web search only to get the real facts and one credible source for the topic.
"""
