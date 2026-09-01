import inspect
import unittest

from golide_engine.orchestration import production


class DurationNormalizationContractTests(unittest.TestCase):
    def test_modest_overrun_reuses_audio_and_scales_native_timings(self):
        source = inspect.getsource(production.ProductionService.run)
        self.assertIn("maximum * 1.08", source)
        self.assertIn('"atempo={tempo:.8f}"', source)
        self.assertIn('word["start"] = round(float(word["start"]) / tempo, 4)', source)
        self.assertIn("corrected.replace(narration)", source)


if __name__ == "__main__":
    unittest.main()
