from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        with self.connect() as connection:
            # Base schema must remain safe for both brand-new and legacy databases.
            # Indexes that depend on migrated columns are created only after the
            # ALTER TABLE compatibility work below.
            connection.executescript(schema)
            cost_columns = {row["name"] for row in connection.execute("PRAGMA table_info(cost_events)")}
            if "characters" not in cost_columns:
                connection.execute(
                    "ALTER TABLE cost_events ADD COLUMN characters INTEGER NOT NULL DEFAULT 0"
                )
            upload_columns = {row["name"] for row in connection.execute("PRAGMA table_info(uploads)")}
            if "uploaded_at" not in upload_columns:
                connection.execute("ALTER TABLE uploads ADD COLUMN uploaded_at TEXT")
                connection.execute(
                    "UPDATE uploads SET uploaded_at=updated_at WHERE youtube_video_id IS NOT NULL AND uploaded_at IS NULL"
                )
            if "media_purged_at" not in upload_columns:
                connection.execute("ALTER TABLE uploads ADD COLUMN media_purged_at TEXT")
            # Safe only after uploaded_at is guaranteed to exist on old databases.
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_upload_uploaded_at ON uploads(uploaded_at)"
            )

            content_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(content_posts)")
            }
            content_additions = {
                "content_class": "TEXT NOT NULL DEFAULT 'post'",
                "weekly_theme": "TEXT NOT NULL DEFAULT ''",
                "content_lane": "TEXT NOT NULL DEFAULT ''",
                "value_units_json": "TEXT NOT NULL DEFAULT '[]'",
                "product_bridge_position": "INTEGER",
                "product_url": "TEXT NOT NULL DEFAULT ''",
                "product_mode": "TEXT NOT NULL DEFAULT 'brand'",
                "product_id": "TEXT NOT NULL DEFAULT ''",
                "owner_voice_media_ref": "TEXT",
                "media_approved": "INTEGER NOT NULL DEFAULT 0",
                "qa_approved": "INTEGER NOT NULL DEFAULT 0",
                "release_approved": "INTEGER NOT NULL DEFAULT 0",
            }
            for name, definition in content_additions.items():
                if name not in content_columns:
                    connection.execute(
                        f"ALTER TABLE content_posts ADD COLUMN {name} {definition}"
                    )

            variant_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(social_variants)")
            }
            if "parts_json" not in variant_columns:
                connection.execute(
                    "ALTER TABLE social_variants ADD COLUMN parts_json TEXT NOT NULL DEFAULT '[]'"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_content_posts_class_schedule "
                "ON content_posts(content_class, status, scheduled_at)"
            )

    def upsert_production(self, spec: dict[str, Any], status: str = "planned") -> None:
        now = utc_now()
        concept = spec.get("concept", {})
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO productions
                   (production_id, format, concept_family, title, status, approved,
                    scheduled_at, parameters_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(production_id) DO UPDATE SET
                    title=excluded.title, status=excluded.status,
                    approved=excluded.approved, scheduled_at=excluded.scheduled_at,
                    parameters_json=excluded.parameters_json, updated_at=excluded.updated_at""",
                (
                    spec["id"], spec["format"], concept.get("family", "unclassified"),
                    spec.get("title", concept.get("title", spec["id"])), status,
                    int(bool(spec.get("release", {}).get("approved", False))),
                    spec.get("release", {}).get("scheduled_at"),
                    json.dumps(spec.get("generation_parameters", {}), sort_keys=True), now, now,
                ),
            )

    def rows(self, query: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(query, parameters).fetchall()]

    def execute(self, query: str, parameters: tuple[Any, ...] = ()) -> None:
        with self.connect() as connection:
            connection.execute(query, parameters)
