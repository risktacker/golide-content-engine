"""One-off (owner request 2026-10-25, remove once delivered): new thumbnails for two
published long videos, carrying their opening-card line instead of 1 to 3 words.

    python tools/thumbnail_replace.py '<production id>|<line>|<punch>|<colour>' ...

The text model picks the hero object from the title and description (a real, named
product drawn as it really looks); the image model draws it with the engine's locked
thumbnail prompt; the engine typesets the line. Output: thumbnail-refresh/<youtube id>.jpg
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golide_engine.providers.openai_media import SAFE_RETRY, is_moderation_block  # noqa: E402
from golide_engine.providers.registry import ProviderRegistry  # noqa: E402
from golide_engine.quality.visual import normalize_thumbnail  # noqa: E402
from golide_engine.vector.thumb_text import stamp_thumbnail  # noqa: E402
from golide_engine.vector.thumbnail_style import palette_rgb, thumbnail_prompt  # noqa: E402

OUT = ROOT / "thumbnail-refresh"
SCHEMA = {"type": "object", "additionalProperties": False,
          "properties": {"moment": {"type": "string"}}, "required": ["moment"]}
RULES = """\
Name the ONE hero subject for a YouTube thumbnail (black space, fine luminous line art,
one glowing part) in one sentence. When the video is about a real, named product, show
THAT product with its real, recognisable design, and name the one part of it that glows.
It must match the thumbnail line given, which is printed next to it. No faces, no people.
"""


def make(arg: str, providers: ProviderRegistry) -> dict:
    production_id, line, punch, colour = (part.strip() for part in arg.split("|"))
    record = json.loads((ROOT / "data" / "production-records" / f"{production_id}.json").read_text(encoding="utf-8"))
    meta = record.get("metadata") or {}
    video_id = record["youtube_video_id"]
    moment = providers.text(live=True).generate_json(
        RULES, f"TITLE: {meta.get('title', '')}\nTHUMBNAIL LINE: {line}\n"
               f"DESCRIPTION: {str(meta.get('description', ''))[:1500]}", SCHEMA, max_output_tokens=3000).value["moment"]
    colors = [colour, "ivory"]
    raw, final = OUT / f"{video_id}-raw.png", OUT / f"{video_id}.jpg"
    prompt = thumbnail_prompt(meta.get("title", ""), moment, colors)
    images = providers.thumbnails(live=True)
    for attempt in (prompt, prompt + SAFE_RETRY):
        try:
            images.create_thumbnail(attempt, raw, providers.config["thumbnail"]["size"], None)
            break
        except Exception as exc:  # noqa: BLE001
            if not is_moderation_block(exc):
                raise
    normalize_thumbnail(raw, final)
    stamp_thumbnail(final, line, punch, palette_rgb(colors))
    raw.unlink(missing_ok=True)
    return {"production_id": production_id, "youtube_video_id": video_id, "title": meta.get("title", ""),
            "line": line, "moment": moment, "file": final.name}


def main(args: list[str]) -> None:
    OUT.mkdir(exist_ok=True)
    providers = ProviderRegistry(ROOT / "config" / "providers.json")
    done = []
    for arg in args:
        try:
            done.append(make(arg, providers))
            print(json.dumps({"status": "thumbnail_ready", **done[-1]}))
        except Exception as exc:  # noqa: BLE001
            print(f"::warning title=Thumbnail failed::{arg}: {str(exc)[:300]}")
    (OUT / "made.json").write_text(json.dumps(done, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not done:
        raise SystemExit("no thumbnail was made")


if __name__ == "__main__":
    main(sys.argv[1:])
