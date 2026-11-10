"""The free guide for each video (owner 2026-11-10: "the engine generating one pdf file for the steps
or just the well structured pdf of information").

One small model call turns the finished script and its verified research into a short guide: what
the viewer will understand, the steps or key points in order, what to do next, and every source
with its link. It is set as a clean PDF in GOLIDE's colours and linked in the description.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

GUIDE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["headline", "intro", "sections", "next_steps"],
    "properties": {
        "headline": {"type": "string"},
        "intro": {"type": "string"},
        "sections": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["heading", "points"],
            "properties": {"heading": {"type": "string"},
                           "points": {"type": "array", "items": {"type": "string"}}}}},
        "next_steps": {"type": "array", "items": {"type": "string"}},
    },
}

INSTRUCTIONS = (
    "Turn this video's script and its verified research into the free guide a viewer downloads after "
    "watching. Plain, useful and short (one or two pages): a headline; a two-sentence intro saying what the "
    "reader will understand or be able to do; three to six sections in the video's order, each a heading "
    "and three to five points (steps when the video explains how to do something, the key facts when it "
    "explains how something works or happened); then three to five concrete next steps the reader can "
    "take. Facts only from the research and the script. Digits for numbers. No hype, no emojis."
)


def write_guide(text: Any, title: str, script: str, research: dict) -> dict:
    claims = "\n".join(f"- {c.get('claim', '')} ({c.get('source_title', '')})" for c in research.get("claims", [])[:30])
    out = text.generate_json(INSTRUCTIONS, f"TITLE: {title}\n\nSCRIPT:\n{script[:12000]}\n\nRESEARCH:\n"
                             f"{research.get('summary', '')}\n{claims}", GUIDE_SCHEMA, max_output_tokens=3000)
    return dict(out.value), out


def sources(research: dict) -> list[tuple[str, str]]:
    seen, out = set(), []
    for c in research.get("claims", []):
        url = str(c.get("source_url", "")).strip()
        if url.startswith("http") and url not in seen:
            seen.add(url)
            out.append((str(c.get("source_title", "") or url), url))
    return out[:20]


def render_pdf(guide: dict, title: str, refs: list[tuple[str, str]], path: Path, community: str = "") -> Path:
    from xml.sax.saxutils import escape

    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

    gold, ink, grey = HexColor("#B8892E"), HexColor("#15151A"), HexColor("#5A5A63")
    base = dict(fontName="Helvetica", textColor=ink, leading=15, fontSize=10.5)
    h_style = ParagraphStyle("h", **dict(base, fontName="Helvetica-Bold", fontSize=22, leading=27))
    k_style = ParagraphStyle("k", **dict(base, fontName="Helvetica-Bold", fontSize=9, textColor=gold, leading=12))
    s_style = ParagraphStyle("s", **dict(base, fontName="Helvetica-Bold", fontSize=13.5, leading=18, spaceBefore=10))
    p_style = ParagraphStyle("p", **base)
    small = ParagraphStyle("sm", **dict(base, fontSize=8.5, leading=11.5, textColor=grey))

    def bullets(items, numbered=False):
        return ListFlowable([ListItem(Paragraph(escape(str(i)), p_style), leftIndent=12) for i in items if str(i).strip()],
                            bulletType="1" if numbered else "bullet", start="1" if numbered else None,
                            bulletColor=gold, leftIndent=14, bulletFontSize=9)

    story = [Paragraph("GOLIDE · FREE GUIDE", k_style), Spacer(1, 4),
             Paragraph(escape(guide.get("headline") or title), h_style), Spacer(1, 6),
             Paragraph(escape(guide.get("intro", "")), p_style), Spacer(1, 8),
             HRFlowable(width="100%", thickness=1.2, color=gold), Spacer(1, 4)]
    for section in guide.get("sections", []):
        story += [Paragraph(escape(section.get("heading", "")), s_style), bullets(section.get("points", []))]
    if guide.get("next_steps"):
        story += [Paragraph("What to do next", s_style), bullets(guide["next_steps"], numbered=True)]
    if refs:
        story += [Spacer(1, 10), HRFlowable(width="100%", thickness=0.6, color=grey),
                  Paragraph("Sources used in the video", s_style)]
        story += [Paragraph(f'{escape(t)}: <link href="{escape(u)}" color="#B8892E">{escape(u)}</link>', small)
                  for t, u in refs]
    story += [Spacer(1, 12), Paragraph(escape(f"From the GOLIDE video \"{title}\"."
                                               + (f" Join the community: {community}" if community else "")), small)]
    path.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                      bottomMargin=18 * mm, title=title, author="GOLIDE").build(story)
    return path


def offer_settings(root: Path) -> dict:
    try:
        return json.loads((root / "config" / "script-offer.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
