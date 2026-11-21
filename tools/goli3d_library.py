"""Render the Goli 3D reaction library (owner 2026-11-21): assets/goli3d/full/<pose>/<expression>.png.

Transparent cut-outs, cropped, drawn once and reused by every thumbnail and video. Needs Blender's Python module
(`pip install bpy==5.3.0`, Python 3.13). Usage: python tools/goli3d_library.py [pose ...]  (no pose = all).
Existing files are kept; delete one to redraw it.
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "src" / "golide_engine" / "goli3d" / "model.py"
OUT = ROOT / "assets" / "goli3d" / "full"
EXPRS = ("neutral happy laughing excited angry determined surprised astonished scared disappointed crying shy "
         "trying_hard thinking confused smug sleepy hungry in_love savage").split()
PLAN = {
    "talk": EXPRS,
    "point_left": ["smug", "excited", "determined", "happy"], "point": ["smug", "excited", "determined", "happy"],
    "point_up": ["smug", "excited", "surprised"], "thumbs_up": ["happy", "excited", "smug"],
    "shock": ["astonished", "scared", "excited", "surprised"], "point_both_up": ["excited", "happy", "astonished"],
    "wave": ["happy", "excited"], "shrug": ["confused", "disappointed", "smug"], "think": ["thinking", "confused"],
    "explain": ["neutral", "determined", "happy", "smug"], "facepalm": ["disappointed", "trying_hard"],
}


def render(job):
    pose, expr = job
    f = OUT / pose / f"{expr}.png"
    if f.exists():
        return
    f.parent.mkdir(parents=True, exist_ok=True)
    raw = f.with_suffix(".raw.png")
    spec = dict(expr=expr, pose=pose, bg="transparent", size=[900, 990], samples=40)
    subprocess.run([sys.executable, str(MODEL), json.dumps(spec), str(raw)], check=True, capture_output=True)
    im = Image.open(raw).convert("RGBA")
    solid = im.getchannel("A").point(lambda v: 255 if v > 40 else 0)
    im.crop(solid.getbbox()).save(f, optimize=True)
    raw.unlink()
    print(pose, expr, flush=True)


if __name__ == "__main__":
    poses = sys.argv[1:] or list(PLAN)
    jobs = [(p, e) for p in poses for e in PLAN[p]]
    with ThreadPoolExecutor(2) as ex:
        list(ex.map(render, jobs))
