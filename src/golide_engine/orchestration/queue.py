from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def due_specs(queue_directory: str | Path, now: datetime | None = None) -> list[Path]:
    now = now or datetime.now(timezone.utc)
    due = []
    for path in Path(queue_directory).glob("*.json"):
        # Only production specs live here as plain <id>.json; companion files such as an
        # owner-approved <id>.script-plan.json and <id>.research.json are read by the production itself.
        if path.name.endswith((".completed.json", ".topic-rejected.json", ".script-plan.json", ".research.json")):
            continue
        spec = json.loads(path.read_text(encoding="utf-8"))
        if "generate_at" not in spec:
            continue
        generate_at = datetime.fromisoformat(spec["generate_at"].replace("Z", "+00:00"))
        if spec.get("production_authorized") is True and generate_at <= now:
            due.append((generate_at, path))
    return [path for _, path in sorted(due)]
