"""Shorts as Instagram and Facebook Reels, with a real cover image.

Instagram uses the first frame as the cover when none is given, and the first
frame of a GOLIDE Black video is still empty black (the drawing has not
started). So every Reel gets a cover: the frame from the first part of the
video where the most of the illustration is on screen.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


def pick_cover(video: Path, output: Path, *, search_fraction: float = 0.4) -> Path:
    """Save the most fully drawn frame from the first part of the video."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=True,
    )
    duration = float(probe.stdout.strip() or 0)
    window = max(3.0, duration * search_fraction)
    w, h = 54, 96
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-t", f"{window:.2f}", "-i", str(video),
         "-vf", f"fps=2,scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
        capture_output=True, check=True,
    ).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    # Ignore the caption band at the bottom: judge the drawing area only.
    ink = frames[:, : int(h * 0.66), :]
    score = (ink > 60).mean(axis=(1, 2))
    best = int(np.argmax(score)) if len(score) else 0
    at = min(best / 2.0 + 0.25, max(0.0, duration - 0.1))
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", str(video), "-frames:v", "1",
         "-q:v", "2", str(output)],
        check=True,
    )
    return output


def upload_media(store, path: Path, name: str, content_type: str, bridge=None, kind: str = "video"):
    upload = store.upload_bytes(filename=name, media_kind=kind, data=path.read_bytes(),
                                content_type=content_type, retention_hours=72)
    if bridge is not None:
        try:
            bridge.register_media([{"media_ref": upload.media_ref, "media_kind": kind,
                                    "expires_at": upload.expires_at.isoformat()}])
        except Exception as exc:  # tracking only
            print({"status": "media_register_failed", "error": str(exc)})
    return upload.media_ref


def reels_payload(*, content_id: str, metadata: dict[str, Any], video_ref: str, cover_ref: str | None,
                  youtube_video_id: str, owner_voice_ref: str) -> dict[str, Any]:
    caption = (str(metadata.get("title", "")).strip() + "\n\n"
               + str(metadata.get("description", "")).strip())[:2100]
    cover = [f"cover:{cover_ref}"] if cover_ref else []
    return {
        "id": content_id,
        "content_class": "short",
        "title": metadata.get("title", ""),
        "master_text": caption,
        "owner_voice_media_ref": owner_voice_ref,
        "media_approved": True,
        "qa_approved": True,
        "release_approved": True,
        "scheduled_at": datetime.now(timezone.utc).isoformat(),
        "variants": [
            {"platform": "instagram", "title": "", "body": caption, "media_ref": video_ref, "parts": cover},
            {"platform": "facebook", "title": "", "body": caption, "media_ref": video_ref, "parts": cover},
            {"platform": "youtube", "title": metadata.get("title", ""), "body": "",
             "media_ref": video_ref, "parts": [f"youtube:{youtube_video_id}"]},
        ],
    }


def publish_reels(*, bridge, store, publisher_factory, production_id: str, video: Path,
                  metadata: dict[str, Any], youtube_video_id: str, owner_voice_ref: str,
                  video_ref: str | None = None, content_id: str | None = None) -> dict[str, Any]:
    """Upload (if needed), queue and publish the IG/FB Reels for one short."""
    if video_ref is None:
        video_ref = upload_media(store, video, f"{production_id}.mp4", "video/mp4", bridge)
    cover_ref = None
    try:
        cover = pick_cover(video, video.with_name(video.stem + "-cover.jpg"))
        cover_ref = upload_media(store, cover, f"{production_id}-cover.jpg", "image/jpeg", bridge, "image")
    except Exception as exc:  # a missing cover must not block the Reel
        print({"status": "cover_failed", "error": str(exc)})
    content_id = content_id or f"{production_id}-reels"
    bridge.create_content(reels_payload(
        content_id=content_id, metadata=metadata, video_ref=video_ref, cover_ref=cover_ref,
        youtube_video_id=youtube_video_id, owner_voice_ref=owner_voice_ref,
    ))
    results = publisher_factory().run_due()
    mine = next((r for r in results if r.get("post_id") == content_id), None)
    return {"social_post_id": content_id, "reels_status": mine["status"] if mine else "not_claimed",
            "cover_ref": cover_ref}
