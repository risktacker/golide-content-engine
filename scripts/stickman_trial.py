"""TRIAL (owner 2026-11-17): a Stickman video made from a finished production's own voice, word timings and research,
so the only new cost is the storyboard writer. Optionally with Goli beside it.

    python scripts/stickman_trial.py <production_id> [goli]

Output in build/stickman-trial/<production_id>/: the video, the kit's contact sheets, the storyboard and the cost.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golide_engine.edit.pipeline import outfit_today, settings  # noqa: E402
from golide_engine.providers.openai_text import OpenAITextProvider  # noqa: E402
from golide_engine.stickman import goli_layer, longform, short  # noqa: E402

PRICES = {"gpt-5.6-sol": (4.0, 20.0)}   # USD per million input / output tokens (config/provider-pricing.json)


def main() -> None:
    pid, goli = sys.argv[1], len(sys.argv) > 2 and sys.argv[2] == "goli"
    work = ROOT / "productions" / pid
    out = ROOT / "build" / "stickman-trial" / pid
    out.mkdir(parents=True, exist_ok=True)
    narration = work / "narration-owner.wav"
    words_path = work / "timed-words-authoritative-v3.json"
    if not words_path.exists():
        words_path = work / "timed-words-owner.json"
    words = json.loads(words_path.read_text(encoding="utf-8"))
    research = json.loads((work / "research.json").read_text(encoding="utf-8"))
    plan = json.loads((work / "scene-plan.json").read_text(encoding="utf-8")) if (work / "scene-plan.json").exists() else {}
    title = str(plan.get("title") or pid)
    duration = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                     str(narration)], capture_output=True, text=True, check=True).stdout)
    fmt = "long" if "-long-" in pid else "short"
    conf = settings().get("stickman") or {}
    writer = OpenAITextProvider(conf.get("model", "gpt-5.6-sol"), conf.get("reasoning_effort", "medium"))
    spent = []
    record = lambda name, o: spent.append({"call": name, "in": o.input_tokens, "cached": o.cached_input_tokens,
                                           "out": o.output_tokens})
    print(json.dumps({"status": "trial_start", "production": pid, "format": fmt, "seconds": round(duration, 1),
                      "words": len(words), "title": title}), flush=True)
    if fmt == "long":
        project = out / "stickman"
        spoken = " ".join(str(w.get("word", "")).strip() for w in words if str(w.get("word", "")).strip())
        doc = longform.prepare(project, spoken, words, duration, narration)
        left = longform.storyboard(writer, project, title, doc, research, record=record)
        print(json.dumps({"status": "trial_plan", "warnings_left": left[:10]}), flush=True)
        longform.kit("stills", project)
        for sheet in sorted((project / "work").glob("sheet_*.jpg")):
            shutil.copy(sheet, out / sheet.name)
        video = longform.render(project, conf.get("res"))
        pauses = longform.gaps(project)
        poses = goli_layer.reactions_long(project, goli_layer._duration(video)) if goli else []
        shutil.copy(project / "story.json", out / "story.json")
    else:
        project = out / "stickman-short"
        video = short.make(writer, project, title, words, duration, narration, record=record)
        if (project / "stills" / "sheet.jpg").exists():
            shutil.copy(project / "stills" / "sheet.jpg", out / "sheet_short.jpg")
        for f in ("web/story.js", "work/PLAN.md"):
            if (project / f).exists():
                shutil.copy(project / f, out / Path(f).name)
        if not video:
            raise SystemExit("TRIAL: the Short failed its look check twice (Goli would make it in production)")
        pauses, poses = [], (goli_layer.reactions_short(project, goli_layer._duration(video)) if goli else [])
    shutil.copy(video, out / "stickman.mp4")
    if goli:
        goli_layer.add(fmt, out / "stickman.mp4", narration, out / "goli", out / "stickman-goli.mp4", outfit_today(),
                       poses, pauses)
    cost = sum((s["in"] - s["cached"]) * PRICES["gpt-5.6-sol"][0] / 1e6 + s["cached"] * PRICES["gpt-5.6-sol"][0] / 10e6
               + s["out"] * PRICES["gpt-5.6-sol"][1] / 1e6 for s in spent)
    (out / "cost.json").write_text(json.dumps({"calls": spent, "usd": round(cost, 3)}, indent=2), encoding="utf-8")
    print(json.dumps({"status": "trial_done", "usd": round(cost, 3)}), flush=True)


if __name__ == "__main__":
    main()
