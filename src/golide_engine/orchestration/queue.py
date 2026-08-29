from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def due_specs(queue_directory: str | Path, now: datetime | None = None) -> list[Path]:
    now = now or datetime.now(timezone.utc)
    due = []
    for path in Path(queue_directory).glob("*.json"):
        if path.name.endswith(".completed.json"):
            continue
        spec = json.loads(path.read_text(encoding="utf-8"))
        generate_at = datetime.fromisoformat(spec["generate_at"].replace("Z", "+00:00"))
        if spec.get("production_authorized") is True and generate_at <= now:
            due.append((generate_at, path))
    return [path for _, path in sorted(due)]
