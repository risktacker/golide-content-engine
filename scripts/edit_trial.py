"""TRIAL of the edit engine on GitHub Actions (no real production touched, no paid call).

Captures two real pages, lip-syncs a recording, builds a canned edit list, renders it with HyperFrames
and mixes the sound, exactly as the daily run would. Output: build/edit-trial/video.mp4.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from golide_engine.edit import editor  # noqa: E402
from golide_engine.edit.pipeline import logo_tile_maker, outfit_today  # noqa: E402
from golide_engine.edit.render import lipsync, render  # noqa: E402
from golide_engine.engine.source_capture import capture  # noqa: E402
from golide_engine.vector.align import TimedLine, Word  # noqa: E402

out = ROOT / "build/edit-trial"
out.mkdir(parents=True, exist_ok=True)
research = {"claims": [
    {"claim": "Claude Fable 5.2 output pricing is $40 per million tokens.", "source_url": "https://platform.claude.com/docs/en/about-claude/models/overview", "source_title": "Models overview"},
    {"claim": "Anthropic announced Claude Fable 5.2.", "source_url": "https://www.anthropic.com/news", "source_title": "Anthropic news"}]}
t = time.time()
sources = capture(research, out / "sources")
print(json.dumps({"capture_s": round(time.time() - t), "pages": [(s["url"], s.get("ok"), len(s.get("highlights") or [])) for s in sources]}))
narration = Path(sys.argv[1])
FMT = sys.argv[2] if len(sys.argv) > 2 else "short"
cues = lipsync(narration, out / "cues.json")
texts = ["Anthropic just shipped a new model and the price is wild.", "Here is the page with the real numbers.",
         "Claude, OpenAI and Google are all in this race.", "So who should pay for it?", "Follow for one AI story a day."]
lines, tt = [], 0.0
for i, tx in enumerate(texts):
    ws = []
    for w in tx.split():
        ws.append(Word(w.strip(".,?"), tt, tt + 0.3)); tt += 0.36
    lines.append(TimedLine(i, tx, "", "", "", "", ws[0].start, ws[-1].end, ws)); tt += 0.3
ok = next((i for i, s in enumerate(sources) if s.get("ok")), None)
raw = {"scenes": [
    {"type": "studio", "first_line": 0, "last_line": 0, "poses": [{"pose": "shock", "word": "wild"}], "screen_words": "A new model just shipped", "punch": "new"},
    {"type": "source", "first_line": 1, "last_line": 1, "source": ok, "phrase": 0 if ok is not None and sources[ok].get("highlights") else None,
     "callout": "$40", "callout_sub": "per million output tokens", "edge": "glass", "goli_corner": True, "poses": [{"pose": "point_left", "word": "page"}]},
    {"type": "logos", "first_line": 2, "last_line": 2, "brands": ["Claude", "OpenAI", "Google Gemini"], "screen_words": "The race"},
    {"type": "studio", "first_line": 3, "last_line": 3, "poses": [{"pose": "think", "word": "who"}], "screen_words": "Who should pay?", "punch": "pay"},
    {"type": "follow", "first_line": 4, "last_line": 4, "label": "One AI story a day"}]}
edit = editor.build(raw, lines, min(22.0, tt + 1.5), FMT, sources, out / "sources", cues, [], logo_tile_maker(out / "logos"))
editor.save(edit, out / "edit-list.json")
print(json.dumps({"notes": edit["notes"], "scenes": [s["type"] for s in edit["scenes"]]}))
t = time.time()
render(edit, out, narration, out / "video.mp4", outfit_today(), None)
print(json.dumps({"render_s": round(time.time() - t), "seconds": edit["duration"]}))
