from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..storage.database import Database, utc_now


class UnknownPriceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    images: int = 0
    audio_minutes: float = 0
    characters: int = 0
    tool_calls: int = 0


class CostTracker:
    def __init__(self, database: Database, pricing_path: str | Path):
        self.database = database
        self.pricing = json.loads(Path(pricing_path).read_text(encoding="utf-8"))

    def estimate(self, provider: str, model: str, usage: Usage) -> float:
        try:
            rate = self.pricing["models"][model]
        except KeyError as exc:
            raise UnknownPriceError(f"no pricing configured for {provider}/{model}") from exc
        values = {
            "input_per_million_tokens": max(0, usage.input_tokens - usage.cached_input_tokens) / 1_000_000,
            "cached_input_per_million_tokens": usage.cached_input_tokens / 1_000_000,
            "output_per_million_tokens": usage.output_tokens / 1_000_000,
            "fallback_per_image": usage.images,
            "fallback_per_minute": usage.audio_minutes,
            "fallback_per_million_characters": usage.characters / 1_000_000,
            "per_tool_call": usage.tool_calls,
        }
        used = {key: amount for key, amount in values.items() if amount}
        if any(float(rate.get(key, 0)) <= 0 for key in used):
            raise UnknownPriceError(f"non-zero pricing required for {provider}/{model}: {sorted(used)}")
        return round(sum(amount * float(rate.get(key, 0)) for key, amount in values.items()), 6)

    def require_rate(self, model: str, rate_key: str) -> float:
        try:
            value = float(self.pricing["models"][model][rate_key])
        except (KeyError, TypeError, ValueError) as exc:
            raise UnknownPriceError(f"missing {rate_key} price for {model}") from exc
        if value <= 0:
            raise UnknownPriceError(f"{rate_key} price for {model} must be refreshed before production")
        return value

    def monthly_characters(self, provider: str) -> int:
        month = utc_now()[:7]
        rows = self.database.rows(
            """SELECT COALESCE(SUM(characters), 0) total
               FROM cost_events
               WHERE provider=? AND substr(created_at, 1, 7)=?""",
            (provider, month),
        )
        return int(rows[0]["total"])

    def require_monthly_character_capacity(self, provider: str, characters: int, limit: int) -> None:
        if characters < 1:
            raise ValueError("character reservation must be positive")
        projected = self.monthly_characters(provider) + characters
        if projected > limit:
            raise RuntimeError(
                f"{provider} monthly character guard would reach {projected:,}; limit is {limit:,}"
            )

    def record(self, production_id: str, stage: str, provider: str, model: str, usage: Usage, request_id: str | None = None) -> float:
        cost = self.estimate(provider, model, usage)
        self.database.execute(
            """INSERT INTO cost_events
               (production_id, stage, provider, model, input_units, cached_input_units,
                output_units, images, audio_minutes, characters, cost_usd,
                provider_request_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                production_id, stage, provider, model, usage.input_tokens,
                usage.cached_input_tokens, usage.output_tokens, usage.images,
                usage.audio_minutes, usage.characters, cost, request_id, utc_now(),
            ),
        )
        return cost

    def provider_total(self, production_id: str, provider: str) -> float:
        rows = self.database.rows(
            "SELECT COALESCE(SUM(cost_usd), 0) total FROM cost_events WHERE production_id=? AND provider=?",
            (production_id, provider),
        )
        return round(float(rows[0]["total"]), 6)

    def monthly_total(self, provider: str) -> float:
        month = utc_now()[:7]
        rows = self.database.rows(
            """SELECT COALESCE(SUM(cost_usd), 0) total
               FROM cost_events
               WHERE provider=? AND substr(created_at, 1, 7)=?""",
            (provider, month),
        )
        return round(float(rows[0]["total"]), 6)

    def total(self, production_id: str) -> float:
        rows = self.database.rows("SELECT COALESCE(SUM(cost_usd), 0) total FROM cost_events WHERE production_id=?", (production_id,))
        return round(float(rows[0]["total"]), 6)
