from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LIFECYCLE_WEIGHT = {
    "IDEA": 20,
    "PRE_LAUNCH": 75,
    "NEW": 100,
    "ACTIVE": 55,
    "MATURE": 20,
    "PAUSED": 0,
}


@dataclass(frozen=True)
class ProductRecord:
    id: str
    name: str
    lifecycle_status: str
    target_audience: str
    problem_solved: str
    marketplace_url: str
    keywords: tuple[str, ...]
    creator_niches: tuple[str, ...]
    target_geographies: tuple[str, ...]
    priority: int
    affiliate_rate: int
    launch_date: str
    partner_coverage: int
    recent_post_count: int
    paused: bool

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ProductRecord":
        return cls(
            id=str(raw.get("id", "")).strip(),
            name=str(raw.get("name", "")).strip(),
            lifecycle_status=str(raw.get("lifecycle_status", "ACTIVE")).strip().upper(),
            target_audience=str(raw.get("target_audience", "")).strip(),
            problem_solved=str(raw.get("problem_solved", "")).strip(),
            marketplace_url=str(raw.get("marketplace_url", "")).strip(),
            keywords=tuple(str(value).strip() for value in raw.get("keywords", []) if str(value).strip()),
            creator_niches=tuple(str(value).strip() for value in raw.get("creator_niches", []) if str(value).strip()),
            target_geographies=tuple(str(value).strip() for value in raw.get("target_geographies", []) if str(value).strip()),
            priority=max(0, min(100, int(raw.get("priority", 50) or 50))),
            affiliate_rate=max(0, min(100, int(raw.get("affiliate_rate", 0) or 0))),
            launch_date=str(raw.get("launch_date", "")).strip(),
            partner_coverage=max(0, int(raw.get("partner_coverage", 0) or 0)),
            recent_post_count=max(0, int(raw.get("recent_post_count", 0) or 0)),
            paused=bool(raw.get("paused", False)),
        )


class ProductRegistry:
    """Lightweight automation snapshot of the Marketplace product registry."""

    MODES = {"brand", "specific_product", "auto_product"}

    def __init__(self, path: str | Path = "config/product-registry.json"):
        self.path = Path(path)
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.version = int(payload.get("version", 1))
        self.products = tuple(
            product for product in (ProductRecord.from_dict(item) for item in payload.get("products", []))
            if product.id and product.name
        )

    def get(self, product_id: str) -> ProductRecord:
        key = str(product_id).strip()
        for product in self.products:
            if product.id == key:
                return product
        raise ValueError(f"unknown product id: {key}")

    def eligible(self) -> tuple[ProductRecord, ...]:
        return tuple(
            product for product in self.products
            if not product.paused and product.lifecycle_status != "PAUSED"
        )

    @staticmethod
    def weight(product: ProductRecord) -> int:
        lifecycle = LIFECYCLE_WEIGHT.get(product.lifecycle_status, 40)
        coverage_gap = max(0, 40 - product.partner_coverage) * 2
        posting_gap = max(0, 8 - product.recent_post_count) * 5
        return max(1, lifecycle + product.priority + coverage_gap + posting_gap)

    def choose_auto(self, *, seed: str | int | None = None) -> ProductRecord:
        candidates = self.eligible()
        if not candidates:
            raise ValueError("no active products are available for auto product selection")
        rng = random.Random(str(seed)) if seed is not None else random.SystemRandom()
        weights = [self.weight(product) for product in candidates]
        return rng.choices(candidates, weights=weights, k=1)[0]

    def resolve(
        self,
        mode: str,
        *,
        product_id: str = "",
        seed: str | int | None = None,
    ) -> ProductRecord | None:
        normalized = str(mode or "brand").strip().lower()
        if normalized not in self.MODES:
            raise ValueError(f"unsupported product mode: {normalized}")
        if normalized == "brand":
            if product_id:
                raise ValueError("brand posts cannot carry a product id")
            return None
        if normalized == "specific_product":
            if not product_id:
                raise ValueError("specific_product requires product_id")
            product = self.get(product_id)
            if product.paused or product.lifecycle_status == "PAUSED":
                raise ValueError("paused products cannot be selected for distribution")
            return product
        return self.choose_auto(seed=seed)

    def snapshot(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "products": [
                {
                    "id": product.id,
                    "name": product.name,
                    "lifecycle_status": product.lifecycle_status,
                    "target_audience": product.target_audience,
                    "problem_solved": product.problem_solved,
                    "marketplace_url": product.marketplace_url,
                    "priority": product.priority,
                    "affiliate_rate": product.affiliate_rate,
                    "weight": self.weight(product),
                    "paused": product.paused,
                }
                for product in self.products
            ],
        }
