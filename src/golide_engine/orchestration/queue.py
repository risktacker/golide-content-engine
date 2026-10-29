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
        if path.name.endswith((".completed.json", ".topic-rejected.json", ".script-plan.json", ".research.json",
                               ".failed.json")):
            continue
        spec = json.loads(path.read_text(encoding="utf-8"))
        if "generate_at" not in spec:
            continue
        generate_at = datetime.fromisoformat(spec["generate_at"].replace("Z", "+00:00"))
        if spec.get("production_authorized") is True and generate_at <= now:
            due.append((generate_at, path))
    return [path for _, path in sorted(due)]


def waiting_for_voice(spec: dict, root: str | Path = ".") -> bool:
    """The script is written and only the owner's recording is missing."""
    if not spec.get("owner_voice_required", True) or str(spec.get("owner_voice_media_ref") or "").strip():
        return False
    work = Path(root) / "productions" / str(spec.get("id", ""))
    rescript = Path(root) / "production-queue" / f"{spec.get('id', '')}.rescript"
    if rescript.exists():
        done = work / "rescript-done.txt"
        token = rescript.read_text(encoding="utf-8").strip()
        if not done.exists() or done.read_text(encoding="utf-8").strip() != token:
            return False   # a fresh script was asked for (2026-10-29)
    return (work / "script.txt").exists()


def pick_due_spec(due: list[Path], root: str | Path = ".") -> Path | None:
    """Which due production to run now (2026-10-08 audit).

    A job with a fresh recording goes first. Jobs that are only waiting for the
    owner's recording are skipped, so one unrecorded video never blocks the
    videos behind it. None means everything due is waiting for a recording.
    """
    first_free = None
    for path in due:
        spec = json.loads(path.read_text(encoding="utf-8"))
        if str(spec.get("owner_voice_media_ref") or "").strip():
            return path
        if first_free is None and not waiting_for_voice(spec, root):
            first_free = path
    return first_free


MAX_FAILED_RUNS = 3


def record_failure(spec_path: Path) -> bool:
    """Count a failed run; after MAX_FAILED_RUNS the spec is set aside as
    <id>.failed.json so it stops blocking the queue. True when set aside."""
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["_failed_runs"] = int(spec.get("_failed_runs", 0)) + 1
    if spec["_failed_runs"] >= MAX_FAILED_RUNS:
        spec_path.with_suffix(".failed.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        spec_path.unlink()
        return True
    spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    return False
