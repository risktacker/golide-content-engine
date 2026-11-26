"""Build the living studio's 3D room (owner 2026-11-26): assets/goli3d/live/studio.glb + studio-set.json.

The long studio set from goli3d/studio_model.py as one whole room (back and side walls, ceiling, floor, the real chair),
every piece tagged and with its Cycles light baked into its own picture (goli3d/studio_export.py). About 10 minutes on
2 CPUs. python tools/goli3d_studio_live.py [samples]
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "goli3d" / "live"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    samples = int(next((a for a in sys.argv[1:] if a.isdigit()), 32))
    # resume: pieces baked by an interrupted build are reused (run it again to finish)
    spec = {"fmt": "long", "export": str(OUT / "studio.glb"), "bake_samples": samples, "tex": 0.8, "resume": "--resume" in sys.argv}
    subprocess.run([sys.executable, str(ROOT / "src/golide_engine/goli3d/studio_model.py"), json.dumps(spec), "/tmp/unused.png"], check=True)
    print(OUT / "studio.glb")


if __name__ == "__main__":
    main()
