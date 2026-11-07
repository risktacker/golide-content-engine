"""Proves the whole path on real Blender with no paid calls: a script goes in, finished 3D
clips come out, and nobody writes a shot by hand. Uses a stand-in for the text model.
Touches nothing in src/: laying clips into the illustrated video is the later hand-off.
python world3d/smoke_test.py --blender-python PATH --out DIR"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from world3d.explain3d import catalog, stage  # noqa: E402
from world3d.tests.test_explain3d import GEAR, SHOT, WORDS  # noqa: E402

LINES = ["inside the gearbox the drive gear turns the", "shaft and that shaft spins the wheels every time"]
TIMES = [(0.0, 3.5), (3.5, 8.0)]


class StandIn:
    def __init__(self):
        self.answers = [{"shots": [SHOT]}, GEAR]

    def generate_json(self, *_, **__):
        return SimpleNamespace(value=self.answers.pop(0))


def check_catalog(python):
    code = """
import sys, json
sys.path.insert(0, 'world3d')
from kit import actions, effects, materials, worlds
from kit.registry import actions as a, effects as e, materials as m, worlds as w
print(json.dumps({'materials': sorted(m.items), 'worlds': sorted(w.items)}))
"""
    out = subprocess.run([python, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    real = json.loads(out.strip().splitlines()[-1])
    cat = catalog.load()
    assert set(cat["materials"]) <= set(real["materials"]), "catalog offers a material the kit lacks"
    assert sorted(cat["worlds"]) == real["worlds"], "catalog worlds differ from the kit"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender-python", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    check_catalog(a.blender_python)

    def render(path, folder, quality):
        shot = json.loads(Path(path).read_text())
        shot["fps"] = 6
        Path(path).write_text(json.dumps(shot))
        stage.render_shot(path, folder, "smoke", a.blender_python)

    clips = stage.run(out / "3d", "long", LINES, TIMES, WORDS, "facts", StandIn(), lambda *_: None, render=render)
    assert clips, "no clip came out"
    assert len(list(Path(clips[0]["frames"]).glob("f*.png"))) > 10, "clip has no frames"
    video = out / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(clips[0]["fps"]),
                    "-i", str(Path(clips[0]["frames"]) / "f%05d.png"), "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", str(video)], check=True)
    assert video.stat().st_size > 10000, "no video"
    print("END TO END OK", video)


if __name__ == "__main__":
    main()
