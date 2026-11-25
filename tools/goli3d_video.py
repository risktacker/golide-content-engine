"""Render Goli's talking video sprites (owner 2026-11-21: the 3D Goli replaces the SVG one in every video).

For one pose: his body in each weekday outfit with the mouth at rest (full canvas, so every pose lines up), the
nine Rhubarb mouth shapes and a blink as small patches cut from the same camera, and meta.json with where each
patch goes. The video composer (edit/compose.py) stacks them and switches mouths on the voice cues as before.
Usage: python tools/goli3d_video.py <pose> [<pose> ...]   (Blender's bpy, Python 3.13)
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from golide_engine.goli3d.kits import glasses as kit_glasses  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "src" / "golide_engine" / "goli3d" / "model.py"
OUT = ROOT / "assets" / "goli3d" / "video"
CANVAS = (1000, 1100)
OUTFITS = ("royal", "ember", "emerald", "midnight", "violet", "sky", "crimson")
VISEMES = "ABCDEFGHX"
# the old Goli's face for each pose -> his 3D reaction (eyes and brows; the mouth comes from the voice)
FACE = {"talk": "neutral", "explain": "neutral", "point": "smug", "point_up": "smug", "point_left": "smug",
        "shock": "astonished", "think": "thinking", "thumbs_up": "happy", "shrug": "confused",
        "point_both_up": "happy", "wave": "happy"}


def render(spec: dict, out: Path) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    spec = dict(spec, bg="transparent", size=list(CANVAS), samples=spec.get("samples", 40))
    subprocess.run([sys.executable, str(MODEL), json.dumps(spec), str(out)], check=True, capture_output=True)
    side = Path(str(out) + ".json")
    meta = json.loads(side.read_text())
    side.unlink()
    return meta


def feather(src: Path, dst: Path) -> None:
    """Soften a patch's edges so it melts into the body render under it; saved as WebP."""
    im = Image.open(src).convert("RGBA")
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).ellipse((6, 6, im.width - 6, im.height - 6), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(5))
    a = Image.composite(im.getchannel("A"), Image.new("L", im.size, 0), m)
    im.putalpha(a)
    im.save(dst, "WEBP", quality=94, method=6)
    src.unlink()


def pose(p: str) -> None:
    d = OUT / p
    face = FACE.get(p, "neutral")
    base = {"pose": p, "expr": face, "viseme": "X"}
    meta = {"canvas": list(CANVAS), "face": face, "patches": {}}
    meta["body"] = {}
    for o in OUTFITS:
        f = d / f"body-{o}.png"
        info = render(dict(base, outfit=o, glasses=kit_glasses(o)), f)   # owner 2026-11-25: the day's kit
        im = Image.open(f).convert("RGBA")
        box = im.getchannel("A").getbbox()
        im.crop(box).save(d / f"body-{o}.webp", "WEBP", quality=94, method=6)
        f.unlink()
        meta["body"][o] = list(box[:2])
        if o == "royal":
            solid = im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
            meta.update(head=info["head"], waist=info["waist"], bbox=list(solid))
    for v in VISEMES:
        name = f"mouth-{v}"
        info = render(dict(base, region="mouth", viseme=v), d / f"{name}.png")
        x0, y0, x1, y1 = info["mouth"]
        feather(d / f"{name}.png", d / f"{name}.webp")
        meta["patches"][v] = [max(0, round(x0 - 6)), max(0, round(y0 - 6))]
    # the eyes: closed and half-closed, in every kit's glasses (owner 2026-11-25: a real, smooth blink)
    for g in sorted(set(kit_glasses(o) for o in OUTFITS)):
        for lid, spec in (("blink", dict(blink=True)), ("half", dict(blink=0.5))):
            name = f"{lid}-{g}"
            info = render(dict(base, region="eyes", glasses=g, **spec), d / f"{name}.png")
            x0, y0, x1, y1 = info["eyes"]
            feather(d / f"{name}.png", d / f"{name}.webp")
            meta["patches"][name] = [max(0, round(x0 - 6)), max(0, round(y0 - 6))]
    meta["patches"].setdefault("blink", meta["patches"]["blink-round_gold"])
    (d / "meta.json").write_text(json.dumps(meta, indent=1))
    print(p, "done", flush=True)


if __name__ == "__main__":
    for p in sys.argv[1:] or list(FACE):
        pose(p)
