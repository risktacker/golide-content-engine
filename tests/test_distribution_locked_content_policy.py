import json
import unittest
from pathlib import Path

from golide_engine.engine import ContentPolicy
from golide_engine.engine.content import ContentValidationError


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
        self.assertEqual(["monday", "wednesday", "friday", "sunday"], [x["day"] for x in calendar["shorts"]])
        self.assertEqual(["tuesday", "saturday"], [x["day"] for x in calendar["long_videos"]])

    def test_social_image_identity_is_locked(self):
        profile = json.loads((ROOT / "config/social-image-profile.json").read_text())
        self.assertTrue(profile["locked"])
        self.assertEqual("4:5", profile["formats"]["instagram_feed"]["aspect_ratio"])
        self.assertEqual("4:5", profile["formats"]["facebook_feed"]["aspect_ratio"])
        self.assertEqual("1:1", profile["formats"]["linkedin_feed"]["aspect_ratio"])
        self.assertEqual("1:1", profile["formats"]["x_feed"]["aspect_ratio"])
        self.assertEqual("dark-skinned / Black", profile["people"]["visible_hands_skin_tone"])
        self.assertFalse(profile["typography"]["em_dash_allowed"])
        self.assertEqual("gpt-image-2", profile["generation"]["model"])
        self.assertEqual("medium", profile["generation"]["quality"])
        self.assertEqual(1, profile["generation"]["master_concept_count"])

    def test_owner_recording_is_the_only_narration_source(self):
        providers = json.loads((ROOT / "config/providers.json").read_text())
        voice = providers["voice"]
        self.assertEqual("owner_recording", voice["provider"])
        self.assertEqual("owner_recording_only", voice["source"])
        self.assertFalse(voice["ai_voice_allowed"])
        self.assertFalse(voice["cloned_voice_allowed"])
        self.assertEqual("owner_voice_media_ref", voice["required_spec_field"])

    def test_policy_rejects_wrong_platform_route_and_bad_bridge(self):
        policy = ContentPolicy(ROOT)
        with self.assertRaises(ContentValidationError):
            policy.validate_route("long", ["youtube", "facebook"])
        with self.assertRaises(ContentValidationError):
            policy.validate_post_structure(
                ["one", "two", "three"],
                1,
                "https://marketplace.golidee.com/jobsearch/",
            )

    def test_policy_rejects_extended_dash_typography(self):
        policy = ContentPolicy(ROOT)
        with self.assertRaises(ContentValidationError):
            policy.validate_post_structure(
                ["One clean point", "This uses an em dash — blocked", "Close"],
                None,
                "",
            )


if __name__ == "__main__":
    unittest.main()
