from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from .storage.database import Database
from .operations.retry import with_retry


_DURATION = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def _duration_seconds(value: str) -> int:
    match = _DURATION.match(value or "")
    if not match:
        return 0
    parts = {key: int(number or 0) for key, number in match.groupdict().items()}
    return parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]


def _video_metadata(youtube: Any, video_ids: list[str]) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for offset in range(0, len(video_ids), 50):
        chunk = video_ids[offset:offset + 50]
        response = with_retry(
            lambda chunk=chunk: youtube.videos().list(
                part="snippet,contentDetails", id=",".join(chunk), maxResults=50
            ).execute()
        )
        for item in response.get("items", []):
            metadata[item["id"]] = item
    return metadata


def build_studio_analytics_payload(
    database: Database,
    youtube: Any,
    channel_id: str,
    *,
    today: date | None = None,
    lookback_days: int = 90,
) -> dict[str, Any]:
    """Build the bounded, privacy-safe Studio analytics contract from engine state."""
    today = today or date.today()
    since = (today - timedelta(days=lookback_days)).isoformat()
    rows = database.rows(
        """SELECT a.*, p.format production_format, p.title production_title,
                  p.scheduled_at, p.parameters_json
           FROM analytics_daily a
           LEFT JOIN productions p
             ON p.production_id=a.production_id OR p.youtube_video_id=a.youtube_video_id
           WHERE a.day >= ?
           ORDER BY a.day DESC, a.views DESC
           LIMIT 250""",
        (since,),
    )
    video_ids = list(dict.fromkeys(str(row["youtube_video_id"]) for row in rows))
    metadata = _video_metadata(youtube, video_ids) if video_ids else {}

    daily_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        daily_buckets[str(row["day"])].append(row)

    daily = []
    for day_key in sorted(daily_buckets):
        bucket = daily_buckets[day_key]
        views = sum(int(row["views"]) for row in bucket)
        watch_seconds = sum(
            int(row["views"]) * float(row["average_view_duration"]) for row in bucket
        )
        weighted_percentage = sum(
            int(row["views"]) * float(row["average_view_percentage"]) for row in bucket
        )
        daily.append({
            "date": day_key,
            "views": views,
            "engagedViews": sum(int(row["engaged_views"]) for row in bucket),
            "estimatedMinutesWatched": max(0, round(watch_seconds / 60)),
            "averageViewDurationSeconds": max(0, round(watch_seconds / views)) if views else 0,
            "averageViewPercentage": round(weighted_percentage / views, 2) if views else 0,
            "subscribersGained": sum(int(row["subscribers_gained"]) for row in bucket),
            "subscribersLost": sum(int(row["subscribers_lost"]) for row in bucket),
            # The current YouTube Analytics query does not expose channel revenue.
            "estimatedRevenueUsd": None,
        })

    videos = []
    for row in rows:
        video_id = str(row["youtube_video_id"])
        item = metadata.get(video_id, {})
        snippet = item.get("snippet", {})
        duration = _duration_seconds(item.get("contentDetails", {}).get("duration", ""))
        production_format = row.get("production_format")
        published_at = (
            snippet.get("publishedAt")
            or row.get("scheduled_at")
            or f"{row['day']}T00:00:00Z"
        )
        parameters = None
        if row.get("parameters_json"):
            try:
                parameters = json.loads(row["parameters_json"])
            except (TypeError, json.JSONDecodeError):
                parameters = None
        row_views = int(row["views"])
        videos.append({
            "videoId": video_id,
            "title": str(snippet.get("title") or row.get("production_title") or video_id)[:200],
            "format": production_format if production_format in {"short", "long"} else (
                "short" if 0 < duration <= 180 else "long"
            ),
            "isGolide": bool(row.get("production_id")),
            "publishedAt": published_at,
            "snapshotDate": str(row["day"]),
            "views": row_views,
            "engagedViews": int(row["engaged_views"]),
            "estimatedMinutesWatched": max(
                0, round(row_views * float(row["average_view_duration"]) / 60)
            ),
            "averageViewDurationSeconds": max(0, round(float(row["average_view_duration"]))),
            "averageViewPercentage": round(float(row["average_view_percentage"]), 2),
            "subscribersGained": int(row["subscribers_gained"]),
            "likes": int(row["likes"]),
            "comments": int(row["comments"]),
            "shares": int(row["shares"]),
            "estimatedRevenueUsd": None,
            **({"generationParameters": parameters} if parameters is not None else {}),
        })

    return {"channelId": channel_id, "daily": daily[-100:], "videos": videos[:250]}
