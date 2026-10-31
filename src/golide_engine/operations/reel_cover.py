"""A reel cover for every long video (owner direction 2026-10-31).

"For every long form video I receive an email after upload with the thumbnail for the
Short or Instagram Reel: the same image you send for short videos, same format and frame,
the one to upload as the cover for that reel."

Same pipeline as the Shorts covers (tools/short_covers.py): one text call plans the real
object, the words and the colours; the image model draws the real object (with the
modelled video's thumbnail as a shape reference); the code sets it on its own 1080x1920
canvas (vector.short_cover.canvas_cover). The cover is emailed with the image attached.
About $0.02 a video: one small text call and one line-art drawing.
"""

from __future__ import annotations

import json
import re
from datetime import date
from email.message import EmailMessage
from pathlib import Path

from ..vector.illustrate import ACCENTS, illustration_prompt
from ..vector.layouts import art_size
from ..vector.short_cover import LAYOUTS, canvas_cover, drawing_cutout
from ..vector.thumbnail_v2 import fetch_reference
from .email import _send

COVER_FIELDS = {
    "id": {"type": "string"}, "object": {"type": "string"}, "drawing": {"type": "string"},
    "gold": {"type": "string"}, "people": {"type": "boolean"}, "words": {"type": "string"},
    "sub": {"type": "string"}, "accent": {"type": "string", "enum": list(ACCENTS)},
    "bg_top": {"type": "string"}, "bg_bottom": {"type": "string"},
    "layout": {"type": "string", "enum": list(LAYOUTS)},
}

COVER_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": list(COVER_FIELDS),
    "properties": COVER_FIELDS,
}

COVER_RULES = """\
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
  gradient: rich and fairly dark (never black, never washed out), chosen for this topic."""

REEL_RULES = """You design the Instagram Reel cover (also the YouTube Short cover) for one GOLIDE
long video, a tech and science explainer. The cover is the real object of the story, drawn
large on a coloured canvas, with a few words. It must look like it was designed for this one
video: its own colours and words, not a template.
""" + COVER_RULES + """
- "layout": use LAYOUT exactly as given. "id": the PRODUCTION_ID given.
Return JSON with these fields only."""


def layout_for(production_id: str) -> str:
    """Rotate the layout by date so consecutive long videos never share one."""
    found = re.search(r"\d{4}-\d{2}-\d{2}", production_id)
    if not found:
        return LAYOUTS[sum(map(ord, production_id)) % len(LAYOUTS)]
    day = date.fromisoformat(found.group(0))
    # Count long videos (Tue, Thu, Sat): three a week, one step each.
    n = (day.toordinal() // 7) * 3 + {1: 0, 3: 1, 5: 2}.get(day.weekday(), day.weekday())
    return LAYOUTS[n % len(LAYOUTS)]


def draw_cover(cover: dict, work: Path, line_art, reference: Path | None = None):
    """Draw the planned object and set it on its canvas. Returns a PIL image, 1080x1920."""
    art = work / "art.png"
    prompt = illustration_prompt(cover["drawing"] + f" It is unmistakably {cover['object']}.", cover["gold"], "short")
    line_art.create(prompt, art, art_size("short", "single"), reference=reference)
    cut, mask = drawing_cutout(art, cover["accent"], people=bool(cover["people"]))
    return canvas_cover(cut, mask, cover["words"], cover["sub"], ACCENTS[cover["accent"]],
                        cover["bg_top"], cover["bg_bottom"], cover["layout"])


def build_reel_cover_email(*, title: str, youtube_video_id: str, image_path: Path, words: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"GOLIDE: reel cover for \"{title}\""
    msg.set_content("\n".join([
        f"The reel cover for today's long video: {title}",
        f"https://youtu.be/{youtube_video_id}" if youtube_video_id else "",
        "",
        f"Cover words: {words}",
        "Size: 1080 x 1920 (9:16), the same frame as the Shorts covers.",
        "",
        "Instagram: when you post the reel, tap Edit cover, then Add from camera roll, and pick this image.",
        "YouTube Short: in the YouTube app, open the Short, tap Edit, then Thumbnail.",
    ]))
    msg.add_attachment(image_path.read_bytes(), maintype="image", subtype="jpeg", filename=image_path.name)
    return msg


def make_reel_cover(*, production_id: str, title: str, story: str, youtube_video_id: str,
                    source_url: str, providers, out_dir: Path, send: bool = True) -> dict:
    """Plan, draw and email one reel cover. Best effort: the caller catches failures."""
    from ..providers.openai_media import OpenAILineArtProvider

    layout = layout_for(production_id)
    text = providers.text(live=True)
    body = json.dumps({"PRODUCTION_ID": production_id, "LAYOUT": layout, "title": title, "story": story[:900]},
                      ensure_ascii=False)
    cover = dict(text.generate_json(REEL_RULES, body, COVER_SCHEMA, max_output_tokens=4000).value)
    cover["layout"] = layout
    if cover.get("accent") not in ACCENTS:
        cover["accent"] = "gold"
    line_art = OpenAILineArtProvider(providers.config["assets"]["support_model"],
                                     providers.config["assets"]["support_quality"])
    work = out_dir / production_id
    work.mkdir(parents=True, exist_ok=True)
    reference = fetch_reference(source_url, work / "reference.jpg") if source_url else None
    image = draw_cover(cover, work, line_art, reference)
    path = out_dir / f"{production_id}-reel-cover.jpg"
    image.convert("RGB").save(path, quality=92)
    sent = _send(build_reel_cover_email(title=title, youtube_video_id=youtube_video_id,
                                        image_path=path, words=cover["words"])) if send else False
    return {"status": "sent" if sent else "made", "path": str(path), "object": cover["object"],
            "words": cover["words"], "layout": layout}
