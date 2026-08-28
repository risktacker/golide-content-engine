from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


SHORT_WEIGHTS = {
    "scroll_stop": 0.20,
    "visual_payoff": 0.16,
    "curiosity_gap": 0.14,
    "retention_design": 0.14,
    "broad_relevance": 0.10,
    "evidence_strength": 0.10,
    "novelty": 0.08,
    "replay_or_loop": 0.05,
    "revenue_fit": 0.03,
}

LONG_WEIGHTS = {
    "click_promise": 0.16,
    "thumbnail_title_fit": 0.14,
    "narrative_engine": 0.14,
    "visual_depth": 0.12,
    "evidence_strength": 0.12,
    "retention_design": 0.12,
    "broad_relevance": 0.08,
    "novelty": 0.06,
    "revenue_fit": 0.06,
}


@dataclass(frozen=True)
class ScoreResult:
    format: str
    total: float
    verdict: str
    dimensions: dict[str, float]
    blockers: tuple[str, ...]


def score_concept(format: str, dimensions: Mapping[str, float]) -> ScoreResult:
    weights = SHORT_WEIGHTS if format == "short" else LONG_WEIGHTS if format == "long" else None
    if weights is None:
        raise ValueError("format must be 'short' or 'long'")
    unknown = set(dimensions) - set(weights)
    missing = set(weights) - set(dimensions)
    if unknown or missing:
        raise ValueError(f"score dimensions mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}")
    normalized = {key: float(value) for key, value in dimensions.items()}
    if any(value < 0 or value > 10 for value in normalized.values()):
        raise ValueError("every score must be between 0 and 10")

    blockers = []
    for gate in ("evidence_strength", "visual_payoff" if format == "short" else "thumbnail_title_fit"):
        if normalized[gate] < 6:
            blockers.append(f"{gate} must score at least 6")
    total = round(sum(normalized[key] * weights[key] for key in weights) * 10, 1)
    verdict = "produce" if total >= 78 and not blockers else "develop" if total >= 65 else "reject"
    if blockers:
        verdict = "reject"
    return ScoreResult(format, total, verdict, normalized, tuple(blockers))

