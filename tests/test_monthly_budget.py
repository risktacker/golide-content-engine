import json
import tempfile
import unittest
from pathlib import Path

from golide_engine.operations.budget import BudgetPaused, MonthlyBudget
from golide_engine.operations.costs import CostTracker, Usage
from golide_engine.storage.database import Database


class MonthlyBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = Database(self.root / "state.sqlite3")
        self.db.initialize()
        pricing = self.root / "pricing.json"
        pricing.write_text(json.dumps({"models": {"image": {"fallback_per_image": 0.1}}}))
        policy = self.root / "budget.json"
        policy.write_text(json.dumps({
            "openai": {
                "monthly_cap_usd": 5,
                "monthly_reserve_usd": 0.5,
                "scheduled_allocations_usd": {"long": 0.5, "short": 0.2},
            }
        }))
        self.tracker = CostTracker(self.db, pricing)
        self.budget = MonthlyBudget(self.db, self.tracker, policy)

    def tearDown(self):
        self.temp.cleanup()

    def spec(self, production_id="short-1", format="short", **extra):
        value = {
            "id": production_id,
            "format": format,
            "concept": {"family": "science"},
            "release": {"approved": True},
            "max_cost_usd": 6,
        }
        value.update(extra)
        self.db.upsert_production(value)
        return value

    def test_scheduled_allocations_preserve_fifty_cent_buffer(self):
        short = self.spec()
        decision = self.budget.reserve(short, "image", Usage(images=1), stage="asset")
        self.assertEqual(0.2, decision.allocation_usd)
        self.assertEqual(0.1, decision.estimated_next_usd)
        snapshot = self.budget.snapshot()
        self.assertEqual(5, snapshot["cap_usd"])
        self.assertEqual(0.5, snapshot["protected_reserve_usd"])

    def test_job_pauses_before_allocation_is_exceeded(self):
        spec = self.spec()
        self.tracker.record(spec["id"], "asset-1", "openai", "image", Usage(images=1))
        self.tracker.record(spec["id"], "asset-2", "openai", "image", Usage(images=1))
        with self.assertRaises(BudgetPaused):
            self.budget.reserve(spec, "image", Usage(images=1), stage="asset-3")

    def test_independent_job_requires_explicit_budget(self):
        spec = self.spec("manual-1", budget_class="independent")
        with self.assertRaises(BudgetPaused):
            self.budget.reserve(spec, "image", Usage(images=1))

    def test_independent_job_has_separate_allocation(self):
        spec = self.spec("manual-2", budget_class="independent", openai_budget_usd=0.3)
        decision = self.budget.reserve(spec, "image", Usage(images=1))
        self.assertEqual("independent", decision.budget_class)
        self.assertEqual(0.3, decision.allocation_usd)
