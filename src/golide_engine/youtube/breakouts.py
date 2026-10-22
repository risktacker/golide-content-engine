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
from pathlib import Path
from typing import Any

# Long videos build views more slowly than shorts, so they get a longer fresh window
# (2026-10-22: a 7-minute breakdown 54 hours old must still count on Saturday).
FRESH_HOURS = {"long": 72, "short": 48}
WIDER_HOURS = 96          # when the fresh window is thin, look a little further back
MIN_RESULTS = 6
# Safety net only, when config/trend-sources.json is missing (2026-10-22: the sources
# are YouTube's own charts, the tech channels and a rotating industry watchlist).
SEED_QUERIES = (
    "AI", "Tesla", "Elon Musk", "iPhone Apple", "robot", "ChatGPT OpenAI", "Nvidia",
    "new technology", "gadget", "Google AI", "SpaceX", "hacker cybersecurity",
)
SOURCES_FILE = Path(__file__).resolve().parents[3] / "config" / "trend-sources.json"
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


def load_sources(path: Path | None = None) -> dict[str, Any]:
    try:
        return json.loads((path or SOURCES_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"chart_regions": ["US"], "chart_category": "28", "channels": [],
                "watchlist": list(SEED_QUERIES), "searches_per_run": len(SEED_QUERIES), "hot_terms_per_run": 0}


def rotation(items: list[str], count: int, day: int, offset: int = 0) -> list[str]:
    """A different slice of the watchlist each run, so every name is searched every few days."""
    if not items or count <= 0:
        return []
    start = (day * count + offset) % len(items)
    return [items[(start + i) % len(items)] for i in range(min(count, len(items)))]


TITLE_STOP = {
    "the", "this", "that", "these", "new", "how", "why", "what", "when", "who", "you", "your", "just", "full",
    "review", "best", "official", "first", "look", "here", "its", "it's", "all", "and", "for", "with", "now",
    "finally", "really", "every", "everything", "nobody", "everyone", "why", "is", "are", "was", "will", "can",
    "my", "i", "we", "our", "they", "breakdown", "explained", "update", "news", "video", "watch", "today",
    "introducing", "announcing", "vs", "top", "big", "huge", "insane", "crazy", "shorts", "short", "ai",
}


def hot_terms(items: list[tuple[str, str]], count: int) -> list[str]:
    """Names in the titles of several different channels right now ("Claude Duet",
    "Galaxy S26"): what the industry is talking about today, found without a list."""
    if count <= 0:
        return []
    seen: dict[str, set[str]] = {}
    for title, channel in items:
        words = re.findall(r"[A-Za-z0-9][A-Za-z0-9+.'-]*", re.sub(r"#\w+", " ", title))
        caps = [w.strip(".'") for w in words]
        run: list[str] = []
        terms: set[str] = set()
        for word in caps + [""]:
            keep = word and (word[0].isupper() or any(ch.isdigit() for ch in word)) and word.lower() not in TITLE_STOP
            if keep and len(word) >= 2:
                run.append(word)
                continue
            for size in (2, 1):
                for i in range(len(run) - size + 1):
                    term = " ".join(run[i:i + size])
                    if len(term) >= 3 and not term.isdigit():
                        terms.add(term)
            run = []
        for term in terms:
            seen.setdefault(term, set()).add(channel)
    ranked = sorted((t for t, ch in seen.items() if len(ch) >= 2), key=lambda t: (-len(seen[t]), -len(t.split()), t))
    picked: list[str] = []
    for term in ranked:
        if any(term.lower() in p.lower() or p.lower() in term.lower() for p in picked):
            continue
        picked.append(term)
        if len(picked) == count:
            break
    return picked


def _call(label: str, fn):
    try:
        return fn().execute()
    except Exception as exc:  # noqa: BLE001 - one failed source never stops the search
        print(json.dumps({"status": "breakout_source_failed", "source": label, "error": str(exc)[:160]}))
        return {}


def _chart_videos(youtube: Any, sources: dict) -> list[dict]:
    """YouTube's own Science & Technology trending charts (1 quota unit per region)."""
    out: list[dict] = []
    for region in sources.get("chart_regions", []):
        response = _call(f"chart:{region}", lambda r=region: youtube.videos().list(
            part="snippet,statistics,contentDetails", chart="mostPopular",
            videoCategoryId=str(sources.get("chart_category", "28")), regionCode=r, maxResults=50))
        out += [dict(v, found_by=f"chart {region}") for v in response.get("items", [])]
    return out


def _channel_upload_ids(youtube: Any, handles: list[str], after: datetime) -> dict[str, str]:
    """Latest uploads of the tech channels that cover everything (2 quota units each)."""
    found: dict[str, str] = {}
    for handle in handles:
        channel = _call(f"channel:{handle}", lambda h=handle: youtube.channels().list(
            part="contentDetails", forHandle=h.lstrip("@")))
        items = channel.get("items") or []
        if not items:
            print(json.dumps({"status": "channel_handle_unknown", "handle": handle}))
            continue
        uploads = ((items[0].get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads")
        if not uploads:
            continue
        latest = _call(f"uploads:{handle}", lambda u=uploads: youtube.playlistItems().list(
            part="contentDetails", playlistId=u, maxResults=10))
        for item in latest.get("items", []):
            details = item.get("contentDetails") or {}
            published = details.get("videoPublishedAt", "")
            try:
                fresh = datetime.fromisoformat(published.replace("Z", "+00:00")) >= after
            except ValueError:
                fresh = False
            if fresh and details.get("videoId"):
                found.setdefault(details["videoId"], f"channel {handle}")
    return found


def _search_ids(youtube: Any, queries: list[str], fmt: str, after: datetime, per_query: int) -> dict[str, str]:
    """YouTube search, the expensive source (100 quota units each), so it is used sparingly."""
    stamp = after.isoformat().replace("+00:00", "Z")
    found: dict[str, str] = {}
    for query in queries:
        response = _call(f"search:{query}", lambda q=query: youtube.search().list(
            part="id", q=q, type="video", order="viewCount", publishedAfter=stamp,
            videoDuration=SEARCH_DURATION.get(fmt, "medium"), maxResults=per_query,
            regionCode="US", relevanceLanguage="en", safeSearch="moderate"))
        for item in response.get("items", []):
            vid = item.get("id", {}).get("videoId")
            if vid:
                found.setdefault(vid, f"search {query}")
    return found


def _fetch(youtube: Any, found: dict[str, str]) -> list[dict]:
    ids = list(found)
    videos: list[dict] = []
    for start in range(0, len(ids), 50):
        batch = _call("videos", lambda chunk=ids[start:start + 50]: youtube.videos().list(
            part="snippet,statistics,contentDetails", id=",".join(chunk), maxResults=50))
        videos += [dict(v, found_by=found.get(v.get("id", ""), "")) for v in batch.get("items", [])]
    return videos


def _measure(youtube: Any, videos: list[dict], fmt: str, now: datetime) -> list[dict[str, Any]]:
    channel_ids = sorted({v["snippet"]["channelId"] for v in videos if v.get("snippet", {}).get("channelId")})
    channels: dict[str, dict] = {}
    for start in range(0, len(channel_ids), 50):
        batch = _call("channels", lambda chunk=channel_ids[start:start + 50]: youtube.channels().list(
            part="statistics,snippet", id=",".join(chunk), maxResults=50))
        channels.update({c["id"]: c for c in batch.get("items", [])})
    out, seen = [], set()
    for v in videos:
        if v.get("id") in seen:
            continue
        seen.add(v.get("id"))
        snippet, stats = v.get("snippet", {}), v.get("statistics", {})
        if str(snippet.get("categoryId", "")) in SKIP_CATEGORIES:
            continue
        seconds = duration_seconds((v.get("contentDetails") or {}).get("duration", ""))
        if not fits_format(seconds, fmt):
            continue
        views = int(stats.get("viewCount", 0) or 0)
        cstats = channels.get(snippet.get("channelId", ""), {}).get("statistics", {})
        per_video = int(cstats.get("viewCount", 0) or 0) / max(1, int(cstats.get("videoCount", 0) or 1))
        age = _age_hours(snippet.get("publishedAt", now.isoformat()), now)
        vph, breakout = views / age, views / max(1.0, per_video)
        out.append({
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "subscribers": int(cstats.get("subscriberCount", 0) or 0),
            "views": views,
            "views_per_hour": round(vph, 1),
            "breakout": round(breakout, 1),
            "hours_old": round(age, 1),
            "duration_seconds": seconds,
            "format": fmt,
            "found_by": v.get("found_by", ""),
            "description": str(snippet.get("description", ""))[:300],
            "url": f"https://www.youtube.com/watch?v={v.get('id', '')}",
            "score": score(vph, breakout),
        })
    return out


def find_breakouts(youtube: Any, fmt: str = "long", now: datetime | None = None, hours: int | None = None,
                   queries: tuple | None = None, per_query: int = 15, limit: int = 25,
                   sources: dict | None = None) -> list[dict[str, Any]]:
    """Videos in our format taking the most numbers right now, best first; only those
    clearing the numbers bar. Sources (2026-10-22, the whole industry, not 12 phrases):
    YouTube's trending charts, the uploads of the big tech channels, searches for the
    names several channels are talking about today, and a rotating industry watchlist.
    Passing ``queries`` searches only those (used by tests and manual checks)."""
    now = now or datetime.now(timezone.utc)
    fresh_hours = hours or FRESH_HOURS.get(fmt, 48)
    wide = now - timedelta(hours=max(WIDER_HOURS, fresh_hours))
    videos: list[dict] = []
    if queries is None:
        sources = sources or load_sources()
        videos = _chart_videos(youtube, sources)
        videos += _fetch(youtube, _channel_upload_ids(youtube, list(sources.get("channels", [])), wide))
        talked = [(v.get("snippet", {}).get("title", ""), v.get("snippet", {}).get("channelId", ""))
                  for v in videos]
        hot = hot_terms(talked, int(sources.get("hot_terms_per_run", 4)))
        day = now.date().toordinal()
        searches = hot + [q for q in rotation(list(sources.get("watchlist", [])),
                                              int(sources.get("searches_per_run", 8)), day,
                                              0 if fmt == "long" else 3)
                          if q.lower() not in {h.lower() for h in hot}]
        print(json.dumps({"status": "breakout_sources", "format": fmt, "chart_and_channel_videos": len(videos),
                          "hot_terms": hot, "searches": searches}))
    else:
        searches = list(queries)
    have = {v.get("id") for v in videos}
    videos += _fetch(youtube, {k: v for k, v in _search_ids(youtube, searches, fmt, wide, per_query).items()
                               if k not in have})
    measured = [b for b in _measure(youtube, videos, fmt, now) if passes_bar(b)]
    fresh = [b for b in measured if b["hours_old"] <= fresh_hours]
    out = fresh if len(fresh) >= MIN_RESULTS else measured
    out.sort(key=lambda b: -b["score"])
    return out[:limit]


BREAKOUT_RULES = """\
YOUTUBE DECIDES THE TOPIC (owner direction 2026-10-21: "you don't go against the
trend, you join it"). BREAKOUTS lists videos in OUR format (long models long, short
models short) from the last few days that are taking numbers right now, best first:
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
