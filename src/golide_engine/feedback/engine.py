from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from statistics import mean
from typing import Any

from ..storage.database import Database, utc_now


@dataclass(frozen=True)
class Observation:
    format: str
    parameters: dict[str, Any]
    views: int
    engaged_views: int
    subscribers: int
    revenue: float
    average_percentage: float


def _performance(item: Observation) -> float:
    engagement = item.engaged_views / max(item.views, 1)
    subscriber_rate = item.subscribers / max(item.views, 1) * 1000
    revenue_per_mille = item.revenue / max(item.views, 1) * 1000
    return (
        0.30 * math.log1p(item.views) + 0.25 * min(engagement, 1) * 10
        + 0.25 * min(item.average_percentage / 100, 1.5) * 10
        + 0.12 * min(subscriber_rate, 5) + 0.08 * min(revenue_per_mille, 10)
    )


class FeedbackEngine:
    def __init__(self, database: Database, minimum_sample: int = 3, shrinkage: float = 5.0):
        self.database = database
        self.minimum_sample = minimum_sample
        self.shrinkage = shrinkage

    def observations(self) -> list[Observation]:
        rows = self.database.rows(
            """SELECT p.format, p.parameters_json, SUM(a.views) views, SUM(a.engaged_views) engaged,
               SUM(a.subscribers_gained-a.subscribers_lost) subscribers, SUM(a.estimated_revenue) revenue,
               CASE WHEN SUM(a.views)>0 THEN SUM(a.average_view_percentage*a.views)/SUM(a.views) ELSE 0 END avg_pct
               FROM productions p JOIN analytics_daily a ON a.production_id=p.production_id
               GROUP BY p.production_id"""
        )
        return [Observation(row["format"], json.loads(row["parameters_json"]), int(row["views"]), int(row["engaged"]), int(row["subscribers"]), float(row["revenue"]), float(row["avg_pct"])) for row in rows]

    def recalculate(self) -> int:
        observations = self.observations()
        baselines = {fmt: mean([_performance(item) for item in observations if item.format == fmt]) for fmt in {item.format for item in observations}}
        groups: dict[tuple[str, str, str], list[float]] = defaultdict(list)
        for item in observations:
            for key, value in item.parameters.items():
                if isinstance(value, (str, int, float, bool)):
                    groups[(item.format, key, str(value))].append(_performance(item))
        count = 0
        for (fmt, key, value), scores in groups.items():
            if len(scores) < self.minimum_sample:
                continue
            raw_delta = mean(scores) - baselines[fmt]
            adjustment = max(-0.6, min(0.6, raw_delta * len(scores) / (len(scores) + self.shrinkage)))
            self.database.execute(
                """INSERT INTO feedback_factors(format, parameter_key, parameter_value, sample_size,
                   performance_score, score_adjustment, calculated_at) VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(format, parameter_key, parameter_value) DO UPDATE SET
                   sample_size=excluded.sample_size, performance_score=excluded.performance_score,
                   score_adjustment=excluded.score_adjustment, calculated_at=excluded.calculated_at""",
                (fmt, key, value, len(scores), round(mean(scores), 4), round(adjustment, 4), utc_now()),
            )
            count += 1
        return count

    def adjustment(self, format_name: str, parameters: dict[str, Any]) -> float:
        total = 0.0
        for key, value in parameters.items():
            rows = self.database.rows(
                "SELECT score_adjustment FROM feedback_factors WHERE format=? AND parameter_key=? AND parameter_value=?",
                (format_name, key, str(value)),
            )
            if rows:
                total += float(rows[0]["score_adjustment"])
        return max(-1.0, min(1.0, total))
