"""TRIAL (owner 2026-11-21): a 10-second Goli Short with the 3D Goli, to see the new look talking.

Reads a 10-second line with the AI voice (ElevenLabs "Mark", about 150 characters of the monthly cap), lip-syncs
it with Rhubarb, builds a Goli studio edit (three poses) and renders it exactly as the daily Short is rendered.
Output: build/goli3d-trial/video.mp4. Nothing is published.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from golide_engine.edit import editor  # noqa: E402
from golide_engine.edit.pipeline import logo_tile_maker, outfit_today  # noqa: E402
from golide_engine.edit.render import lipsync, render  # noqa: E402
from golide_engine.providers.registry import ProviderRegistry  # noqa: E402
from golide_engine.vector.align import TimedLine, Word  # noqa: E402

out = ROOT / "build/goli3d-trial"
out.mkdir(parents=True, exist_ok=True)
SCRIPT = ["This is Goli, now in real 3D.", "Same voice, same channel, a brand new look.",
          "Watch his mouth: it moves with every word.", "Follow for one AI story a day."]
voice = out / "voice.mp3"
res = ProviderRegistry(ROOT / "config/providers.json").voice(live=True).synthesize(" ".join(SCRIPT), voice)
said = [w for w in (res.details or {}).get("words") or []]
dur = float((res.details or {}).get("duration_seconds") or 10.0)
print(json.dumps({"voice_s": round(dur, 2), "characters": (res.details or {}).get("characters")}))

# lines from the voice's own word timings (even spread if none came back)
flat = [w for ln in SCRIPT for w in ln.split()]
times = [(float(w.get("start", 0)), float(w.get("end", 0))) for w in said] if len(said) == len(flat) else \
    [(i * dur / len(flat), (i + 0.8) * dur / len(flat)) for i in range(len(flat))]
lines, k = [], 0
for i, tx in enumerate(SCRIPT):
    ws = []
    for w in tx.split():
        ws.append(Word(w.strip(".,:?"), times[k][0], times[k][1]))
        k += 1
    lines.append(TimedLine(i, tx, "", "", "", "", ws[0].start, ws[-1].end, ws))

cues = lipsync(voice, out / "cues.json")
raw = {"scenes": [
    {"type": "studio", "first_line": 0, "last_line": 0, "poses": [{"pose": "wave", "word": "Goli"}], "screen_words": "Goli in 3D", "punch": "3D"},
    {"type": "studio", "first_line": 1, "last_line": 1, "poses": [{"pose": "point", "word": "new"}], "screen_words": "A brand new look", "punch": "new"},
    {"type": "studio", "first_line": 2, "last_line": 2, "poses": [{"pose": "think", "word": "mouth"}], "screen_words": "Every word", "punch": "word"},
    {"type": "follow", "first_line": 3, "last_line": 3, "label": "One AI story a day"}]}
edit = editor.build(raw, lines, dur + 0.4, "short", [], None, cues, [], logo_tile_maker(out / "logos"))
editor.save(edit, out / "edit-list.json")
print(json.dumps({"notes": edit["notes"], "scenes": [s["type"] for s in edit["scenes"]]}))
render(edit, out, voice, out / "video.mp4", outfit_today(), None)
print("rendered", out / "video.mp4")
