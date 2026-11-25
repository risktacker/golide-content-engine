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
POSES = ("talk", "point_left", "point", "point_up", "thumbs_up", "shock", "point_both_up", "wave", "shrug", "think",
         "explain", "facepalm")
PLAN = {p: EXPRS for p in POSES}     # owner 2026-11-21: every pose with every reaction, no stand-ins


sys.path.insert(0, str(ROOT / "src"))
from golide_engine.goli3d.kits import KITS  # noqa: E402


def render(job):
    pose, expr, kit = job
    f = (OUT / "kits" / kit / pose if kit else OUT / pose) / f"{expr}.png"
    if f.exists():
        return
    f.parent.mkdir(parents=True, exist_ok=True)
    raw = f.with_suffix(".raw.png")
    spec = dict(expr=expr, pose=pose, bg="transparent", size=[900, 990], samples=40)
    if kit:                                   # owner 2026-11-25: the weekday's hoodie and glasses
        spec.update(outfit=kit, glasses=KITS[kit])
    subprocess.run([sys.executable, str(MODEL), json.dumps(spec), str(raw)], check=True, capture_output=True)
    im = Image.open(raw).convert("RGBA")
    solid = im.getchannel("A").point(lambda v: 255 if v > 40 else 0)
    box = solid.getbbox()
    side = Path(str(raw) + ".json")
    head = json.loads(side.read_text())["head"]
    head = [max(0, round(head[0] - box[0])), max(0, round(head[1] - box[1])), round(head[2] - box[0]), round(head[3] - box[1])]
    from PIL.PngImagePlugin import PngInfo
    meta = PngInfo()
    meta.add_text("head", ",".join(map(str, head)))         # x0,y0,x1,y1 of his head in this file
    im.crop(box).save(f, optimize=True, pnginfo=meta)
    raw.unlink()
    side.unlink()
    print(pose, expr, flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    kits = [a.split("=", 1)[1] for a in args if a.startswith("kit=")]
    kits = list(KITS) if kits == ["all"] else kits or [None]
    poses = [a for a in args if not a.startswith("kit=")] or list(PLAN)
    jobs = [(p, e, k) for k in kits for p in poses for e in PLAN[p]]
    with ThreadPoolExecutor(2) as ex:
        list(ex.map(render, jobs))
