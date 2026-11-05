"""Replacement thumbnails, emailed to the owner (2026-11-05): "email me 2 replacements for each
video". Our own art in the older thumbnail look (the real object glowing on black, modelled on
the source video's idea) with 2 to 4 big words. About $0.05 a thumbnail.

    python tools/thumb_options.py <production_id> "<title>" [count]
"""

from __future__ import annotations

import json
import sys
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golide_engine.operations.email import _send  # noqa: E402
from golide_engine.providers.registry import ProviderRegistry  # noqa: E402
from golide_engine.quality.visual import normalize_thumbnail  # noqa: E402
from golide_engine.vector.thumbnail_style import DEFAULT, palette_rgb, thumbnail_colors  # noqa: E402
from golide_engine.vector.thumbnail_v2 import big_words, fetch_reference, stamp_overlap, thumbnail_prompt_v2  # noqa: E402

OUT = ROOT / "production-queue" / "preview" / "thumb-options"


def spec_for(production_id: str) -> dict:
    for path in sorted((ROOT / "production-queue").glob(f"{production_id}*.json")):
        if path.name.count(".") <= 2 and "script-plan" not in path.name:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                pass
    return {}


def main(production_id: str, title: str, count: int = 2) -> None:
    providers = ProviderRegistry(ROOT / "config" / "providers.json")
    text, images = providers.text(live=True), providers.thumbnails(live=True)
    spec, work = spec_for(production_id), ROOT / "productions" / production_id
    try:
        plan = json.loads((work / "visual-plan.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        plan = {}
    cover = plan.get("cover") or {}
    colors = thumbnail_colors(cover, plan.get("scenes") or []) if plan else list(DEFAULT)
    source = spec.get("source_breakout") or {}
    OUT.mkdir(parents=True, exist_ok=True)
    reference = fetch_reference(str(source.get("url") or ""), OUT / f"{production_id}-reference.jpg")
    words = big_words(text, title, str(cover.get("text", "")), str(source.get("title") or ""), count)
    made = []
    for n in range(count):
        raw, final = OUT / f"{production_id}-{n + 1}-raw.png", OUT / f"{production_id}-option-{n + 1}.png"
        prompt = thumbnail_prompt_v2(title, str(cover.get("thumbnail_moment") or ""), colors, reference is not None)
        images.create_thumbnail(prompt, raw, providers.config["thumbnail"]["size"], [reference] if reference else None)
        normalize_thumbnail(raw, final)
        line, punch = words[n % len(words)] if words else (str(cover.get("text", "")), str(cover.get("gold", "")))
        stamp_overlap(final, line, punch, palette_rgb(colors))
        made.append((final, line))
        print(json.dumps({"made": final.name, "words": line}))
    msg = EmailMessage()
    msg["Subject"] = f"GOLIDE: {count} replacement thumbnails for \"{title}\""
    msg.set_content("\n".join(
        [f"{count} replacement thumbnails for: {title}", ""]
        + [f"Option {i + 1}: {line}" for i, (_, line) in enumerate(made)]
        + ["", "To use one: YouTube Studio > the video > Edit > Thumbnail > Upload."]))
    for path, _ in made:
        msg.add_attachment(path.read_bytes(), maintype="image", subtype="png", filename=path.name)
    print(json.dumps({"emailed": _send(msg)}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2)
