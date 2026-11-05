"""Apply a rewrite of a waiting script (2026-11-05). Reads production-queue/<id>.owner-script.txt
(chapters in order, each starting with a [[k]] marker), merges it into the engine's scene plan from
the restored checkpoint (each new line keeps the pictures of the draft line at the same point of its
chapter) and writes production-queue/<id>.script-plan.json, which the engine uses in place of its own
script until the recording is processed. Prints the reading copy. No paid calls."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golide_engine.engine.content_rules import merge_spoken_chapters, script_display  # noqa: E402


def main(production_id: str) -> None:
    plan = json.loads((ROOT / "productions" / production_id / "scene-plan.json").read_text(encoding="utf-8"))
    raw = (ROOT / "production-queue" / f"{production_id}.owner-script.txt").read_text(encoding="utf-8")
    order: list[int] = []
    for line in plan["lines"]:
        index = int(line.get("chapter") or 0)
        if not order or order[-1] != index:
            order.append(index)
    parts = re.split(r"\[\[\d+\]\]", raw)[1:]
    if len(parts) != len(order):
        raise SystemExit(f"rewrite has {len(parts)} chapters, the plan has {len(order)}")
    script = "".join(f"\n\n[[{i}]] {p.strip()}" for i, p in zip(order, parts))
    merged = merge_spoken_chapters(plan, {"script": script})
    if merged is None:
        raise SystemExit("merge failed")
    (ROOT / "production-queue" / f"{production_id}.script-plan.json").write_text(
        json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    (ROOT / "production-queue" / f"{production_id}.owner-script-display.txt").write_text(
        script_display(merged) + "\n", encoding="utf-8")
    print(script_display(merged))


if __name__ == "__main__":
    main(sys.argv[1])
