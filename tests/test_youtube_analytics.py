from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from golide_engine.storage.database import Database
from golide_engine.youtube.analytics import AnalyticsCollector, TOP_VIDEOS_LIMIT


class FakeAnalytics:
    def __init__(self):
        self.queries: list[dict[str, object]] = []
        self.current_query: dict[str, object] = {}

    def reports(self):
        return self

    def query(self, **kwargs):
        self.current_query = kwargs
        self.queries.append(kwargs)
        return self

    def execute(self):
        day = str(self.current_query["startDate"])
        views = 12 if day == "2026-08-27" else 8
        return {
            "columnHeaders": [
                {"name": "video"},
                {"name": "views"},
                {"name": "engagedViews"},
                {"name": "likes"},
                {"name": "comments"},
                {"name": "shares"},
                {"name": "subscribersGained"},
                {"name": "subscribersLost"},
                {"name": "averageViewDuration"},
                {"name": "averageViewPercentage"},
            ],
            "rows": [["video-1", views, 7, 3, 1, 2, 1, 0, 18.5, 64.2]],
        }


class AnalyticsCollectorTests(unittest.TestCase):
    def test_collect_queries_each_day_with_supported_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "golide.sqlite3")
            database.initialize()
            analytics = FakeAnalytics()
            collector = AnalyticsCollector(analytics, database)

            count = collector.collect(date(2026, 8, 27), date(2026, 8, 28))

            self.assertEqual(count, 2)
            self.assertEqual(len(analytics.queries), 2)
            self.assertEqual(
                [query["startDate"] for query in analytics.queries],
                ["2026-08-27", "2026-08-28"],
            )
            for query in analytics.queries:
                self.assertEqual(query["startDate"], query["endDate"])
                self.assertEqual(query["dimensions"], "video")
                self.assertEqual(query["sort"], "-views")
                self.assertEqual(query["maxResults"], TOP_VIDEOS_LIMIT)
                self.assertNotIn("estimatedRevenue", str(query["metrics"]))

            rows = database.rows(
                """SELECT day, youtube_video_id, views, engaged_views,
                          estimated_revenue
                   FROM analytics_daily ORDER BY day"""
            )
            self.assertEqual(
                rows,
                [
                    {
                        "day": "2026-08-27",
                        "youtube_video_id": "video-1",
                        "views": 12,
                        "engaged_views": 7,
                        "estimated_revenue": 0.0,
                    },
                    {
                        "day": "2026-08-28",
                        "youtube_video_id": "video-1",
                        "views": 8,
                        "engaged_views": 7,
                        "estimated_revenue": 0.0,
                    },
                ],
            )


if __name__ == "__main__":
    unittest.main()
