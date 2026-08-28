import unittest

from golide_engine.scoring import LONG_WEIGHTS, SHORT_WEIGHTS, score_concept


class ScoringTests(unittest.TestCase):
    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(SHORT_WEIGHTS.values()), 1)
        self.assertAlmostEqual(sum(LONG_WEIGHTS.values()), 1)

    def test_strong_short_passes(self):
        scores = {key: 8 for key in SHORT_WEIGHTS}
        self.assertEqual(score_concept("short", scores).verdict, "produce")

    def test_weak_evidence_blocks_concept(self):
        scores = {key: 9 for key in LONG_WEIGHTS}
        scores["evidence_strength"] = 5
        result = score_concept("long", scores)
        self.assertEqual(result.verdict, "reject")
        self.assertTrue(result.blockers)


if __name__ == "__main__":
    unittest.main()
