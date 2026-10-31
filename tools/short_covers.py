"""Thumbnails for every Short published so far (owner direction 2026-10-31).

"Count all the shorts we have and design independent, different in everything, using the
real structure of the topic object: if Tesla, it's Tesla. Then send an email, I will add
them manually myself." For each Short: one text call plans the real object and the words
for all of them at once (so no two share colours, layout or words); the image model draws
the real object (with the modelled video's thumbnail as a shape reference when there is
one); the code colours it and sets it on its own canvas (vector.short_cover). All covers
go out in one email.
"""

from __future__ import annotations

import json
import sys
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golide_engine.operations.email import _send  # noqa: E402
from golide_engine.providers.openai_media import OpenAILineArtProvider  # noqa: E402
from golide_engine.providers.registry import ProviderRegistry  # noqa: E402
from golide_engine.vector.illustrate import ACCENTS, illustration_prompt  # noqa: E402
from golide_engine.vector.layouts import art_size  # noqa: E402
from golide_engine.vector.short_cover import LAYOUTS, canvas_cover, drawing_cutout  # noqa: E402
from golide_engine.vector.thumbnail_v2 import fetch_reference  # noqa: E402

OUT = ROOT / "short-covers"

PLAN_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["covers"],
    "properties": {"covers": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["id", "object", "drawing", "gold", "people", "words", "sub", "accent", "bg_top", "bg_bottom", "layout"],
        "properties": {
            "id": {"type": "string"}, "object": {"type": "string"}, "drawing": {"type": "string"}, "gold": {"type": "string"},
            "people": {"type": "boolean"}, "words": {"type": "string"}, "sub": {"type": "string"},
            "accent": {"type": "string", "enum": list(ACCENTS)},
            "bg_top": {"type": "string"}, "bg_bottom": {"type": "string"},
            "layout": {"type": "string", "enum": list(LAYOUTS)},
        }}}},
}

PLAN_RULES = """You design YouTube Shorts covers for GOLIDE, a tech and science explainer channel.
For EACH short below, plan one cover. The cover is the real object of the story, drawn large
on a coloured canvas, with a few words.
- "object": the REAL thing, named exactly (the new 2-door Tesla Roadster sports car, the
  iPhone Duo foldable phone, a liquid-cooled server rack, Meta Ray-Ban smart glasses...).
  If the story names a real product, company device or place, it is that one, never a generic
  stand-in. If the story is about something you cannot hold (an AI agent, a policy), pick the
  real physical thing people would picture (the phone running it, the device, the building).
- "drawing": one sentence for the illustrator: the object, its real distinctive parts, its
  angle, and at most one simple prop that tells the story. One clear subject, nothing else.
- "gold": the ONE part of the object that tells the story (the cracked hinge, the jets),
  drawn in the accent colour.
- "people": true only if a person must be in the picture (they are drawn in neutral tones).
- "words": 2 to 4 words that make someone tap (not the title repeated). "sub": 2 to 4 smaller
  words naming the product or company.
- "accent": the colour of the words. "bg_top" and "bg_bottom": two hex colours for the canvas
  gradient: rich and fairly dark (never black, never washed out), chosen for this topic.
- EVERY COVER DIFFERENT IN EVERYTHING: no two covers share a colour pair, consecutive covers
  never share a layout or accent, and no word is reused across covers.
Return JSON {"covers": [...]} with one entry per short, using its id."""


def shorts() -> list[dict]:
    items = []
    for path in sorted((ROOT / "data" / "production-records").glob("golide-short-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        pid = path.stem
        spec_path = ROOT / "production-queue" / f"{pid}.completed.json"
        spec = json.loads(spec_path.read_text(encoding="utf-8")) if spec_path.exists() else {}
        items.append({
            "id": pid, "youtube": record.get("youtube_video_id", ""),
            "title": (record.get("production") or {}).get("title") or spec.get("title", ""),
            "story": (spec.get("brief") or str(record.get("narration", ""))[:600])[:700],
            "source": (spec.get("source_breakout") or {}).get("url", ""),
        })
    return items


def main() -> None:
    items = shorts()
    providers = ProviderRegistry(ROOT / "config" / "providers.json")
    text = providers.text(live=True)
    plan = text.generate_json(PLAN_RULES, json.dumps([{k: i[k] for k in ("id", "title", "story")} for i in items]),
                              PLAN_SCHEMA, max_output_tokens=16000).value["covers"]
    by_id = {c["id"]: c for c in plan}
    line_art = OpenAILineArtProvider(providers.config["assets"]["support_model"],
                                     providers.config["assets"]["support_quality"])
    OUT.mkdir(exist_ok=True)
    made = []
    for n, item in enumerate(items):
        cover = by_id.get(item["id"])
        if not cover:
            continue
        work = OUT / item["id"]
        ref = fetch_reference(item["source"], work / "reference.jpg") if item["source"] else None
        art = work / "art.png"
        prompt = illustration_prompt(cover["drawing"] + f" It is unmistakably {cover['object']}.", cover["gold"], "short")
        try:
            line_art.create(prompt, art, art_size("short", "single"), reference=ref)
            cut, mask = drawing_cutout(art, cover["accent"], people=bool(cover["people"]))
            image = canvas_cover(cut, mask, cover["words"], cover["sub"], ACCENTS[cover["accent"]],
                                 cover["bg_top"], cover["bg_bottom"], cover["layout"])
        except Exception as exc:  # noqa: BLE001 - one failed cover never stops the rest
            print(json.dumps({"cover": item["id"], "error": str(exc)[:300]}))
            continue
        path = OUT / f"{n + 1:02d}-{item['id']}.jpg"
        image.save(path, quality=90)
        made.append((path, item, cover))
        print(json.dumps({"cover": item["id"], "object": cover["object"], "words": cover["words"]}))

    msg = EmailMessage()
    msg["Subject"] = f"GOLIDE: {len(made)} Shorts covers ready to set"
    lines = ["Your Shorts covers, one per Short. Set each one in the YouTube app or YouTube Studio when it suits you.",
             "In the app: open the Short, tap Edit, then Thumbnail. In Studio on a computer: Content, Shorts, the pencil, Thumbnail.", ""]
    for path, item, cover in made:
        lines.append(f"{path.name}: {item['title']} (https://youtube.com/shorts/{item['youtube']})")
    msg.set_content("\n".join(lines))
    for path, _, _ in made:
        msg.add_attachment(path.read_bytes(), maintype="image", subtype="jpeg", filename=path.name)
    _send(msg)


if __name__ == "__main__":
    main()
