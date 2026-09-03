from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .database import Database, utc_now


RETAIN_HOURS = 48
SAFE_TERMINAL_STATES = {"uploaded_private", "scheduled", "published"}
HEAVY_ROOTS = ("productions", "build", "release-packages", "generated")


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def write_lightweight_record(
    root: Path,
    database: Database,
    production_id: str,
    youtube_video_id: str,
) -> Path:
    """Persist the small audit/reproduction record while heavy media stays temporary."""
    work = root / "productions" / production_id
    package_root = root / "release-packages" / production_id

    def read_text(name: str) -> str | None:
        path = work / name
        return path.read_text(encoding="utf-8") if path.exists() else None

    def read_json(name: str) -> Any | None:
        raw = read_text(name)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    upload_rows = database.rows(
        "SELECT youtube_video_id, upload_status, privacy_status, scheduled_at, uploaded_at "
        "FROM uploads WHERE production_id=?",
        (production_id,),
    )
    production_rows = database.rows(
        "SELECT format, title, status, scheduled_at, parameters_json FROM productions WHERE production_id=?",
        (production_id,),
    )
    costs = database.rows(
        "SELECT stage, provider, model, input_units, cached_input_units, output_units, images, "
        "audio_minutes, characters, cost_usd, created_at FROM cost_events WHERE production_id=? ORDER BY id",
        (production_id,),
    )

    package_manifest = None
    package_manifest_path = package_root / "package-manifest.json"
    if package_manifest_path.exists():
        package_manifest = json.loads(package_manifest_path.read_text(encoding="utf-8"))

    record = {
        "production_id": production_id,
        "youtube_video_id": youtube_video_id,
        "retention_hours": RETAIN_HOURS,
        "upload": upload_rows[0] if upload_rows else None,
        "production": production_rows[0] if production_rows else None,
        "narration": read_text("script.txt"),
        "research": read_json("research.json"),
        "metadata": read_json("upload-metadata.json"),
        "source_ledger": read_json("source-ledger.json"),
        "qa_report": read_json("qa-report.json"),
        "generation_parameters": read_json("generation-parameters.json"),
        "package_manifest": package_manifest,
        "cost_events": costs,
        "recorded_at": utc_now(),
    }
    records = root / "data" / "production-records"
    records.mkdir(parents=True, exist_ok=True)
    target = records / f"{production_id}.json"
    target.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def register_successful_upload(
    root: Path,
    database: Database,
    production_id: str,
    youtube_video_id: str,
) -> dict[str, Any]:
    """Start retention only after a confirmed YouTube upload has a durable video ID."""
    rows = database.rows(
        "SELECT uploaded_at FROM uploads WHERE production_id=? AND youtube_video_id=?",
        (production_id, youtube_video_id),
    )
    if not rows or not rows[0].get("uploaded_at"):
        raise RuntimeError("cannot start retention before a successful YouTube upload timestamp exists")
    uploaded_at = _parse_utc(str(rows[0]["uploaded_at"]))
    expires_at = uploaded_at + timedelta(hours=RETAIN_HOURS)
    record = write_lightweight_record(root, database, production_id, youtube_video_id)
    return {
        "production_id": production_id,
        "youtube_video_id": youtube_video_id,
        "uploaded_at": uploaded_at.isoformat(),
        "media_expires_at": expires_at.isoformat(),
        "record": str(record),
    }


def cleanup_expired_media(root: Path, database: Database, now: datetime | None = None) -> list[dict[str, Any]]:
    """Purge only uploaded terminal productions older than 48h; unfinished work is never touched."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff = (now - timedelta(hours=RETAIN_HOURS)).isoformat()
    rows = database.rows(
        """SELECT u.production_id, u.youtube_video_id, u.uploaded_at, p.status
           FROM uploads u JOIN productions p USING(production_id)
           WHERE u.youtube_video_id IS NOT NULL
             AND u.uploaded_at IS NOT NULL
             AND u.uploaded_at <= ?
             AND u.media_purged_at IS NULL""",
        (cutoff,),
    )
    purged: list[dict[str, Any]] = []
    for row in rows:
        production_id = str(row["production_id"])
        if row["status"] not in SAFE_TERMINAL_STATES:
            # Running, failed, QA-blocked, release-ready or correction work is retained.
            continue

        removed: list[str] = []
        for directory in HEAVY_ROOTS:
            target = root / directory / production_id
            if target.exists():
                shutil.rmtree(target, ignore_errors=False)
                removed.append(str(target))
        archive = root / "release-packages" / f"{production_id}.zip"
        if archive.exists():
            archive.unlink()
            removed.append(str(archive))

        purged_at = utc_now()
        database.execute(
            "UPDATE uploads SET media_purged_at=?, updated_at=? WHERE production_id=?",
            (purged_at, purged_at, production_id),
        )
        purged.append({
            "production_id": production_id,
            "youtube_video_id": row["youtube_video_id"],
            "uploaded_at": row["uploaded_at"],
            "purged_at": purged_at,
            "removed": removed,
        })
    return purged
