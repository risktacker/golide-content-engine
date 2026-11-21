"""Render Goli's 3D studio plates (owner 2026-11-21: built once in Blender, reused in every video).

For each format (short, long, lower): back.webp (behind Goli: wall, TV, shelves, neon, chair), front.webp (in front
of him: the table, laptop, mug, mic; transparent around them) and meta.json (TV screen corners, mug top for the
steam, the table's lit edge). Usage: python tools/goli3d_studio.py [short long lower]   (Blender's bpy)
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "src" / "golide_engine" / "goli3d" / "studio_model.py"
OUT = ROOT / "assets" / "goli3d" / "studio"
LOGO = OUT / "neon_logo.png"


def plate(fmt: str, which: str) -> dict:
    d = OUT / fmt
    d.mkdir(parents=True, exist_ok=True)
    raw = d / f"{which}.png"
    spec = {"fmt": fmt, "pass": which, "scale": 1.0, "samples": 64, "neon_logo": str(LOGO)}
    subprocess.run([sys.executable, str(MODEL), json.dumps(spec), str(raw)], check=True, capture_output=True)
    meta = json.loads(Path(str(raw) + ".json").read_text())
    Path(str(raw) + ".json").unlink()
    im = Image.open(raw).convert("RGBA")
    off = [0, 0]
    if which == "back" and meta.get("top"):          # the lower third only shows the set below its top line
        off = [0, int(meta["top"])]
        im = im.crop((0, off[1], im.width, im.height))
    elif which == "front":
        box = im.getchannel("A").getbbox() or (0, 0, im.width, im.height)
        off = [box[0], box[1]]
        im = im.crop(box)
    im.save(d / f"{which}.webp", "WEBP", quality=93, method=6)
    raw.unlink()
    meta[f"{which}_at"] = off
    return meta


if __name__ == "__main__":
    for fmt in sys.argv[1:] or ("short", "long", "lower"):
        meta = plate(fmt, "back")
        meta.update({k: v for k, v in plate(fmt, "front").items() if k.endswith("_at")})
        (OUT / fmt / "meta.json").write_text(json.dumps(meta, indent=1))
        print(fmt, "done", flush=True)
