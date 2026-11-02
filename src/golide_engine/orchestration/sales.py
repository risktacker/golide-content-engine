"""Sales videos made from Studio (owner direction 2026-11-03).

"A placeholder for sales videos, not the one scheduled by the engine... where I can paste the
script that I've used for the audio, then you run it and you produce the video for me. And the
video goes into all those platforms."

A sales video is a Short the owner starts by hand in Studio: his script (exactly as he recorded
it), his recording, a title, the buy link and a picture of the product (a book cover). The
engine skips topic discovery, research and script writing, and builds everything else exactly
as for any video: storyboard, illustrations, render, thumbnail, upload, Reels and posts. The
product itself is never redrawn by an image model: its reveal scenes use the real picture.
"""

from __future__ import annotations

import json
import re
import shutil
import urllib.request
from pathlib import Path
from typing import Any

PURPOSE = "sales-video"
MAX_LINE_WORDS = 14


def is_sale(spec: dict[str, Any]) -> bool:
    return spec.get("purpose") == PURPOSE


def sale_info(spec: dict[str, Any]) -> dict[str, Any]:
    return dict(spec.get("sale") or {})


# ---------------------------------------------------------------------------
# The owner's script, as he recorded it, split into screen lines (no word changes)
# ---------------------------------------------------------------------------

def _chunks(sentence: str) -> list[str]:
    """Split one sentence into breath-sized lines of at most MAX_LINE_WORDS words,
    preferring the commas, never changing a word."""
    words = sentence.split()
    if len(words) <= MAX_LINE_WORDS:
        return [sentence]
    pieces = [p.strip() for p in re.split(r"(?<=[,;:])\s+", sentence) if p.strip()]
    lines: list[str] = []
    current: list[str] = []
    for piece in pieces:
        piece_words = piece.split()
        if current and len(current) + len(piece_words) > MAX_LINE_WORDS:
            lines.append(" ".join(current))
            current = []
        current.extend(piece_words)
        while len(current) > MAX_LINE_WORDS:
            # A long stretch with no comma: split it evenly.
            parts = -(-len(current) // MAX_LINE_WORDS)
            size = -(-len(current) // parts)
            lines.append(" ".join(current[:size]))
            current = current[size:]
    if current:
        lines.append(" ".join(current))
    return lines


def owner_script_plan(script: str, title: str) -> dict[str, Any]:
    """The scene plan the rest of the engine expects, built from the owner's own words."""
    text = " ".join(str(script or "").split())
    if len(text.split()) < 8:
        raise ValueError("the sales script is too short (fewer than 8 words)")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    texts = [line for sentence in sentences for line in _chunks(sentence)]
    lines = []
    for index, line in enumerate(texts):
        section = "claim" if index == 0 else "cta" if index == len(texts) - 1 else "proof"
        lines.append({
            "chapter": 0, "section": section, "text": line, "emphasis": "",
            "visual": "icon_hero", "subjects": [], "label": "", "follow": False,
        })
    return {"title": title, "chapters": [], "lines": lines}


def sale_research(spec: dict[str, Any]) -> dict[str, Any]:
    """What the video may claim: only what the owner wrote about his own product."""
    info = sale_info(spec)
    link = str(info.get("link", ""))
    name = str(info.get("product_name") or spec.get("title", ""))
    return {
        "summary": f"Sales video for {name}, the owner's own product, in the owner's own words.",
        "claims": [{
            "claim": f"{name} is available at {link}" if link else name,
            "source_title": name, "source_url": link, "published_or_updated": "",
        }],
    }


def storyboard_note(spec: dict[str, Any]) -> str:
    info = sale_info(spec)
    name = str(info.get("product_name") or spec.get("title", ""))
    return (
        f"\nSALES VIDEO: this Short sells the owner's own product, {name}. The product is shown as "
        "itself in its reveal scenes (set \"product\": true there; its real picture is used, never "
        "drawn). Every other scene illustrates what the line says: the reader's problem, the result "
        "they get, the moment of buying, the steps the product walks them through.\n"
    )


# ---------------------------------------------------------------------------
# Media from Studio (R2 refs, https or a local path)
# ---------------------------------------------------------------------------

def fetch_media(ref: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if ref.startswith("r2://"):
        from ..storage.r2 import r2_store_from_environment
        store = r2_store_from_environment()
        if store is None:
            raise RuntimeError("R2 is required to fetch Studio media")
        with urllib.request.urlopen(store.resolve(ref, expires_seconds=3600), timeout=90) as response:
            dest.write_bytes(response.read())
    elif ref.startswith("https://"):
        with urllib.request.urlopen(ref, timeout=90) as response:
            dest.write_bytes(response.read())
    else:
        local = Path(ref).expanduser()
        if not local.is_file():
            raise RuntimeError(f"media not found: {ref}")
        shutil.copyfile(local, dest)
    return dest


def cover_plate(source: Path, target: Path) -> Path:
    """The real product picture as a plate (the engine's full-colour product picture: the
    pen traces its outline, then the picture fills in)."""
    from PIL import Image

    image = Image.open(source).convert("RGBA")
    image.thumbnail((1024, 1024))
    pad = max(8, image.width // 40)
    plate = Image.new("RGBA", (image.width + pad * 2, image.height + pad * 2), (0, 0, 0, 0))
    plate.paste(image, (pad, pad), image)
    target.parent.mkdir(parents=True, exist_ok=True)
    plate.save(target)
    target.with_suffix(".plate.json").write_text(json.dumps({"kind": "product", "source": "owner"}) + "\n",
                                                 encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# The buy link everywhere the video goes
# ---------------------------------------------------------------------------

def with_link(text: str, link: str, lead: str = "Get it here") -> str:
    """The buy link at the top of a description or caption (once)."""
    text = str(text or "").strip()
    link = str(link or "").strip()
    if not link or link in text:
        return text
    return f"{lead}: {link}\n\n{text}" if text else f"{lead}: {link}"
