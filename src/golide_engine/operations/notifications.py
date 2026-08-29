from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class FailureEvent:
    production_id: str
    stage: str
    message: str
    occurred_at: str


class Notifier:
    def __init__(self, event_directory: str | Path = "failure-events"):
        self.event_directory = Path(event_directory)

    def failure(self, production_id: str, stage: str, message: str) -> Path:
        event = FailureEvent(production_id, stage, message, datetime.now(timezone.utc).isoformat())
        self.event_directory.mkdir(parents=True, exist_ok=True)
        path = self.event_directory / f"{production_id}-{stage}.json"
        payload = json.dumps(asdict(event), indent=2).encode()
        path.write_bytes(payload + b"\n")
        webhook = os.getenv("GOLIDE_FAILURE_WEBHOOK")
        if webhook:
            request = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(request, timeout=10).close()
        return path
