"""Self-test of the split render (edit/remote.py) on GitHub: builds a short real composition (studio light, a 3D
metaphor, captions), films it across 2 machines through edit-render.yml, and checks the joined picture frame by frame
count against the film. Free (no model calls)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from golide_engine.edit import remote  # noqa: E402
from golide_engine.edit.compose import Composer  # noqa: E402

out = Path("selftest"); out.mkdir(exist_ok=True)
dur = 12.0
# the living studio as production films it (owner 2026-11-26): the 3D room, the live Goli with a storyboard shot and
# act, the page on the big screen, a 3D metaphor cut-in with real logos, then the close shot
from PIL import Image  # noqa: E402
img = out / "page.png"; Image.new("RGB", (1280, 720), (30, 60, 140)).save(img)
words = [{"text": w, "at": 0.3 + i * 0.35} for i, w in enumerate("Last month one developer shook Adobe. Crazy right? Here's the thing.".split())]
cues = [{"start": round(0.3 + i * 0.12, 3), "value": "BCDBAEXC"[i % 8]} for i in range(60)]
e = {"format": "long", "duration": dur, "live_studio": True,
     "captions": [{"start": 0, "end": dur, "words": words, "keys": []}],
     "scenes": [{"type": "host", "start": 0.0, "duration": 6.0, "data": {"place": "studio", "cues": cues, "poses": [],
                 "screen": img, "shot": "wide", "act": "sip"}},
                {"type": "metaphor", "start": 6.0, "duration": 3.0, "data": {"kind": "scales", "left": "Claude", "right": "Gmail", "at": 1.0}},
                {"type": "host", "start": 9.0, "duration": 3.0, "data": {"place": "studio", "cues": cues[:20], "poses": [],
                 "shot": "close", "act": "laugh"}}]}
comp = out / "composition"
Composer("long", outfit="royal").build(e, comp)
pic = remote.render(comp, dur, out / "picture.mp4", label="selftest", wait_minutes=40, poll_seconds=15)
n = remote.frames_of(pic)
print(json.dumps({"status": "split_render_selftest", "frames": n, "expected": round(dur * 30)}))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pic), "-vf", "fps=1,scale=480:-1,tile=6x1", "-frames:v", "1",
                str(out / "sheet.jpg")], check=True)
# every second of the picture has content (never a black or empty frame from a machine that failed to draw 3D)
import numpy as np  # noqa: E402
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(pic), "-vf", "fps=1,scale=64:36,format=gray", "-f", "rawvideo", "-"],
                     capture_output=True, check=True).stdout
levels = [round(float(np.frombuffer(raw[i:i + 64 * 36], dtype=np.uint8).mean()), 1) for i in range(0, len(raw), 64 * 36)]
print(json.dumps({"status": "split_render_levels", "per_second": levels}))
sys.exit(0 if abs(n - round(dur * 30)) <= 1 and min(levels) > 8 else 1)
