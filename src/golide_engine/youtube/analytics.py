from __future__ import annotations

import json
from datetime import date, timedelta

from ..operations.retry import with_retry
from ..storage.database import Database, utc_now

METRICS = (
    "views", "engagedViews", "likes", "comments", "shares", "subscribersGained",
    "subscribersLost", "averageViewDuration", "averageViewPercentage", "estimatedRevenue",
)


class AnalyticsCollector:
    def __init__(self, analytics, database: Database):
        self.analytics = analytics
        self.database = database

    def collect(self, start: date, end: date) -> int:
        response = with_retry(lambda: self.analytics.reports().query(
            ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(),
            dimensions="day,video", metrics=",".join(METRICS), sort="day,video",
        ).execute())
        headers = [item["name"] for item in response.get("columnHeaders", [])]
        count = 0
        for values in response.get("rows", []):
            row = dict(zip(headers, values))
            production = self.database.rows("SELECT production_id FROM productions WHERE youtube_video_id=?", (row["video"],))
            production_id = production[0]["production_id"] if production else None
            self.database.execute(
                """INSERT INTO analytics_daily
                   (day, youtube_video_id, production_id, views, engaged_views, likes, comments, shares,
                    subscribers_gained, subscribers_lost, average_view_duration, average_view_percentage,
                    estimated_revenue, raw_json, collected_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(day, youtube_video_id) DO UPDATE SET
                    views=excluded.views, engaged_views=excluded.engaged_views, likes=excluded.likes,
                    comments=excluded.comments, shares=excluded.shares,
                    subscribers_gained=excluded.subscribers_gained, subscribers_lost=excluded.subscribers_lost,
                    average_view_duration=excluded.average_view_duration,
                    average_view_percentage=excluded.average_view_percentage,
                    estimated_revenue=excluded.estimated_revenue, raw_json=excluded.raw_json,
                    collected_at=excluded.collected_at""",
                (row["day"], row["video"], production_id, int(row.get("views", 0)), int(row.get("engagedViews", 0)),
                 int(row.get("likes", 0)), int(row.get("comments", 0)), int(row.get("shares", 0)),
                 int(row.get("subscribersGained", 0)), int(row.get("subscribersLost", 0)),
                 float(row.get("averageViewDuration", 0)), float(row.get("averageViewPercentage", 0)),
                 float(row.get("estimatedRevenue", 0)), json.dumps(row, sort_keys=True), utc_now()),
            )
            count += 1
        return count

    def collect_daily(self, today: date | None = None, lookback_days: int = 3) -> int:
        today = today or date.today()
        end = today - timedelta(days=1)
        return self.collect(end - timedelta(days=lookback_days - 1), end)
