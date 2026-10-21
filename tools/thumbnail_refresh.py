"""One-off (owner request 2026-10-21, remove after 72 hours): fresh thumbnails for
the long videos already published, in the new look.

For each video: the text model reads its title and description and writes the
thumbnail subject (one object or metaphor), 1 to 3 curiosity words, the punch word
and the meaning colours; the image model draws the art with the engine's locked
thumbnail prompt; the words are typeset by the engine. The owner sets them on
YouTube himself. Output: thumbnail-refresh/<youtube id>.jpg plus words.json.

    python tools/thumbnail_refresh.py golide-long-2026-10-06 golide-long-2026-10-10 ...
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
from golide_engine.vector.illustrate import ACCENTS  # noqa: E402
from golide_engine.vector.thumb_text import stamp_thumbnail  # noqa: E402
from golide_engine.vector.thumbnail_style import palette_rgb, thumbnail_prompt  # noqa: E402

OUT = ROOT / "thumbnail-refresh"

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "moment": {"type": "string"},
        "words": {"type": "string"},
        "punch": {"type": "string"},
        "colors": {"type": "array", "items": {"type": "string", "enum": list(ACCENTS)}},
    },
    "required": ["moment", "words", "punch", "colors"],
}

RULES = """\
You design ONE YouTube thumbnail for a GOLIDE explainer video (black space, fine
luminous line art, one glowing part). Return:
- "moment": one sentence naming ONE object or visual metaphor that captures the
  tension of the story, understood in one second, and the ONE part of it that glows.
  Examples: "a house key on a ring whose teeth glow" (leaked API keys); "an old
  balance scale, a glowing chip in one pan outweighing a lump of coal" (a market
  record); "a glass padlock with a crack through its glowing keyhole" (an attack
  path). Never a face, avatar or character; a hand only if the metaphor needs it.
- "words": ONE TO THREE words printed huge on the thumbnail. A curiosity gap the
  title does NOT answer, never a summary and never the title's words. Examples:
  "WHO GETS IT?", "KEYS LEAKED", "NOT FLYING", "OUTWEIGHED".
- "punch": the one word of "words" shown in the glow colour, copied exactly.
- "colors": two accent colours by meaning from gold (value, money), rose (risk,
  warning), teal (tech, AI, data), ivory (hope, neutral), copper (everyday things);
  the first is the glow. Not always teal.
"""


def refresh(production_id: str, providers: ProviderRegistry) -> dict:
    record = json.loads((ROOT / "data" / "production-records" / f"{production_id}.json").read_text(encoding="utf-8"))
    meta = record.get("metadata") or {}
    video_id = record["youtube_video_id"]
    design = providers.text(live=True).generate_json(
        RULES, f"TITLE\n{meta.get('title', '')}\n\nDESCRIPTION\n{str(meta.get('description', ''))[:1500]}",
        SCHEMA, max_output_tokens=4000).value
    colors = [c for c in design["colors"] if c in ACCENTS] or ["gold", "teal"]
    raw = OUT / f"{video_id}-raw.png"
    final = OUT / f"{video_id}.jpg"
    prompt = thumbnail_prompt(meta.get("title", ""), design["moment"], colors)
    images = providers.thumbnails(live=True)
    size = providers.config["thumbnail"]["size"]
    for attempt in (prompt, prompt + SAFE_RETRY):
        try:
            images.create_thumbnail(attempt, raw, size, None)
            break
        except Exception as exc:  # noqa: BLE001
            if not is_moderation_block(exc):
                raise
    normalize_thumbnail(raw, final)
    stamp_thumbnail(final, design["words"], design["punch"], palette_rgb(colors))
    raw.unlink(missing_ok=True)
    return {"production_id": production_id, "youtube_video_id": video_id, "title": meta.get("title", ""),
            "words": design["words"], "punch": design["punch"], "moment": design["moment"], "colors": colors,
            "file": final.name}


def main(ids: list[str]) -> None:
    OUT.mkdir(exist_ok=True)
    providers = ProviderRegistry(ROOT / "config" / "providers.json")
    done = []
    for production_id in ids:
        try:
            done.append(refresh(production_id, providers))
            print(json.dumps({"status": "thumbnail_ready", **done[-1]}))
        except Exception as exc:  # noqa: BLE001 - one failure never stops the others
            print(f"::warning title=Thumbnail failed::{production_id}: {str(exc)[:300]}")
    (OUT / "words.json").write_text(json.dumps(done, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not done:
        raise SystemExit("no thumbnail was made")


if __name__ == "__main__":
    main(sys.argv[1:])
