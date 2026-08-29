from __future__ import annotations

from collections.abc import Callable

from ..operations.notifications import Notifier
from ..operations.retry import with_retry
from ..storage.database import Database, utc_now


class StageRunner:
    def __init__(self, database: Database, notifier: Notifier):
        self.database = database
        self.notifier = notifier

    def run(self, production_id: str, stage: str, operation: Callable[[], object], attempts: int = 3):
        completed = self.database.rows(
            "SELECT status FROM stage_runs WHERE production_id=? AND stage=? AND status='completed' LIMIT 1",
            (production_id, stage),
        )
        if completed:
            return None
        previous = self.database.rows("SELECT COALESCE(MAX(attempt), 0) attempt FROM stage_runs WHERE production_id=? AND stage=?", (production_id, stage))
        attempt = int(previous[0]["attempt"]) + 1
        self.database.execute(
            "INSERT INTO stage_runs(production_id, stage, attempt, status, started_at) VALUES (?, ?, ?, 'running', ?)",
            (production_id, stage, attempt, utc_now()),
        )
        try:
            result = with_retry(operation, attempts=attempts)
        except Exception as exc:
            self.database.execute(
                "UPDATE stage_runs SET status='failed', completed_at=?, error=? WHERE production_id=? AND stage=? AND attempt=?",
                (utc_now(), str(exc)[:2000], production_id, stage, attempt),
            )
            self.notifier.failure(production_id, stage, str(exc))
            raise
        self.database.execute(
            "UPDATE stage_runs SET status='completed', completed_at=? WHERE production_id=? AND stage=? AND attempt=?",
            (utc_now(), production_id, stage, attempt),
        )
        return result
