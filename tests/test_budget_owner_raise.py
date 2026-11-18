"""2026-11-18: an allowance the owner sets for a video raises the one saved at its first run."""
import json
import tempfile
import unittest
from pathlib import Path

from golide_engine.operations.budget import MonthlyBudget
from golide_engine.operations.costs import CostTracker
from golide_engine.storage.database import Database


class OwnerRaiseTests(unittest.TestCase):
    def test_owner_allowance_raises_the_saved_one(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = Database(root / "state.sqlite3")
            db.initialize()
            (root / "pricing.json").write_text(json.dumps({"models": {}}))
            (root / "budget.json").write_text(json.dumps({"openai": {
                "monthly_cap_usd": 35, "monthly_reserve_usd": 0, "scheduled_allocations_usd": {"long": 4, "short": 1.2}}}))
            budget = MonthlyBudget(db, CostTracker(db, root / "pricing.json"), root / "budget.json")
            spec = {"id": "short-1", "format": "short", "concept": {"family": "science"}, "release": {"approved": True},
                    "max_cost_usd": 6}
            db.upsert_production(spec)
            self.assertEqual(budget.ensure_allocation(spec), ("scheduled", 1.2))
            spec["openai_budget_usd"] = 2.2
            self.assertEqual(budget.ensure_allocation(spec), ("scheduled", 2.2))
            spec["openai_budget_usd"] = 1.0                      # never lowers what is already allowed
            self.assertEqual(budget.ensure_allocation(spec), ("scheduled", 2.2))


if __name__ == "__main__":
    unittest.main()
