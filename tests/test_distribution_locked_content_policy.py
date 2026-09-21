import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LockedContentPolicyTests(unittest.TestCase):
    def test_platform_routing_is_locked(self):
        policy = json.loads((ROOT / "config/content-routing.json").read_text())
        self.assertEqual(["instagram", "facebook", "linkedin", "x"], policy["content_types"]["post"]["platforms"])
        self.assertEqual(["instagram", "facebook", "youtube"], policy["content_types"]["short"]["platforms"])
        self.assertEqual(["youtube"], policy["content_types"]["long_video"]["platforms"])
        self.assertFalse(policy["pinterest"]["native_engine_integration"])

    def test_weekly_cadence_is_locked(self):
        calendar = json.loads((ROOT / "config/content-calendar.json").read_text())
        self.assertEqual(14, calendar["weekly_totals"]["core_posts"])
        self.assertEqual(4, calendar["weekly_totals"]["shorts"])
        self.assertEqual(2, calendar["weekly_totals"]["long_videos"])
        self.assertEqual(2, len(calendar["daily_posts"]))

    def test_social_image_identity_is_locked(self):
        profile = json.loads((ROOT / "config/social-image-profile.json").read_text())
        self.assertTrue(profile["locked"])
        self.assertEqual("4:5", profile["formats"]["instagram_feed"]["aspect_ratio"])
        self.assertEqual("1:1", profile["formats"]["linkedin_feed"]["aspect_ratio"])
        self.assertEqual("dark-skinned / Black", profile["people"]["visible_hands_skin_tone"])
        self.assertFalse(profile["typography"]["em_dash_allowed"])
