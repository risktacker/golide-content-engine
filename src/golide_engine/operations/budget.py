from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .costs import CostTracker, Usage
from ..storage.database import Database, utc_now


@dataclass(frozen=True)
class BudgetDecision:
    production_id: str
    provider: str
    budget_class: str
    allocation_usd: float
    spent_usd: float
    estimated_next_usd: float
    remaining_usd: float


class BudgetPaused(RuntimeError):
    """A resumable stop raised before a paid request can exceed its allowance."""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "openai",
        required_usd: float = 0.0,
        remaining_usd: float = 0.0,
    ):
        super().__init__(message)
        self.provider = provider
        self.required_usd = max(0.0, float(required_usd))
        self.remaining_usd = max(0.0, float(remaining_usd))


def is_provider_balance_error(exc: Exception) -> bool:
    code = str(getattr(exc, "code", "") or getattr(exc, "type", "")).lower()
    message = str(exc).lower()
    markers = (
        "insufficient_quota",
        "billing_hard_limit_reached",
        "credit balance",
        "insufficient funds",
        "payment required",
        "quota exceeded",
    )
    return any(marker in code or marker in message for marker in markers)


class MonthlyBudget:
    """Allocates and enforces provider budgets without repeating completed stages."""

    def __init__(
        self,
        database: Database,
        tracker: CostTracker,
        policy_path: str | Path,
    ):
        self.database = database
        self.tracker = tracker
        self.policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))

    @staticmethod
    def month_key() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _scheduled_cap(self) -> float:
        configured = os.getenv("GOLIDE_OPENAI_MONTHLY_CAP_USD")
        value = float(configured) if configured else float(
            self.policy["openai"].get(
                "scheduled_video_cap_usd",
                self.policy["openai"]["monthly_cap_usd"],
            )
        )
        if value < 0:
            raise ValueError("monthly OpenAI cap cannot be negative")
        return value

    def _allocation_for(self, spec: dict[str, Any], provider: str) -> tuple[str, float]:
        budget_class = str(spec.get("budget_class", "scheduled"))
        if budget_class not in {"scheduled", "independent"}:
            raise ValueError("budget_class must be scheduled or independent")
        if provider != "openai":
            explicit = float(spec.get("provider_budgets_usd", {}).get(provider, spec.get("max_cost_usd", 0)))
            return budget_class, max(0.0, explicit)
        if budget_class == "independent":
            explicit = spec.get("openai_budget_usd")
            if explicit is None or float(explicit) <= 0:
                raise BudgetPaused(
                    "independent production needs an explicit OpenAI budget after funds are loaded",
                    provider="openai",
                )
            return budget_class, float(explicit)
        allocations = self.policy["openai"]["scheduled_allocations_usd"]
        return budget_class, float(allocations[spec["format"]])

    def ensure_allocation(self, spec: dict[str, Any], provider: str = "openai") -> tuple[str, float]:
        production_id = spec["id"]
        month = self.month_key()
        rows = self.database.rows(
            """SELECT budget_class, allocated_usd FROM budget_allocations
               WHERE production_id=? AND provider=? AND month=?""",
            (production_id, provider, month),
        )
        if rows:
            budget_class = str(rows[0]["budget_class"])
            allocated = float(rows[0]["allocated_usd"])
            desired_class, desired = self._allocation_for(spec, provider)
            if budget_class == "scheduled" and desired_class == "scheduled" and desired > allocated:
                self.database.execute(
                    """UPDATE budget_allocations SET allocated_usd=?
                       WHERE production_id=? AND provider=? AND month=?""",
                    (desired, production_id, provider, month),
                )
                allocated = desired
            return budget_class, allocated
        budget_class, amount = self._allocation_for(spec, provider)
        self.database.execute(
            """INSERT INTO budget_allocations
               (production_id, provider, month, budget_class, allocated_usd, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (production_id, provider, month, budget_class, amount, utc_now()),
        )
        return budget_class, amount

    def _class_spend(self, provider: str, budget_class: str) -> float:
        rows = self.database.rows(
            """SELECT COALESCE(SUM(c.cost_usd), 0) total
               FROM cost_events c
               JOIN budget_allocations b
                 ON b.production_id=c.production_id
                AND b.provider=c.provider
                AND b.month=substr(c.created_at, 1, 7)
               WHERE c.provider=? AND b.budget_class=? AND b.month=?""",
            (provider, budget_class, self.month_key()),
        )
        return round(float(rows[0]["total"]), 6)

    def _assert_estimate_fits(
        self,
        spec: dict[str, Any],
        provider: str,
        estimated: float,
        stage: str,
    ) -> BudgetDecision:
        budget_class, allocation = self.ensure_allocation(spec, provider)
        spent = self.tracker.provider_total(spec["id"], provider)
        remaining = max(0.0, allocation - spent)
        if estimated > remaining + 1e-9:
            raise BudgetPaused(
                f"{stage} needs about ${estimated:.4f}; {provider} job allocation has ${remaining:.4f} left",
                provider=provider,
                required_usd=estimated,
                remaining_usd=remaining,
            )
        if provider == "openai" and budget_class == "scheduled":
            cap = self._scheduled_cap()
            monthly_spent = self._class_spend("openai", "scheduled")
            monthly_remaining = max(0.0, cap - monthly_spent)
            if estimated > monthly_remaining + 1e-9:
                raise BudgetPaused(
                    f"{stage} needs about ${estimated:.4f}; monthly OpenAI ceiling has ${monthly_remaining:.4f} left",
                    provider="openai",
                    required_usd=estimated,
                    remaining_usd=monthly_remaining,
                )
        self.database.execute(
            """UPDATE budget_pauses SET resolved_at=?
               WHERE production_id=? AND provider=? AND resolved_at IS NULL""",
            (utc_now(), spec["id"], provider),
        )
        return BudgetDecision(
            spec["id"], provider, budget_class, allocation, spent, estimated, remaining
        )

    def reserve(
        self,
        spec: dict[str, Any],
        model: str,
        usage: Usage,
        *,
        provider: str = "openai",
        stage: str = "paid-request",
    ) -> BudgetDecision:
        estimated = self.tracker.estimate(provider, model, usage)
        return self._assert_estimate_fits(spec, provider, estimated, stage)

    def reserve_batch(
        self,
        spec: dict[str, Any],
        requests: list[tuple[str, Usage]],
        *,
        provider: str = "openai",
        stage: str = "paid-batch",
    ) -> BudgetDecision:
        """Preflight a whole planned provider batch before the first paid request fires."""
        if not requests:
            return self._assert_estimate_fits(spec, provider, 0.0, stage)
        estimated = round(
            sum(self.tracker.estimate(provider, model, usage) for model, usage in requests),
            6,
        )
        return self._assert_estimate_fits(spec, provider, estimated, stage)

    def snapshot(self) -> dict[str, float]:
        cap = self._scheduled_cap()
        spent = self._class_spend("openai", "scheduled")
        reserve = float(self.policy["openai"]["monthly_reserve_usd"])
        return {
            "cap_usd": cap,
            "spent_usd": spent,
            "remaining_usd": round(max(0.0, cap - spent), 6),
            "protected_reserve_usd": reserve,
        }
