import inspect
import unittest

from golide_engine.orchestration import production
from golide_engine.orchestration.schemas import TREND_CANDIDATES_SCHEMA


class TrendingFallbackContractTests(unittest.TestCase):
    def test_candidate_schema_requires_authoritative_source(self):
        candidate = TREND_CANDIDATES_SCHEMA["properties"]["candidates"]["items"]
        self.assertIn("authoritative_source_url", candidate["required"])
        self.assertEqual(3, TREND_CANDIDATES_SCHEMA["properties"]["candidates"]["minItems"])

    def test_production_fallback_is_budgeted_checkpointed_and_original(self):
        source = inspect.getsource(production.ProductionService.run)
        self.assertIn('self.runner.run(\n                    production_id, "trend-candidates"', source)
        self.assertIn('stage="trend-candidates"', source)
        self.assertIn("Do not copy video titles or premises.", source)
        self.assertIn("candidate, demand = gate.select(spec)", source)
        self.assertIn('"platform_seed_demand" not in item', source)
