import unittest
from pathlib import Path

from golide_engine.policy import load_policy


class PolicyTests(unittest.TestCase):
    def test_review_rules_are_locked(self):
        policy = load_policy(Path("config/production-policy.json"))
        self.assertTrue(policy["loop"]["required"])
        self.assertTrue(policy["captions"]["visual_labels"])
        self.assertTrue(policy["captions"]["spoken_captions"])
        self.assertTrue(policy["music"]["required"])
        self.assertEqual(policy["shorts"]["weekly_count"], 3)
        self.assertTrue(policy["long_form"]["first_pipeline_upload"])
        self.assertEqual(policy["voice"]["age_character"], "mature-adult")
        self.assertEqual(policy["visuals"]["composition"]["default"], "center-stage-with-negative-space")
        self.assertTrue(policy["visuals"]["avatar"]["face_consistency_required"])


if __name__ == "__main__":
    unittest.main()
