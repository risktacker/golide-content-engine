"""Preview of the owner's script voice (2026-11-04): an engine script before and after the new
spoken pass (free rewrite per chapter, then split back into screen lines). Writes
production-queue/preview/voice-<id>.txt. No video is touched."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golide_engine.engine.content_rules import (SPOKEN_CHAPTERS_SCHEMA, SPOKEN_PASS_EFFORT,  # noqa: E402
                                                draft_chapters, merge_spoken_chapters, script_text,
                                                spoken_pass_instructions, split_spoken)
from golide_engine.providers.registry import ProviderRegistry  # noqa: E402


def plan_from_record(record: dict, chapters: int) -> dict:
    lines = split_spoken(str(record["narration"]))
    per = -(-len(lines) // chapters)
    return {"lines": [{"chapter": i // per, "text": t, "emphasis": "", "label": "", "follow": False,
                       "section": "proof", "visual": "icon_hero", "subjects": []} for i, t in enumerate(lines)]}


def main(production_id: str) -> None:
    record = json.loads((ROOT / "data/production-records" / f"{production_id}.json").read_text(encoding="utf-8"))
    fmt = "long" if "-long-" in production_id else "short"
    plan = plan_from_record(record, 4 if fmt == "long" else 1)
    text = ProviderRegistry(ROOT / "config" / "providers.json").text(live=True)
    out = text.generate_json(spoken_pass_instructions(fmt), "DRAFT CHAPTERS\n" + json.dumps(
        {"chapters": draft_chapters(plan)}, ensure_ascii=False), SPOKEN_CHAPTERS_SCHEMA,
        max_output_tokens=32000, reasoning_effort=SPOKEN_PASS_EFFORT)
    merged = merge_spoken_chapters(plan, dict(out.value))
    after = "\n".join(b["text"] for b in out.value["chapters"])
    path = ROOT / "production-queue" / "preview" / f"voice-{production_id}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("BEFORE (engine script as recorded)\n\n" + script_text(plan) + "\n\n\nAFTER (new spoken pass)\n\n"
                    + after + "\n\n\nSCREEN LINES\n\n" + (script_text(merged) if merged else "(merge failed)")
                    + f"\n\ntokens in {out.input_tokens}, out {out.output_tokens}\n", encoding="utf-8")
    print(json.dumps({"preview": str(path), "words_before": len(script_text(plan).split()),
                      "words_after": len(after.split())}))


if __name__ == "__main__":
    main(sys.argv[1])
