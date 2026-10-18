"""A replaced recording replaces everything built from the old one (2026-10-18).

The owner uploaded the wrong recording, cancelled, and uploaded again. Checkpoints
are kept between runs, so without this the new recording would be ignored: the
transcript, timing, captions, render and metadata of the old one would be reused.
The script, research, storyboard pictures and thumbnail do not depend on the
voice, so they are kept (nothing paid for is thrown away).
"""

from __future__ import annotations

import json
from pathlib import Path

VOICE_STAGES = (
    "owner-voice", "captions-authoritative-v3", "render-vector-v1", "render-full-duration-v11",
    "editorial-beats-authoritative-v3", "storyboard-authoritative-v5", "metadata", "qa",
)
VOICE_FILES = (
    "owner-voice-source", "narration-owner.wav", "timed-words-owner.json", "timed-words-authoritative-v3.json",
    "spoken-captions-authoritative-v3.srt", "chapters.json", "storyboard-vector.json", "upload-metadata.json",
    "qa-report.json",
)
REF_FILE = "owner-voice-ref.txt"


def reset_if_recording_changed(database, root: Path, production_id: str, work: Path, voice_ref: str) -> bool:
    """Clear voice-built work when ``voice_ref`` is not the recording it was built from.
    Returns True when a reset happened. Never resets a production already released."""
    marker = work / REF_FILE
    built_from = marker.read_text(encoding="utf-8").strip() if marker.exists() else ""
    voice_done = (work / "timed-words-owner.json").exists()
    released = database.rows(
        "SELECT 1 FROM stage_runs WHERE production_id=? AND stage='release' AND status='completed' LIMIT 1",
        (production_id,),
    )
    changed = voice_done and built_from != voice_ref  # no marker yet: built before markers existed
    if changed and not released:
        for name in VOICE_FILES:
            (work / name).unlink(missing_ok=True)
        build = root / "build" / production_id
        for name in ("video.mp4", "video-cover.jpg", "visual-labels.srt"):
            (build / name).unlink(missing_ok=True)
        for stage in VOICE_STAGES:
            database.execute("DELETE FROM stage_runs WHERE production_id=? AND stage=?", (production_id, stage))
        print(json.dumps({"status": "recording_replaced", "production_id": production_id,
                          "from": built_from or "unknown", "to": voice_ref}))
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(voice_ref + "\n", encoding="utf-8")
    return bool(changed and not released)
