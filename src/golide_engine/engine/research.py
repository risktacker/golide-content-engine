from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TopicCandidate:
    topic: str
    source: str
    evidence: str
    relevance: float
    freshness: float
    engagement_potential: float
    audience_fit: float
    originality_of_angle: float
    golide_relevance: float

    def score(self, weights: dict[str, float] | None = None) -> float:
        values = {
            "relevance": self.relevance,
            "freshness": self.freshness,
            "engagement_potential": self.engagement_potential,
            "audience_fit": self.audience_fit,
            "originality_of_angle": self.originality_of_angle,
            "golide_relevance": self.golide_relevance,
        }
        for key, value in values.items():
            if not 0 <= value <= 1:
                raise ValueError(f"{key} must be between 0 and 1")
        applied = weights or {key: 1.0 for key in values}
        total_weight = sum(applied.get(key, 0.0) for key in values)
        if total_weight <= 0:
            raise ValueError("topic score requires positive weights")
        return sum(values[key] * applied.get(key, 0.0) for key in values) / total_weight


def rank_topics(
    candidates: Iterable[TopicCandidate],
    weights: dict[str, float] | None = None,
) -> list[TopicCandidate]:
    """Highest evidence-backed opportunity first."""
    return sorted(candidates, key=lambda item: item.score(weights), reverse=True)


def top_topic(
    candidates: Iterable[TopicCandidate],
    weights: dict[str, float] | None = None,
) -> TopicCandidate:
    ranked = rank_topics(candidates, weights)
    if not ranked:
        raise ValueError("at least one topic candidate is required")
    return ranked[0]
