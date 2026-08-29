import json
import tempfile
import unittest
from pathlib import Path

from golide_engine.operations.costs import CostTracker, UnknownPriceError, Usage
from golide_engine.storage.database import Database


class StorageAndCostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = Database(self.root / "state.sqlite3")
        self.database.initialize()
        self.spec = {
            "id": "p1", "format": "short", "title": "Test",
            "concept": {"family": "science"}, "generation_parameters": {"hook_type": "question"},
            "release": {"approved": True, "scheduled_at": "2026-09-07T13:00:00Z"},
        }
        self.database.upsert_production(self.spec)

    def tearDown(self):
        self.temp.cleanup()

    def test_production_parameters_are_stored(self):
        row = self.database.rows("SELECT * FROM productions")[0]
        self.assertEqual("question", json.loads(row["parameters_json"])["hook_type"])

    def test_token_cost_avoids_double_charging_cached_tokens(self):
        pricing = self.root / "pricing.json"
        pricing.write_text(json.dumps({"models": {"model": {
            "input_per_million_tokens": 10, "cached_input_per_million_tokens": 1,
            "output_per_million_tokens": 20,
        }}}))
        tracker = CostTracker(self.database, pricing)
        cost = tracker.record("p1", "script", "provider", "model", Usage(
            input_tokens=1_000_000, cached_input_tokens=200_000, output_tokens=100_000,
        ))
        self.assertEqual(10.2, cost)
        self.assertEqual(10.2, tracker.total("p1"))

    def test_zero_rate_blocks_paid_stage(self):
        pricing = self.root / "pricing.json"
        pricing.write_text(json.dumps({"models": {"image": {"fallback_per_image": 0}}}))
        with self.assertRaises(UnknownPriceError):
            CostTracker(self.database, pricing).estimate("provider", "image", Usage(images=1))
