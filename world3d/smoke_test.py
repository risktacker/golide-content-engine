"""Proves the whole path on real Blender with no paid calls: a script goes in, a finished
video comes out, and nobody writes a shot by hand. Uses a stand-in for the text model.
python world3d/smoke_test.py --blender-python PATH --out DIR"""
import argparse
import json
import subprocess
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from test_explain3d import GEAR, SHOT, WORDS  # noqa: E402

from golide_engine.explain3d import catalog, stage  # noqa: E402
from golide_engine.vector.render import VectorRenderer  # noqa: E402

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
from kit import actions, effects, materials, parts, worlds
from kit.registry import actions as a, effects as e, materials as m, parts as p, worlds as w
print(json.dumps({'builders': sorted(p.items), 'materials': sorted(m.items), 'worlds': sorted(w.items)}))
"""
    out = subprocess.run([python, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    real = json.loads(out.strip().splitlines()[-1])
    cat = catalog.load()
    assert sorted(cat["builders"]) == real["builders"], "catalog builders differ from the kit"
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
    narration = out / "voice.wav"
    with wave.open(str(narration), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\0\0" * 16000 * 9)
    plan = {"title": "Gearbox", "lines": [{"text": t, "visual": "title"} for t in LINES]}
    video = out / "video.mp4"
    VectorRenderer("long", fps=12).render(plan, WORDS, narration, video, 9.0, clips=clips)
    assert video.stat().st_size > 10000, "no video"
    print("END TO END OK", video)


if __name__ == "__main__":
    main()
