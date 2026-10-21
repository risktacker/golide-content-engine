"""The trend pulse: is a story breaking and rising RIGHT NOW? (owner direction 2026-10-17)

The demand gate (``demand.py``) asks whether a subject is popular on YouTube over
30 days. That passes almost any tech topic, so big-company updates were winning
over the stories everyone was actually talking about. The pulse adds what a
trend really is, for this channel:

1. FRESH:  the story broke in the last 48 hours.
2. RISING: new videos about it (under 48 hours old) are gaining views fast.
3. OPEN:   there is a "how does it work / is it real" question with science or
           engineering underneath, which is what GOLIDE explains.
4. BROAD:  a normal person would stop scrolling for it (judged by the planner).

Signals: YouTube search of the last 48 hours (views per hour), plus free public
front pages (Hacker News, Reddit technology) to see what people are discussing.
Everything here is best effort: a missing signal never blocks a video.
"""

from __future__ import annotations

import json
import math
import statistics
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

FRESH_HOURS = 48
HOT_SCORE = 60.0           # a candidate at or above this is a live trend
MIN_FRESH_VIDEOS = 3       # ... and must already have this many fresh videos

PULSE_RULES = """\
TREND PULSE (owner direction 2026-10-17: "we need not to be left out"). A real
trend for GOLIDE passes four tests, in this order of importance:
1. FRESH: the story broke in the last 48 hours (give the date in "broke_on").
2. RISING: people are talking about it right now (see FRESH HEADLINES, and the
   platform seeds), not just a company announcement nobody is sharing.
3. OPEN QUESTION WITH SCIENCE UNDERNEATH: viewers are asking how it works, whether
   it is real, or what it means, and there is real science or engineering we can
   explain (forces, energy, chips, batteries, AI training, optics, materials...).
   Say it in one line in "science_angle"; "" when there is none.
4. BROAD: a curious non-technical person would stop scrolling for it.
A story that passes all four beats a bigger company's routine update. Make at
least one candidate the most-discussed fresh tech story with a science angle,
even if its company was covered recently (a live trend is the exception to the
spread-it-out rule). Every week has one: a viral demo, a launch everyone argues
about, a record, a failure.
"""


@dataclass(frozen=True)
class Pulse:
    query: str
    fresh_videos: int
    median_views_per_hour: float
    top_views_per_hour: float
    score: float
    hot: bool
    measured_at: str


def score_pulse(fresh_videos: int, median_vph: float, top_vph: float, has_science: bool) -> float:
    """0 to 100. Velocity of fresh videos dominates; supply and a science angle add."""
    supply = min(20.0, fresh_videos * 2.0)
    median = min(40.0, math.log10(1 + median_vph) * 12.0)   # 1k views/hour -> 36
    top = min(25.0, math.log10(1 + top_vph) * 5.0)          # 100k views/hour -> 25
    science = 15.0 if has_science else 0.0
    return round(supply + median + top + science, 1)


def measure(youtube: Any, query: str, has_science: bool, now: datetime | None = None,
            market: str = "US") -> Pulse:
    """Views per hour of the most-watched videos on ``query`` from the last 48 hours."""
    now = now or datetime.now(timezone.utc)
    after = (now - timedelta(hours=FRESH_HOURS)).isoformat().replace("+00:00", "Z")
    response = youtube.search().list(
        part="snippet", q=query, type="video", order="viewCount", publishedAfter=after,
        maxResults=10, regionCode=market, relevanceLanguage="en", safeSearch="strict",
    ).execute()
    ids = [item.get("id", {}).get("videoId") for item in response.get("items", [])]
    ids = [i for i in ids if i]
    rates: list[float] = []
    if ids:
        stats = youtube.videos().list(part="statistics,snippet", id=",".join(ids), maxResults=10).execute()
        for item in stats.get("items", []):
            views = int(item.get("statistics", {}).get("viewCount", 0) or 0)
            published = item.get("snippet", {}).get("publishedAt")
            if not published:
                continue
            age = (now - datetime.fromisoformat(published.replace("Z", "+00:00"))).total_seconds() / 3600
            rates.append(views / max(1.0, age))
    median = statistics.median(rates) if rates else 0.0
    top = max(rates, default=0.0)
    score = score_pulse(len(rates), median, top, has_science)
    return Pulse(query, len(rates), round(median, 1), round(top, 1), score,
                 score >= HOT_SCORE and len(rates) >= MIN_FRESH_VIDEOS and has_science,
                 now.isoformat())


