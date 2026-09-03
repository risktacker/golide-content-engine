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


def _initial_release_status(release: dict) -> tuple[dict, str, str]:
    """Set final visibility during upload so youtube.upload scope is sufficient."""
    status = {"privacyStatus": "private", "selfDeclaredMadeForKids": False}
    publish_at = release.get("scheduled_at")
    if not publish_at:
        return status, "uploaded_private", "private"
    instant = datetime.fromisoformat(str(publish_at).replace("Z", "+00:00"))
    if instant.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        status["privacyStatus"] = "public"
        return status, "published", "public"
    status["publishAt"] = instant.astimezone(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    return status, "scheduled", "private"


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
        force_reupload = (
            release.get("force_reupload") is True
            or os.getenv("GOLIDE_FORCE_REUPLOAD_PRODUCTION_ID") == production_id
        )
        if prior and prior[0]["youtube_video_id"] and not force_reupload:
            return str(prior[0]["youtube_video_id"])

        # A forced corrected upload always creates a brand-new YouTube video.
        # Cleanup of any obsolete upload is intentionally separate and must never
        # block publication of the corrected render.
        try:
            from googleapiclient.http import MediaFileUpload
        except ImportError as exc:
            raise RuntimeError("install production dependencies") from exc
        status, upload_state, privacy = _initial_release_status(release)
        status["containsSyntheticMedia"] = bool(metadata["altered_content"])
        body = {
            "snippet": {
                "title": metadata["title"], "description": metadata["description"],
                "tags": metadata.get("tags", []), "categoryId": str(metadata.get("category_id", 28)),
                "defaultLanguage": metadata.get("video_language", "en"),
            },
            "status": status,
        }
        request = self.youtube.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(str(video), chunksize=-1, resumable=True))
        response = with_retry(request.execute)
        video_id = response["id"]
        with_retry(lambda: self.youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(thumbnail))).execute())
        uploaded_at = utc_now()
        self.database.execute(
            """INSERT INTO uploads(production_id, youtube_video_id, privacy_status, upload_status, request_fingerprint, uploaded_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(production_id) DO UPDATE SET youtube_video_id=excluded.youtube_video_id,
               privacy_status=excluded.privacy_status, upload_status=excluded.upload_status,
               request_fingerprint=excluded.request_fingerprint, uploaded_at=excluded.uploaded_at,
               updated_at=excluded.updated_at""",
            (production_id, video_id, privacy, upload_state, fingerprint, uploaded_at, uploaded_at),
        )
        self.database.execute(
            "UPDATE productions SET youtube_video_id=?, status=?, updated_at=? WHERE production_id=?",
            (video_id, upload_state, uploaded_at, production_id),
        )
        return video_id

    def schedule(self, production_id: str, video_id: str, publish_at: str, release: dict) -> None:
        self._assert_release(release)
        instant = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
        missed = instant.astimezone(timezone.utc) <= datetime.now(timezone.utc)
        status = {"privacyStatus": "public" if missed else "private", "selfDeclaredMadeForKids": False}
        if not missed:
            status["publishAt"] = instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        body = {"id": video_id, "status": status}
        with_retry(lambda: self.youtube.videos().update(part="status", body=body).execute())
        final_state = "published" if missed else "scheduled"
        privacy = "public" if missed else "private"
        self.database.execute(
            "UPDATE uploads SET privacy_status=?, scheduled_at=?, upload_status=?, updated_at=? WHERE production_id=?",
            (privacy, publish_at, final_state, utc_now(), production_id),
        )
        self.database.execute(
            "UPDATE productions SET status=?, scheduled_at=?, updated_at=? WHERE production_id=?",
            (final_state, publish_at, utc_now(), production_id),
        )
