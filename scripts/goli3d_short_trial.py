"""TRIAL (owner 2026-11-21): a 10-second Goli Short with the 3D Goli, to see the new look talking.

Uses the owner's own saved recording (assets/trial/voice.mp3 + voice.txt, one line per sentence). Owner
2026-11-21: never spends ElevenLabs characters; with no saved recording it stops and says so. It lip-syncs it with
Rhubarb, builds a Goli studio edit (three poses) and renders it exactly as the daily Short is rendered.
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
from golide_engine.vector.align import TimedLine, Word  # noqa: E402

out = ROOT / "build/goli3d-trial"
out.mkdir(parents=True, exist_ok=True)
saved = ROOT / "assets/trial/voice.mp3"
if not saved.exists() or not saved.with_suffix(".txt").exists():
    sys.exit("No saved recording at assets/trial/voice.mp3 (+ voice.txt). The trial never uses ElevenLabs (owner 2026-11-21).")
SCRIPT = [ln.strip() for ln in saved.with_suffix(".txt").read_text().splitlines() if ln.strip()]
voice = saved
said = []
import subprocess  # noqa: E402
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(voice)],
                           capture_output=True, text=True, check=True).stdout)

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