def attach(youtube: Any, candidates: list[dict[str, Any]], now: datetime | None = None) -> None:
    """Measure every candidate's pulse in place (best effort: a failure leaves no pulse)."""
    for candidate in candidates:
        try:
            pulse = measure(youtube, candidate.get("query") or candidate["title"],
                            bool(str(candidate.get("science_angle") or "").strip()), now)
            candidate["trend_pulse"] = asdict(pulse)
        except Exception as exc:  # noqa: BLE001 - a signal outage never blocks a video
            print(json.dumps({"status": "trend_pulse_unavailable", "query": candidate.get("query"),
                              "error": str(exc)[:200]}))


def hot_first(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The live trends among the candidates, hottest first (empty when there are none)."""
    hot = [c for c in candidates if (c.get("trend_pulse") or {}).get("hot")]
    return sorted(hot, key=lambda c: -float(c["trend_pulse"]["score"]))


def choose(gate: Any, spec: dict[str, Any]):
    """Pick the topic. 2026-10-21: a candidate built on a YouTube breakout wins outright,
    the strongest breakout first; the breakout itself is the demand proof. Without one,
    a live trend that passes the demand gate wins; otherwise the demand ranking decides."""
    from .demand import DemandResult, TopicDemandRejected

    riding = [c for c in spec.get("topic_candidates") or [] if c.get("breakout") and c.get("evidence_valid")]
    if riding:
        best = max(riding, key=lambda c: float(c["breakout"].get("score", 0)))
        b = best["breakout"]
        demand = DemandResult(
            query=best.get("query") or best["title"], score=float(b.get("score", 0)), verdict="pass",
            recent_videos=1, median_views_per_day=float(b.get("views_per_hour", 0)) * 24,
            top_views_per_day=float(b.get("views_per_hour", 0)) * 24, market_coverage=1,
            title_query_overlap=1.0, measured_at=datetime.now(timezone.utc).isoformat(),
            signal_type="youtube-breakout-v1",
        )
        print(json.dumps({"status": "breakout_selected", "title": best.get("model_title"),
                          "source": b.get("title"), "views_per_hour": b.get("views_per_hour"),
                          "breakout": b.get("breakout")}))
        return best, demand

    hot = hot_first(spec.get("topic_candidates") or [])
    if hot:
        try:
            candidate, demand = gate.select({**spec, "topic_candidates": hot})
            print(json.dumps({"status": "live_trend_selected", "title": candidate.get("title"),
                              "pulse": candidate.get("trend_pulse")}))
            return candidate, demand
        except TopicDemandRejected:
            pass
    return gate.select(spec)


# ------------------------------------------------------------ what people discuss

def _get_json(url: str, timeout: float = 8.0) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "golide-content-engine/1.0 (trend pulse)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fresh_headlines(now: datetime | None = None, limit: int = 30) -> list[dict[str, Any]]:
    """Tech headlines people are discussing in the last 48 hours, from free public front
    pages. Best effort: returns what it can, never raises."""
    now = now or datetime.now(timezone.utc)
    since = int((now - timedelta(hours=FRESH_HOURS)).timestamp())
    out: list[dict[str, Any]] = []
    try:
        from urllib.parse import quote

        filters = quote(f"created_at_i>{since},points>150")
        data = _get_json(f"https://hn.algolia.com/api/v1/search?tags=story&numericFilters={filters}&hitsPerPage={limit}")
        for hit in data.get("hits", []):
            out.append({"source": "hacker news", "title": hit.get("title", ""), "points": hit.get("points", 0),
                        "comments": hit.get("num_comments", 0)})
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "headlines_unavailable", "source": "hacker news", "error": str(exc)[:120]}))
    for sub in ("technology", "Futurology"):
        try:
            data = _get_json(f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=15")
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                out.append({"source": f"reddit r/{sub}", "title": post.get("title", ""),
                            "points": post.get("score", 0), "comments": post.get("num_comments", 0)})
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"status": "headlines_unavailable", "source": sub, "error": str(exc)[:120]}))
    out.sort(key=lambda h: -(int(h.get("points") or 0) + 3 * int(h.get("comments") or 0)))
    return [h for h in out if h["title"]][:limit]
