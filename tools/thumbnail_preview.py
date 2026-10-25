"""One-off preview (owner request 2026-10-25, removed once he approves): thumbnails drawn
from the real product (the modelled video's thumbnail as reference) with the line set
over the art. Nothing in the engine uses this yet.

    python tools/thumbnail_preview.py '<production id>|<source url>|<line>|<punch>|<colour>' ...
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
from golide_engine.vector.thumbnail_style import palette_rgb  # noqa: E402
from golide_engine.vector.thumbnail_v2 import fetch_reference, stamp_overlap, thumbnail_prompt_v2  # noqa: E402

OUT = ROOT / "thumbnail-preview"
SCHEMA = {"type": "object", "additionalProperties": False,
          "properties": {"moment": {"type": "string"}}, "required": ["moment"]}
RULES = ("Name the ONE hero subject for a YouTube thumbnail in one sentence: the real, named product "
         "the video is about, by name only (a reference image shows its real look, so never describe "
         "its shape, legs, wheels or colours), and the ONE part of it that glows.")


def _download(url: str, dest: Path):
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
    except Exception:  # noqa: BLE001
        return None
    if len(data) < 5000:
        return None
    from PIL import Image
    import io
    Image.open(io.BytesIO(data)).convert("RGB").save(dest, "JPEG", quality=92)
    return dest


def make(arg: str, providers: ProviderRegistry) -> dict:
    parts = [part.strip() for part in arg.split("|")]
    production_id, source, line, punch, colour = parts[:5]
    given_moment = parts[5] if len(parts) > 5 else ""
    record = json.loads((ROOT / "data" / "production-records" / f"{production_id}.json").read_text(encoding="utf-8"))
    meta = record.get("metadata") or {}
    refs = []
    for n, url in enumerate(u for u in source.split(",") if u.strip()):
        dest = OUT / f"{production_id}-reference-{n}.jpg"
        got = fetch_reference(url, dest) if "youtu" in url else _download(url.strip(), dest)
        if got:
            refs.append(got)
    reference = refs[0] if refs else None
    moment = given_moment or providers.text(live=True).generate_json(
        RULES, f"TITLE: {meta.get('title', '')}\nLINE: {line}\nDESCRIPTION: {str(meta.get('description', ''))[:1500]}",
        SCHEMA, max_output_tokens=3000).value["moment"]
    colors = [colour, "ivory"]
    raw, final = OUT / f"{production_id}-raw.png", OUT / f"{production_id}.jpg"
    prompt = thumbnail_prompt_v2(meta.get("title", ""), moment, colors, reference is not None)
    images = providers.thumbnails(live=True)
    for attempt in (prompt, prompt + SAFE_RETRY):
        try:
            images.create_thumbnail(attempt, raw, providers.config["thumbnail"]["size"],
                                    refs or None)
            break
        except Exception as exc:  # noqa: BLE001
            if not is_moderation_block(exc):
                raise
    normalize_thumbnail(raw, final)
    import shutil
    shutil.copy(final, OUT / f"{production_id}-art.jpg")   # the art without words, for re-layout
    stamp_overlap(final, line, punch, palette_rgb(colors))
    raw.unlink(missing_ok=True)
    return {"production_id": production_id, "youtube_video_id": record["youtube_video_id"],
            "line": line, "moment": moment, "reference": len(refs), "file": final.name}


def main(args: list[str]) -> None:
    OUT.mkdir(exist_ok=True)
    providers = ProviderRegistry(ROOT / "config" / "providers.json")
    done = []
    for arg in args:
        try:
            done.append(make(arg, providers))
            print(json.dumps({"status": "preview_ready", **done[-1]}))
        except Exception as exc:  # noqa: BLE001
            print(f"::warning title=Preview failed::{arg}: {str(exc)[:300]}")
    (OUT / "made.json").write_text(json.dumps(done, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not done:
        raise SystemExit("no preview was made")


if __name__ == "__main__":
    main(sys.argv[1:])
