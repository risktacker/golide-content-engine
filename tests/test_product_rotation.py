from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from golide_engine.engine.products import ProductRecord, ProductRegistry


class ProductRotationTests(unittest.TestCase):
    def record(self, *, lifecycle: str, priority: int = 50, coverage: int = 0, posts: int = 0, paused: bool = False):
        return ProductRecord(
            id=lifecycle.lower(),
            name=lifecycle,
            lifecycle_status=lifecycle,
            target_audience="audience",
            problem_solved="problem",
            marketplace_url="https://marketplace.golidee.com/test",
            keywords=(),
            creator_niches=(),
            target_geographies=(),
            priority=priority,
            affiliate_rate=80,
            launch_date="",
            partner_coverage=coverage,
            recent_post_count=posts,
            paused=paused,
        )

    def test_new_and_undercovered_products_receive_higher_weight(self):
        new = self.record(lifecycle="NEW", priority=70, coverage=2, posts=0)
        mature = self.record(lifecycle="MATURE", priority=50, coverage=40, posts=8)
        self.assertGreater(ProductRegistry.weight(new), ProductRegistry.weight(mature))

    def test_paused_products_are_never_auto_selected(self):
        payload = {
            "version": 1,
            "products": [
                {
                    "id": "paused",
                    "name": "Paused",
                    "lifecycle_status": "PAUSED",
                    "marketplace_url": "https://marketplace.golidee.com/paused",
                    "priority": 100,
                    "paused": True,
                },
                {
                    "id": "active",
                    "name": "Active",
                    "lifecycle_status": "ACTIVE",
                    "marketplace_url": "https://marketplace.golidee.com/active",
                    "priority": 1,
                    "paused": False,
                },
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "products.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            registry = ProductRegistry(path)
            for seed in range(30):
                self.assertEqual("active", registry.choose_auto(seed=seed).id)

    def test_specific_product_and_brand_modes_are_explicit(self):
        registry = ProductRegistry(Path(__file__).resolve().parents[1] / "config/product-registry.json")
        self.assertIsNone(registry.resolve("brand"))
        selected = registry.resolve("specific_product", product_id="job-search-conversion-system")
        self.assertEqual("job-search-conversion-system", selected.id)


if __name__ == "__main__":
    unittest.main()
