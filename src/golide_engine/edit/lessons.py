"""What the Goli engine learns from every video (owner 2026-11-25: "mistakes being learned, so that from the next
video that one can be happening").

The doctor (edit/doctor.py) reads every finished video and fixes what is broken. Each kind of fix is a GENERAL rule
(never a topic or a name, doctor.RULES), counted in R2 (goli-lessons/lessons.json). The editor reads the most frequent
and most recent ones before the next video (editor.instructions), so it stops making the same mistake. A rule that
stops happening fades: it drops out after LAPSE videos without a repeat. Free: no model call.
"""
from __future__ import annotations

import json
from typing import Any

from ..shorts3d.lessons import LAPSE, SHOW

KEY = "goli-lessons/lessons.json"


def observe(report: dict[str, Any] | None) -> list[str]:
    """This video's lessons, each once."""
    out: list[str] = []
    for r in (report or {}).get("rules") or []:
        if r not in out:
            out.append(r)
    return out


def update(store: dict | None, rules: list[str]) -> dict:
    st = json.loads(json.dumps(store or {"videos": 0, "lessons": {}}))
    st["videos"] = int(st.get("videos", 0)) + 1
    for r in rules:
        e = st["lessons"].setdefault(r, {"count": 0, "last": 0})
        e["count"] += 1
        e["last"] = st["videos"]
    for r in list(st["lessons"]):
        if st["videos"] - st["lessons"][r]["last"] >= LAPSE:
            del st["lessons"][r]
    return st


def for_editor(store: dict | None) -> list[str]:
    ls = (store or {}).get("lessons") or {}
    keys = sorted(ls, key=lambda r: (-ls[r]["count"], -ls[r]["last"]))[:SHOW]
    return [f"{r} (the doctor had to fix this on {ls[r]['count']} video{'s' if ls[r]['count'] != 1 else ''})"
            for r in keys]


def _store():
    try:
        from ..storage.r2 import r2_store_from_environment
        return r2_store_from_environment()
    except Exception:  # noqa: BLE001 - no R2 here (tests, a local run)
        return None


def load() -> dict | None:
    r2 = _store()
    if r2 is None:
        return None
    try:
        import urllib.request
        with urllib.request.urlopen(r2.resolve(f"r2://{KEY}", expires_seconds=600), timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - nothing learned yet
        return None


def learn(production, report: dict[str, Any] | None) -> dict[str, Any]:
    """After a video: observe, count, save. Never stops a video."""
    rules = observe(report)
    st = update(load(), rules)
    r2 = _store()
    if r2 is not None:
        r2.put_object(KEY, json.dumps(st, indent=1).encode("utf-8"), "application/json")
    return {"learned": rules, "videos": st["videos"]}
