from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from ..storage.database import Database, utc_now


class TopicDemandRejected(RuntimeError):
    pass


@dataclass(frozen=True)
class DemandResult:
    query: str
    score: float
    verdict: str
    recent_videos: int
    median_views_per_day: float
    top_views_per_day: float
    market_coverage: int
    title_query_overlap: float
    measured_at: str
    signal_type: str = "observable-youtube-demand-proxy"


class YouTubeDemandGate:
    """Ranks evidence-valid topics using platform-wide YouTube signals.

    The Data API does not expose raw search volume. This gate therefore records
    transparent proxies: recent relevant supply, view velocity, title/query
    overlap and cross-market coverage. It never reads or changes channel country.
    """

    def __init__(
        self,
        youtube: Any,
        database: Database,
        *,
        markets: tuple[str, ...] = ("US", "GB", "IN", "ZA"),
        threshold: float = 55.0,
        now: datetime | None = None,
    ):
        self.youtube = youtube
        self.database = database
        self.markets = markets
        self.threshold = float(threshold)
        self.now = now or datetime.now(timezone.utc)

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {token for token in "".join(c.lower() if c.isalnum() else " " for c in value).split() if len(token) > 2}

    def _cache_key(self, query: str, format: str) -> str:
        raw = f"{self.now.date()}|{format}|{query.strip().lower()}|{','.join(self.markets)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _cached(self, key: str) -> DemandResult | None:
        rows = self.database.rows(
            "SELECT result_json FROM topic_demand_snapshots WHERE cache_key=?",
            (key,),
        )
        return DemandResult(**json.loads(rows[0]["result_json"])) if rows else None

    def evaluate(self, query: str, format: str) -> DemandResult:
        query = query.strip()
        if not query:
            raise ValueError("demand query is required")
        if format not in {"short", "long"}:
            raise ValueError("format must be short or long")
        key = self._cache_key(query, format)
        cached = self._cached(key)
        if cached:
            return cached

        published_after = (self.now - timedelta(days=30)).isoformat().replace("+00:00", "Z")
        ids: set[str] = set()
        market_hits: set[str] = set()
        titles: dict[str, str] = {}
        duration = "short" if format == "short" else "medium"
        for market in self.markets:
            response = self.youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                order="viewCount",
                publishedAfter=published_after,
                maxResults=10,
                regionCode=market,
                relevanceLanguage="en",
                videoDuration=duration,
                safeSearch="strict",
            ).execute()
            items = response.get("items", [])
            if items:
                market_hits.add(market)
            for item in items:
                video_id = item.get("id", {}).get("videoId")
                if video_id:
                    ids.add(video_id)
                    titles[video_id] = item.get("snippet", {}).get("title", "")

        velocities: list[float] = []
        overlap_values: list[float] = []
        query_tokens = self._tokens(query)
        if ids:
            response = self.youtube.videos().list(
                part="statistics,snippet",
                id=",".join(sorted(ids)),
                maxResults=50,
            ).execute()
            for item in response.get("items", []):
                views = int(item.get("statistics", {}).get("viewCount", 0) or 0)
                published = item.get("snippet", {}).get("publishedAt")
                if published:
                    published_at = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    age_days = max(1.0, (self.now - published_at).total_seconds() / 86400)
                    velocities.append(views / age_days)
                title_tokens = self._tokens(item.get("snippet", {}).get("title", titles.get(item.get("id", ""), "")))
                if query_tokens:
                    overlap_values.append(len(query_tokens & title_tokens) / len(query_tokens))

        median_velocity = statistics.median(velocities) if velocities else 0.0
        top_velocity = max(velocities, default=0.0)
        overlap = statistics.mean(overlap_values) if overlap_values else 0.0
        supply_score = min(25.0, len(ids) * 1.25)
        median_score = min(30.0, math.log10(1 + median_velocity) * 7.5)
        top_score = min(15.0, math.log10(1 + top_velocity) * 3.0)
        market_score = min(15.0, len(market_hits) / max(1, len(self.markets)) * 15.0)
        relevance_score = min(15.0, overlap * 15.0)
        score = round(supply_score + median_score + top_score + market_score + relevance_score, 1)
        result = DemandResult(
            query=query,
            score=score,
            verdict="pass" if score >= self.threshold else "reject",
            recent_videos=len(ids),
            median_views_per_day=round(median_velocity, 2),
            top_views_per_day=round(top_velocity, 2),
            market_coverage=len(market_hits),
            title_query_overlap=round(overlap, 4),
            measured_at=utc_now(),
        )
        self.database.execute(
            """INSERT INTO topic_demand_snapshots
               (cache_key, query, format, score, verdict, result_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (key, query, format, score, result.verdict, json.dumps(asdict(result), sort_keys=True), utc_now()),
        )
        return result

    def select(self, spec: dict[str, Any]) -> tuple[dict[str, Any], DemandResult]:
        candidates = spec.get("topic_candidates") or [{
            "title": spec.get("title", spec["brief"]),
            "query": spec.get("demand_query", spec["brief"]),
            "brief": spec["brief"],
            "evidence_valid": True,
        }]
        evidence_valid = [candidate for candidate in candidates if candidate.get("evidence_valid") is True]
        if not evidence_valid:
            raise TopicDemandRejected("no evidence-valid topic candidates were supplied")
        ranked = [
            (candidate, self.evaluate(candidate.get("query") or candidate["title"], spec["format"]))
            for candidate in evidence_valid
        ]
        candidate, result = max(ranked, key=lambda item: item[1].score)
        if result.verdict != "pass":
            raise TopicDemandRejected(
                f"all evidence-valid topics failed platform demand; best score was {result.score:.1f}/{self.threshold:.1f}"
            )
        return candidate, result

    def trending_seeds(self, category_id: str = "28") -> list[dict[str, str]]:
        """Return current platform seeds for the topic planner, not copy-ready topics."""
        seeds: dict[str, dict[str, str]] = {}
        for market in self.markets:
            response = self.youtube.videos().list(
                part="snippet,statistics",
                chart="mostPopular",
                regionCode=market,
                videoCategoryId=category_id,
                maxResults=25,
            ).execute()
            for item in response.get("items", []):
                video_id = item.get("id")
                if video_id:
                    seeds.setdefault(video_id, {
                        "video_id": video_id,
                        "title": item.get("snippet", {}).get("title", ""),
                        "market": market,
                    })
        return list(seeds.values())
