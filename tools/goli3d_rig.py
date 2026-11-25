"""Build Goli's rigged 3D model (living studio, owner 2026-11-25): assets/goli3d/live/goli.glb + goli-rig.json.

python tools/goli3d_rig.py            (about 15 s; Blender's bpy module)
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "goli3d" / "live"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"rig": True, "out": str(OUT / "goli.glb"), "outfit": "royal", "expr": "neutral"}
    subprocess.run([sys.executable, str(ROOT / "src/golide_engine/goli3d/model.py"), json.dumps(spec), "/tmp/unused.png"], check=True)
    print(OUT / "goli.glb")


if __name__ == "__main__":
    main()
