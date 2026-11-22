"""The morning pick (owner 2026-11-22): every slot still waiting for his link shows the engine's choice of video to
model, early enough for him to copy the link, fetch its transcript from a free site and paste it back. He pastes:
the transcript is condensed to our length. He doesn't: at the slot's time the engine makes that same video the
normal way (no OpenAI here, only the YouTube data quota)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

KEEP = ("url", "title", "channel", "views", "views_per_hour", "breakout", "hours_old", "duration_seconds",
        "description", "found_by", "news", "score", "style")


def choose(breakouts: list[dict[str, Any]], taken: set[str]) -> dict[str, Any] | None:
    from .history import video_key
    for b in breakouts:
        key = video_key(b.get("url", ""))
        if key and key not in taken:
            return {k: b.get(k) for k in KEEP if k in b}
    return None


def run(bridge: Any, youtube: Any, now: datetime | None = None) -> list[dict[str, Any]]:
    from ..youtube.breakouts import find_breakouts
    from .history import used_source_videos, video_key
    now = now or datetime.now(timezone.utc)
    slots = bridge.link_slots()
    taken = {video_key((s.get("suggested_model") or {}).get("url", "")) for s in slots} - {""}
    found: dict[str, list[dict]] = {}
    done = []
    for slot in sorted(slots, key=lambda s: str(s.get("scheduled_at") or "")):
        if (slot.get("suggested_model") or {}).get("url"):
            continue
        fmt = "long" if slot.get("format") == "long" else "short"
        if fmt not in found:
            found[fmt] = find_breakouts(youtube, fmt, now=now)
        pick = choose(found[fmt], taken | used_source_videos(str(slot.get("job_id"))))
        if not pick:
            print(json.dumps({"status": "pick_none", "job": slot.get("job_id"), "format": fmt}))
            continue
        taken.add(video_key(pick["url"]))
        ok = bridge.suggest(str(slot["job_id"]), pick)
        done.append({"job": slot["job_id"], "url": pick["url"], "title": pick.get("title"), "ok": ok})
    print(json.dumps({"status": "morning_pick", "picked": done}))
    return done


def main() -> None:
    from ..studio_bridge import StudioBridge
    from ..youtube.auth import services
    youtube, _ = services()
    run(StudioBridge(os.getenv("GOLIDE_STUDIO_BASE_URL", "https://studio.golidee.com")), youtube)


if __name__ == "__main__":
    main()
