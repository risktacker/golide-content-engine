from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from ..operations.retry import with_retry
from ..storage.database import Database, utc_now


def _fingerprint(video: Path, metadata: dict) -> str:
    digest = hashlib.sha256()
    digest.update(video.read_bytes())
    digest.update(json.dumps(metadata, sort_keys=True).encode())
    return digest.hexdigest()


class YouTubeUploader:
    def __init__(self, youtube, database: Database, expected_channel_id: str):
        self.youtube = youtube
        self.database = database
        self.expected_channel_id = expected_channel_id

    def _assert_release(self, release: dict) -> None:
        if os.getenv("GOLIDE_ENABLE_YOUTUBE_UPLOAD") != "1":
            raise RuntimeError("YouTube upload lock is closed")
        if not release.get("approved"):
            raise RuntimeError("release is not approved")
        if release.get("qa", {}).get("passed") is not True:
            raise RuntimeError("release QA has not passed")
        if release.get("channel_id") != self.expected_channel_id:
            raise RuntimeError("release targets the wrong YouTube channel")

    def upload_private(self, production_id: str, video: Path, thumbnail: Path, metadata: dict, release: dict) -> str:
        self._assert_release(release)
        fingerprint = _fingerprint(video, metadata)
        prior = self.database.rows("SELECT youtube_video_id FROM uploads WHERE request_fingerprint=?", (fingerprint,))
        if prior and prior[0]["youtube_video_id"]:
            return str(prior[0]["youtube_video_id"])
        try:
            from googleapiclient.http import MediaFileUpload
        except ImportError as exc:
            raise RuntimeError("install production dependencies") from exc
        body = {
            "snippet": {
                "title": metadata["title"], "description": metadata["description"],
                "tags": metadata.get("tags", []), "categoryId": str(metadata.get("category_id", 28)),
                "defaultLanguage": metadata.get("video_language", "en"),
            },
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": bool(metadata["altered_content"])},
        }
        request = self.youtube.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(str(video), chunksize=-1, resumable=True))
        response = with_retry(request.execute)
        video_id = response["id"]
        with_retry(lambda: self.youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(thumbnail))).execute())
        self.database.execute(
            """INSERT INTO uploads(production_id, youtube_video_id, privacy_status, upload_status, request_fingerprint, updated_at)
               VALUES (?, ?, 'private', 'uploaded', ?, ?)
               ON CONFLICT(production_id) DO UPDATE SET youtube_video_id=excluded.youtube_video_id,
               privacy_status='private', upload_status='uploaded', updated_at=excluded.updated_at""",
            (production_id, video_id, fingerprint, utc_now()),
        )
        self.database.execute(
            "UPDATE productions SET youtube_video_id=?, status='uploaded_private', updated_at=? WHERE production_id=?",
            (video_id, utc_now(), production_id),
        )
        return video_id

    def schedule(self, production_id: str, video_id: str, publish_at: str, release: dict) -> None:
        self._assert_release(release)
        instant = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
        if instant.astimezone(timezone.utc) <= datetime.now(timezone.utc):
            raise ValueError("publish_at must be in the future")
        body = {"id": video_id, "status": {"privacyStatus": "private", "publishAt": instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"), "selfDeclaredMadeForKids": False}}
        with_retry(lambda: self.youtube.videos().update(part="status", body=body).execute())
        self.database.execute(
            "UPDATE uploads SET privacy_status='private', scheduled_at=?, upload_status='scheduled', updated_at=? WHERE production_id=?",
            (publish_at, utc_now(), production_id),
        )
        self.database.execute(
            "UPDATE productions SET status='scheduled', scheduled_at=?, updated_at=? WHERE production_id=?",
            (publish_at, utc_now(), production_id),
        )
