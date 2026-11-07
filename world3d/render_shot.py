"""Compile one shot list into frames. Run with Blender's Python (pip install bpy):
python render_shot.py shots/space_hubble.json --out DIR --quality video [--frames 0-239] [--stills 0,120]
Finished frames are kept, so a stopped job resumes and long shots can split across jobs."""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bpy  # noqa: E402

from kit import actions as _a, cameras, effects as _e, labels, lights as _l, materials as _m  # noqa: E402,F401
from kit import objects, parts as _p, stage, worlds as _w  # noqa: E402,F401
from kit.registry import actions, cameras as camera_moves, effects, lights, worlds  # noqa: E402


def compile_shot(shot, quality):
    fps, duration = shot.get("fps", 24), shot["duration"]
    scene = stage.reset(quality, fps, shot.get("vertical", False))
    world = worlds.get(shot["world"]["name"])(scene, shot["world"])
    model = objects.build(shot["object"]["blueprint"], shot["object"].get("blueprint_dir"))
    lights.get(shot["light"]["rig"])(world, shot["light"], model.meshes())
    model.fit(shot["object"].get("size", 10.0))
    _a.orient(model, shot["object"])
    _w.stand_on(world, model)
    cam = cameras.make(shot["camera"])
    timeline = []
    for a in shot.get("actions", []):
        timeline.append(actions.get(a["type"])(model, a))
    bpy.context.view_layer.update()
    for e in shot.get("effects", []):
        timeline.append(effects.get(e["type"])(model, e))
    # The camera moves last, so it frames the object after every part has moved this frame.
    timeline.append(camera_moves.get(shot["camera"]["move"])(cam, shot["camera"], duration, model))
    return scene, model, timeline, fps, duration


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shot")
    ap.add_argument("--out", required=True)
    ap.add_argument("--quality", default="video", choices=stage.QUALITY)
    ap.add_argument("--frames", help="first-last frame")
    ap.add_argument("--stills", help="comma list of frames")
    a = ap.parse_args()
    shot = json.loads(Path(a.shot).read_text())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    scene, model, timeline, fps, duration = compile_shot(shot, a.quality)
    total = int(duration * fps)
    if a.stills:
        frames = [int(x) for x in a.stills.split(",")]
    elif a.frames:
        lo, hi = map(int, a.frames.split("-"))
        frames = list(range(lo, min(hi + 1, total)))
    else:
        frames = list(range(total))
    lab_path = out / "labels.json"
    lab = json.loads(lab_path.read_text()) if lab_path.exists() else {}
    for f in frames:
        t = f / fps
        for update in timeline:
            update(t)
        bpy.context.view_layer.update()
        name = f"f{f:05d}"
        lab[name] = labels.project(scene, model, shot.get("labels", []), t)
        target = out / f"{name}.png"
        if target.exists():
            continue
        scene.render.filepath = str(target)
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"FRAME {f} {time.time() - t0:.1f}s", flush=True)
        lab_path.write_text(json.dumps(lab))
    lab_path.write_text(json.dumps(lab))


if __name__ == "__main__":
    main()
