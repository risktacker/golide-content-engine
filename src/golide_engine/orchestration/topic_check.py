"""2026-11-12 (owner): the video, its title and its research are about ONE topic, checked at every step.

What went wrong on golide-long-2026-11-12-r: the topic was this week's Claude Fable 5.2 launch, but research was
only given the brief ("the viral model launch..."), which names no model, no source and no date. Research found an
older launch (Opus 4.6, February), the script was built on it, the voice read it, and the title, fixed at topic
choice, still said Fable/IPO. Nothing compared them. Now:

1. research gets the topic itself (title, the topic's source page, what happened, today's date) and must verify the
   core fact from that source first; if it cannot, the run stops BEFORE the script and the voice (no money spent);
2. the script writer gets the same topic packet, so the story is about what broke this week;
3. the title is checked against the FINAL script before upload: every name, product, number and claim in it must be
   said in the script, otherwise it is rewritten from the script in the modelled title's form.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

CORE_FACT_SCHEMA = {
    "type": "object",
    "properties": {
        "fact": {"type": "string"},
        "source_url": {"type": "string"},
        "published_or_updated": {"type": "string"},
        "verified": {"type": "boolean"},
    },
    "required": ["fact", "source_url", "published_or_updated", "verified"],
    "additionalProperties": False,
}

TITLE_CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "unsupported": {"type": "array", "items": {"type": "string"}},
        "title": {"type": "string"},
    },
    "required": ["unsupported", "title"],
    "additionalProperties": False,
}


def chosen_topic(spec: dict[str, Any]) -> dict[str, Any]:
    """The topic candidate this video was made from (empty when the job was written by hand)."""
    source = spec.get("selected_topic_source")
    title = spec.get("model_title") or spec.get("title")
    for c in spec.get("topic_candidates") or []:
        if (source and c.get("authoritative_source_url") == source) or c.get("model_title") == title:
            return c
    return {}


def topic_packet(spec: dict[str, Any], today: dt.date | None = None) -> str:
    """Everything that says what this video is about, for research and for the script writer."""
    c = chosen_topic(spec)
    rows = [
        ("TODAY", (today or dt.date.today()).isoformat()),
        ("TITLE", spec.get("model_title") or spec.get("title") or ""),
        ("TOPIC SOURCE", spec.get("selected_topic_source") or c.get("authoritative_source_url") or ""),
        ("WHAT HAPPENED", c.get("evidence_summary") or ""),
        ("WHY PEOPLE ARE WATCHING", c.get("broke_on") or ""),
    ]
    return "THE TOPIC (this video is about THIS, happening now)\n" + "\n".join(f"{k}: {v}" for k, v in rows if v) + "\n\n"


RESEARCH_RULE = (
    " The video is about THE TOPIC given above, which is happening now. Start from its TOPIC SOURCE and put the "
    "topic's core fact (what happened, to what, when) in core_fact, with that source and its date; verified is true "
    "only when you read it in a source. Then research the claims the story needs. Prefer sources from the last 30 "
    "days; older material only as background, and every claim keeps its date. Never swap the topic for an older or "
    "different event, product or model version.")


def core_problem(research: dict[str, Any]) -> str:
    """Why the research cannot carry this topic ('' when it can)."""
    core = research.get("core_fact")
    if not isinstance(core, dict):
        return ""          # research written before this check (or by hand): nothing to judge
    if not core.get("verified") or not str(core.get("source_url") or "").startswith("http"):
        return f"the topic's core fact could not be verified ({str(core.get('fact') or 'nothing found')[:160]})"
    return ""


TITLE_RULE = (
    "You check a YouTube title against the FINAL script of the video (what the viewer will actually hear). List in "
    "unsupported every name, product, model version, company, number, date or claim in the title that the script "
    "does not say. If the list is empty, return the title exactly as given. If not, write a new title (max 90 "
    "characters) in the same form, hook and length as the MODELLED TITLE, using only what the script says, and "
    "return it. No clickbait the script cannot pay off; no hashtags.")


def title_input(title: str, modelled: str, script: str) -> str:
    return f"TITLE\n{title}\n\nMODELLED TITLE\n{modelled}\n\nFINAL SCRIPT\n{script}"


def checked_title(result: dict[str, Any], title: str) -> tuple[str, list[str]]:
    """The title to upload and what was wrong with the old one."""
    wrong = [str(x) for x in result.get("unsupported") or [] if str(x).strip()]
    new = " ".join(str(result.get("title") or "").split())[:100]
    if not wrong or not new:
        return title, []
    return new, wrong
