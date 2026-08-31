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
            connection.executescript(schema)
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(cost_events)")}
            if "characters" not in columns:
                connection.execute(
                    "ALTER TABLE cost_events ADD COLUMN characters INTEGER NOT NULL DEFAULT 0"
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
