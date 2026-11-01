"""Preview of modelled thumbnails (owner direction 2026-11-01): 3 long thumbnails and 2 Shorts
covers, each beside the source thumbnail it is modelled on. Saved to production-queue/preview/."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golide_engine.providers.openai_media import OpenAILineArtProvider  # noqa: E402
from golide_engine.providers.registry import ProviderRegistry  # noqa: E402
from golide_engine.quality.visual import normalize_thumbnail  # noqa: E402
from golide_engine.vector.illustrate import illustration_prompt  # noqa: E402
from golide_engine.vector.layouts import art_size  # noqa: E402
from golide_engine.vector.short_cover import drawing_cutout  # noqa: E402
from golide_engine.vector.thumb_model import (canvas_from_layout, layout_json, modelled_prompt,  # noqa: E402
                                              place_text, read_layout)
from golide_engine.vector.thumbnail_v2 import fetch_reference  # noqa: E402

OUT = ROOT / "production-queue" / "preview"


def picks(fmt: str, count: int) -> list[dict]:
    items = []
    for path in sorted((ROOT / "production-queue").glob(f"golide-{fmt}-*.completed.json"), reverse=True):
        spec = json.loads(path.read_text(encoding="utf-8"))
        url = (spec.get("source_breakout") or {}).get("url", "")
        if url:
            items.append({"id": spec["id"], "title": spec.get("title", ""), "url": url})
        if len(items) == count:
            break
    return items


def pair(source: Path, ours: Image.Image, label: str, out: Path) -> None:
    src = Image.open(source).convert("RGB")
    height = 720
    src = src.resize((int(src.width * height / src.height), height))
    ours = ours.resize((int(ours.width * height / ours.height), height))
    sheet = Image.new("RGB", (src.width + ours.width + 60, height + 70), (24, 24, 28))
    sheet.paste(src, (20, 50))
    sheet.paste(ours, (src.width + 40, 50))
    ImageDraw.Draw(sheet).text((20, 14), f"SOURCE  |  OURS   {label}", fill=(235, 235, 235))
    sheet.save(out, quality=90)


def main() -> None:
    providers = ProviderRegistry(ROOT / "config" / "providers.json")
    text = providers.text(live=True)
    OUT.mkdir(parents=True, exist_ok=True)
    thumbs = providers.thumbnails(live=True)
    for item in picks("long", 3):
        work = OUT / item["id"]
        ref = fetch_reference(item["url"], work / "source.jpg")
        if ref is None:
            continue
        try:
            layout = read_layout(text, ref, item["title"])
            (work / "layout.json").write_text(layout_json(layout), encoding="utf-8")
            raw = work / "raw.png"
            thumbs.create_thumbnail(modelled_prompt(item["title"], "", layout, True), raw,
                                    providers.config["thumbnail"]["size"], [ref])
            final = work / "ours.jpg"
            normalize_thumbnail(raw, final)
            image = place_text(Image.open(final), layout)
            image.save(final, quality=92)
            pair(ref, image, item["title"], OUT / f"long-{item['id']}.jpg")
            print(json.dumps({"long": item["id"], "their_text": layout["their_text"], "our_text": layout["our_text"]}))
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"long": item["id"], "error": str(exc)[:300]}))
    line_art = OpenAILineArtProvider(providers.config["assets"]["support_model"],
                                     providers.config["assets"]["support_quality"])
    for item in picks("short", 2):
        work = OUT / item["id"]
        ref = fetch_reference(item["url"], work / "source.jpg")
        if ref is None:
            continue
        try:
            layout = read_layout(text, ref, item["title"])
            (work / "layout.json").write_text(layout_json(layout), encoding="utf-8")
            art = work / "art.png"
            prompt = illustration_prompt(f"{layout['subject']}, seen {layout['subject_angle']}. "
                                         f"It is unmistakably the real {layout['subject']}.", "its key part", "short")
            line_art.create(prompt, art, art_size("short", "single"), reference=ref)
            cut, mask = drawing_cutout(art, "gold")
            image = canvas_from_layout(cut, mask, layout)
            image.save(work / "ours.jpg", quality=92)
            pair(ref, image, item["title"], OUT / f"short-{item['id']}.jpg")
            print(json.dumps({"short": item["id"], "their_text": layout["their_text"], "our_text": layout["our_text"]}))
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"short": item["id"], "error": str(exc)[:300]}))


if __name__ == "__main__":
    main()
