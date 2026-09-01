import unittest
from datetime import date

from golide_engine.studio_analytics import (
    _duration_seconds,
    build_studio_analytics_payload,
)


class _Execute:
    def __init__(self, value):
        self.value = value

    def execute(self):
        return self.value


class _Videos:
    def list(self, **kwargs):
        return _Execute({"items": [{
            "id": "video123",
            "snippet": {
                "title": "A GOLIDE explainer",
                "publishedAt": "2026-08-30T12:00:00Z",
            },
            "contentDetails": {"duration": "PT2M30S"},
        }]})


class _YouTube:
    def videos(self):
        return _Videos()


class _Database:
    def rows(self, query, parameters=()):
        return [{
            "day": "2026-08-31",
            "youtube_video_id": "video123",
            "production_id": "golide-short-1",
            "views": 120,
            "engaged_views": 90,
            "likes": 12,
            "comments": 3,
            "shares": 2,
            "subscribers_gained": 4,
            "subscribers_lost": 1,
            "average_view_duration": 45.0,
            "average_view_percentage": 62.5,
            "estimated_revenue": 0.0,
            "production_format": "short",
            "production_title": "Fallback",
            "scheduled_at": None,
            "parameters_json": '{"motion_intensity":"premium"}',
        }]


class StudioAnalyticsTests(unittest.TestCase):
    def test_duration_parser(self):
        self.assertEqual(150, _duration_seconds("PT2M30S"))

    def test_payload_matches_studio_contract_without_false_revenue(self):
        payload = build_studio_analytics_payload(
            _Database(), _YouTube(), "UCqaXVBSBz7iQsRHOupKt-3w",
            today=date(2026, 9, 1),
        )
        self.assertEqual(1, len(payload["daily"]))
        self.assertEqual(90, payload["daily"][0]["estimatedMinutesWatched"])
        self.assertIsNone(payload["daily"][0]["estimatedRevenueUsd"])
        self.assertEqual("short", payload["videos"][0]["format"])
        self.assertTrue(payload["videos"][0]["isGolide"])
        self.assertEqual(
            {"motion_intensity": "premium"},
            payload["videos"][0]["generationParameters"],
        )


if __name__ == "__main__":
    unittest.main()
