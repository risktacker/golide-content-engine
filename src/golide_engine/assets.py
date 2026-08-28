from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssetRequest:
    scene_id: str
    kind: str
    query_or_prompt: str
    source: str
    estimated_cost_usd: float = 0.0


ALLOWED_SOURCES = {"public_domain", "licensed_stock", "generated_still", "original_graphic"}


def validate_asset_plan(requests: list[AssetRequest], budget_usd: float) -> list[str]:
    problems = []
    if any(request.source not in ALLOWED_SOURCES for request in requests):
        problems.append("asset source is unsupported or has unclear rights")
    if sum(request.estimated_cost_usd for request in requests) > budget_usd:
        problems.append("asset plan exceeds project budget")
    if len({request.scene_id for request in requests}) != len(requests):
        problems.append("each scene must have one canonical asset request")
    return problems

