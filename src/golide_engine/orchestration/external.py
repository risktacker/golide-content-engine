"""External videos (owner direction 2026-11-03).

"An option just for external video creation: upload my own audio, with a placeholder for the
script that was used so it can be cross-checked. It creates the video from that instead of the
engine's own script. Any day, any time, nothing to do with the schedule."

The engine skips topic discovery, research and script writing, and builds the video from the
owner's script and recording exactly as for any other video. An optional link goes into the
YouTube description and the Facebook and LinkedIn captions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PURPOSE = "external-video"
MAX_LINE_WORDS = 14


def is_external(spec: dict[str, Any]) -> bool:
    return spec.get("purpose") == PURPOSE


def external_info(spec: dict[str, Any]) -> dict[str, Any]:
    return dict(spec.get("external") or {})


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
        raise ValueError("the script is too short (fewer than 8 words)")
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


def external_research(spec: dict[str, Any]) -> dict[str, Any]:
    """Nothing to research: the facts are the owner's own words."""
    link = str(external_info(spec).get("link", ""))
    return {"summary": "Video built from the owner's own script and recording.",
            "claims": [{"claim": "The owner's own script.", "source_title": "Owner",
                        "source_url": link, "published_or_updated": ""}]}


# ---------------------------------------------------------------------------
# The optional link
# ---------------------------------------------------------------------------

def with_link(text: str, link: str, lead: str = "Link") -> str:
    """The link at the top of a description or caption (once)."""
    text = str(text or "").strip()
    link = str(link or "").strip()
    if not link or link in text:
        return text
    return f"{lead}: {link}\n\n{text}" if text else f"{lead}: {link}"


# ---------------------------------------------------------------------------
# The owner's optional reference: a picture of the real thing, or a link to it
# ---------------------------------------------------------------------------

def reference_note(spec: dict[str, Any]) -> str:
    """For the storyboard: the owner says what the real thing is (look it up, draw it as it is)."""
    url = str(external_info(spec).get("reference_link", "")).strip()
    if not url:
        return ""
    return (f"\nREFERENCE FROM THE OWNER: {url}\nThis is the real thing the video is about. Use web search "
            "to see exactly what it is and what it looks like, and draw it as it really is.\n")


def fetch_media(ref: str, dest: Path) -> Path:
    import shutil
    import urllib.request

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
        shutil.copyfile(Path(ref).expanduser(), dest)
    return dest


def reference_plate(source: Path, target: Path) -> Path:
    """The owner's real picture as the product picture (the pen traces its outline, then it fills in)."""
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
