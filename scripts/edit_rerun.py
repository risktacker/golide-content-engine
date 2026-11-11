"""TRIAL: re-cut a finished production with the current edit engine (no upload, one editor call).

Reads the saved recording, word timings, script plan and research of `productions/<id>` (restored from
the run checkpoint), captures the sources again, asks the editor model for a per-beat edit, renders it
and writes build/edit-rerun/<id>/ (video.mp4, edit-list.json, stills).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from golide_engine.edit import editor  # noqa: E402
from golide_engine.edit.pipeline import logo_tile_maker, outfit_today  # noqa: E402
from golide_engine.edit.render import lipsync, render  # noqa: E402
from golide_engine.engine.source_capture import capture  # noqa: E402
from golide_engine.providers.registry import ProviderRegistry  # noqa: E402
from golide_engine.vector.align import align_lines  # noqa: E402
from golide_engine.vector.chapters import chapter_marks  # noqa: E402

pid = sys.argv[1]
work = ROOT / "productions" / pid
out = ROOT / "build" / "edit-rerun" / pid
out.mkdir(parents=True, exist_ok=True)
spec = json.loads((work / "spec.json").read_text()) if (work / "spec.json").exists() else {}
fmt = spec.get("format") or ("short" if "short" in pid else "long")
plan = json.loads((work / "scene-plan.json").read_text())
research = json.loads((work / "research.json").read_text())
words = json.loads((work / "timed-words-authoritative-v3.json").read_text())
narration = work / "narration-owner.wav"
seconds = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                         str(narration)]).decode().strip())
sources = capture(research, out / "sources")
print(json.dumps({"pages": [(s["url"][:70], s.get("ok"), len(editor.shots(s)), bool(s.get("photo"))) for s in sources]}))
cues = lipsync(narration, out / "cues.json")
lines = align_lines(plan, words, seconds)
marks = chapter_marks(plan, lines) if plan.get("chapters") else []
beat_lines = editor.beats(lines, fmt)
spoken = [x for x in plan.get("lines", []) if str(x.get("text", "")).strip()]
follow = {b.index for b in beat_lines for i, x in enumerate(spoken) if x.get("follow") is True and i < len(lines)
          and lines[i].start - 0.01 <= b.start <= lines[i].end}
content = editor.request(str(spec.get("title", pid)), beat_lines, sources, marks, follow)
text = ProviderRegistry(ROOT / "config/providers.json").text(live=True)
result = text.generate_json(editor.instructions(fmt), content, editor.EDIT_SCHEMA,
                            max_output_tokens=min(60000, 6000 + 260 * len(beat_lines)))
(out / "edit-plan-raw.json").write_text(json.dumps(result.value, indent=2))
edit = editor.build(result.value, beat_lines, seconds, fmt, sources, out / "sources", cues, marks,
                    logo_tile_maker(out / "logos"))
editor.save(edit, out / "edit-list.json")
print(json.dumps({"beats": len(beat_lines), "scenes": len(edit["scenes"]), "notes": edit["notes"],
                  "types": [s["type"] + (":" + s["data"]["place"] if s["type"] == "host" else "") for s in edit["scenes"]]}))
render(edit, out, narration, out / "video.mp4", outfit_today(), None)
print(json.dumps({"video_mb": round((out / "video.mp4").stat().st_size / 1e6, 1), "seconds": round(seconds, 1)}))
for i, t in enumerate([seconds * k / 12 for k in range(12)]):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t + 0.6:.2f}", "-i", str(out / "video.mp4"), "-frames:v", "1",
                    "-vf", "scale=360:-1", str(out / f"still-{i:02d}.jpg")], check=True)
