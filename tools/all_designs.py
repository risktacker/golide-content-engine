"""Every Goli thumbnail design drawn for one video, side by side (owner 2026-11-20: "all those designs can be used for
any video type; show me all of them for this video"). Ingredient rules are ignored on purpose: each design gets the
story's real photos, the brands' real logos and the words.

    python tools/all_designs.py "<title>" "<words>" "<punch>" "<brand,brand>" "<wikipedia page,page>" "<person>" out.jpg
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from golide_engine.engine.source_capture import subject_pictures  # noqa: E402
from golide_engine.vector import thumb_engine as E  # noqa: E402
from golide_engine.vector.thumb_engine import BY_NAME, Design, Story, logos, render  # noqa: E402

title, words, punch, brands, things, person, out = sys.argv[1:8]
pics_dir = ROOT / "build" / "all-designs" / "pics"
got = subject_pictures([t.strip() for t in things.split(",") if t.strip()], pics_dir, 1)
pics = [pics_dir / p for g in got for p in (g.get("photos") or ([g["photo"]] if g.get("photo") else []))]
pics = [p for p in pics if p.exists()]
found = [(b, logos.find(b)) for b in [b.strip() for b in brands.split(",") if b.strip()]]
found = [(b, i) for b, i in found if i]
print(json.dumps({"photos": [p.name for p in pics], "logos": [b for b, _ in found]}))

# the wired designs plus the ones drawn in code but never on the menu
extra = [Design(n, n, lambda s: True, getattr(E, f"d_{n}")) for n in ("glass_point", "dark_drama", "mega_word",
                                                                      "grid_arrow", "studio") if hasattr(E, f"d_{n}")]
designs = [d for d in E.DESIGNS] + [d for d in extra if d.name not in BY_NAME]
tiles = []
for d in designs:
    s = Story(title, " ".join(words.split()).upper(), punch.strip().upper(), [b for b, _ in found], [i for _, i in found],
              pics, pics[0] if pics else None, "royal", "money", 1, person if pics else "")
    E.T.REC = []
    try:
        image, hits = render(d, s)
        tiles.append((d.name, image.convert("RGB").resize((640, 360))))
        print(json.dumps({"design": d.name, "ok": True}))
    except Exception as exc:  # noqa: BLE001 - one failing design is shown as failed, the rest still draw
        print(json.dumps({"design": d.name, "error": str(exc)[:200]}))
        tile = Image.new("RGB", (640, 360), "#222")
        ImageDraw.Draw(tile).text((20, 170), f"{d.name}: {str(exc)[:70]}", fill="#f66")
        tiles.append((d.name, tile))
    finally:
        E.T.REC = None
cols = 3
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 650 + 10, rows * 400 + 10), "#111")
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
except OSError:
    font = ImageFont.load_default()
for k, (name, tile) in enumerate(tiles):
    x, y = 10 + (k % cols) * 650, 10 + (k // cols) * 400
    draw.text((x + 4, y + 4), name, fill="#ffd66b", font=font)
    sheet.paste(tile, (x, y + 32))
sheet.save(out, quality=86)
print(json.dumps({"sheet": out, "designs": len(tiles)}))
