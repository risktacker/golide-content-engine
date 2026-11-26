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
dur = 6.0
e = {"format": "long", "duration": dur,
     "captions": [{"start": 0, "end": dur, "words": [{"text": "Claude", "at": 0.3}, {"text": "wins", "at": 1.0}], "keys": []}],
     "scenes": [{"type": "metaphor", "start": 0.0, "duration": 3.0, "data": {"kind": "scales", "left": "Claude", "right": "Gmail", "at": 1.0}},
                {"type": "metaphor", "start": 3.0, "duration": 3.0, "data": {"kind": "cycle", "items": ["Build", "Ship", "Learn"], "at": 1.0}}]}
comp = out / "composition"
Composer("long", outfit="royal").build(e, comp)
pic = remote.render(comp, dur, out / "picture.mp4", label="selftest", wait_minutes=40, poll_seconds=15)
n = remote.frames_of(pic)
print(json.dumps({"status": "split_render_selftest", "frames": n, "expected": round(dur * 30)}))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pic), "-vf", "fps=1,scale=480:-1,tile=6x1", "-frames:v", "1",
                str(out / "sheet.jpg")], check=True)
sys.exit(0 if abs(n - round(dur * 30)) <= 1 else 1)
