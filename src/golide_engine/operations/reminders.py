"""Owner reminders for connections that cannot renew themselves (LinkedIn)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

REMIND_ON_DAYS = (7, 3, 1, 0)


def days_left(expires_at: str, now: datetime) -> int | None:
    try:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return int((expiry - now).total_seconds() // 86400)


def due_reminders(connections: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    """Reminders to send this run. Runs twice a day, so only the morning run sends."""
    if now.astimezone(timezone.utc).hour >= 12:
        return []
    due = []
    for item in connections:
        left = days_left(str(item.get("expires_at") or ""), now)
        if left is not None and left in REMIND_ON_DAYS:
            due.append({"platform": item.get("platform", ""), "days_left": left,
                        "account": item.get("account", "")})
    return due
