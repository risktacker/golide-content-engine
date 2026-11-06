"""The script writer, rebuilt (owner direction 2026-11-06).

"Break every script rule you set there... model what we have seen that is working." The old
writer had to think in screen lines (4 to 14 words, each with its own picture fields) and filled
a fixed recipe (claim, proof, pattern, cost, line to remember...), so it wrote lists. Now:

1. The writer only writes the story: one continuous narration, the way the videos that work tell
   theirs (the model scripts of the day plus the method example), in the owner's voice guide,
   from our own research.
2. Code cuts it into screen lines (split_spoken), the same way the owner's recording is cut.
3. A small storyboard call picks each line's gold word and pictures without touching the words.
"""

from __future__ import annotations

import re
from pathlib import Path

from .content_rules import (VISUAL_CUES, chapter_range, length_target, owner_voice, spoken_blocks,
                            split_spoken, voice_pairs)

EXAMPLE_FILE = Path(__file__).resolve().parents[3] / "config" / "story-example.txt"
GUIDE_FILE = Path(__file__).resolve().parents[3] / "config" / "script-voice.md"

STORY_SCHEMA: dict = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "chapters": {"type": "array", "maxItems": 10, "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"number": {"type": "string"}, "title": {"type": "string"}},
            "required": ["number", "title"]}},
        "script": {"type": "string"},
    },
    "required": ["title", "chapters", "script"],
}

BOARD_SCHEMA: dict = {
    "type": "object", "additionalProperties": False,
    "properties": {"lines": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": {
            "emphasis": {"type": "string"},
            "subjects": {"type": "array", "maxItems": 3, "items": {"type": "string"}},
            "visual": {"type": "string", "enum": list(VISUAL_CUES)},
            "label": {"type": "string"},
            "follow": {"type": "boolean"},
        },
        "required": ["emphasis", "subjects", "visual", "label", "follow"]}}},
    "required": ["lines"],
}


def _read(path: Path) -> str:
    try:
        return "\n".join(row for row in path.read_text(encoding="utf-8").splitlines() if not row.startswith("#")).strip()
    except OSError:
        return ""


def story_instructions(format_name: str, model_seconds: float | None = None) -> str:
    target = length_target(format_name, model_seconds)
    kind = "a YouTube Short (also posted as a Reel)" if format_name == "short" else "a long YouTube video"
    if format_name == "long":
        low, high = chapter_range(format_name, model_seconds)
        chapters = (
            f"- Long video: \"chapters\" lists Intro first (number \"\"), then {low} to {high} numbered chapters "
            "(\"01\", \"02\"...; 2 to 4 plain words about this story), then Close (number \"\"). In \"script\", put "
            "[[0]] where the Intro starts, [[1]] where chapter 01 starts, and so on, one marker per chapter in order. "
            "The talk flows straight across the markers; chapter titles are never read aloud.\n")
    else:
        chapters = "- Short: \"chapters\" is an empty list and \"script\" has no markers.\n"
    example = _read(EXAMPLE_FILE)
    guide = _read(GUIDE_FILE)
    return (
        f"You write the narration for {kind} about a trending technology, AI or science story. "
        "It is read aloud, and animated pictures follow the words.\n\n"
        "WRITE IT THE WAY THE VIDEOS THAT WORK DO. Study the MODEL SCRIPTS you are given (videos working on "
        "YouTube now) and the METHOD EXAMPLE below, and do what they do, with our research and our own words:\n"
        "- Tell it as a story, in the order things happened: real moments, times, amounts, names, places, "
        "and who said what (name the source).\n"
        "- Open on the most striking real moment, then tell the viewer what they are about to find out.\n"
        "- Every sentence moves the story on. Explain a technical step at the moment it happens, with one "
        "simple everyday picture when it is needed, and come back to that picture later.\n"
        "- Ask the question the viewer is asking at that point and answer it, or say honestly that nobody "
        "knows yet and why.\n"
        "- Use the turns and twists the facts give you.\n"
        "- End by tying back to the opening moment, then one sentence asking the viewer to follow the channel, "
        "with a real reason to come back.\n"
        "- When the story is a product rather than an event, tell the story of it the same way: what happened, "
        "who made it, and a real moment of someone using it.\n"
        "Facts only from VERIFIED RESEARCH. A company's own figure is said as their claim. Never reuse a sentence "
        "from a model script or the method example: we copy how they tell it, not what they say.\n\n"
        + (f"SCRIPT VOICE GUIDE (the owner's)\n{guide}\n\n" if guide else "")
        + "HOW THE OWNER TALKS\n" + voice_pairs() + owner_voice() + "\n"
        + (f"METHOD EXAMPLE (a script that works; how it tells the story, not its words)\n{example}\n\n" if example else "")
        + "TECHNICAL (the pipeline needs these)\n"
        f"- About {target['words_min']} to {target['words_max']} spoken words (about {target['seconds']} seconds).\n"
        + chapters
        + "- Numbers as digits (6.3 billion, 93 cents, 4:20, 2026, 18,270); fractions and everyday ordinals stay "
        "words, and \"one\" on its own stays a word.\n"
        "- Never say the brand name aloud; say \"follow the channel\" or \"follow us\".\n"
        "- \"title\": the working title of the video.\n"
        "Return JSON."
    )


def plan_from_story(story: dict, format_name: str) -> dict:
    """The story cut into screen lines, chapter by chapter, words untouched."""
    chapters = list(story.get("chapters") or []) if format_name == "long" else []
    text = str(story.get("script") or "")
    if chapters:
        blocks = spoken_blocks(text)
        if blocks and blocks[0]["chapter"] == -1:
            blocks[0]["chapter"] = 0
    else:
        blocks = [{"chapter": 0, "text": " ".join(re.sub(r"\[\[\d+\]\]", " ", text).split())}]
    last = max(0, len(chapters) - 1)
    lines: list[dict] = []
    for block in blocks:
        index = min(max(0, int(block["chapter"])), last)
        for piece in split_spoken(block["text"]):
            lines.append({"chapter": index, "section": "proof", "text": piece, "emphasis": "",
                          "visual": "icon_hero", "subjects": [], "label": "",
                          "follow": "follow" in piece.lower()})
    return {"title": str(story.get("title") or ""), "chapters": chapters, "lines": lines}


def board_instructions() -> str:
    return (
        "You storyboard a narration that is already written: for each numbered screen line, in order, pick\n"
        "- \"emphasis\": the 1 or 2 words, copied exactly from that line, that light up gold in the captions: "
        "the name, number or key idea the viewer must remember (never a filler word);\n"
        "- \"subjects\": 1 to 3 concrete things the picture should show (\"exchange building\", \"bitcoin coin\", "
        "\"laptop\", \"vault\"), never abstract words;\n"
        f"- \"visual\": one of {', '.join(VISUAL_CUES)} (charts only when the line states numbers; logo_end only "
        "on the very last line);\n"
        "- \"label\": a 1 to 3 word on-screen label, or \"\";\n"
        "- \"follow\": true only on a line that asks the viewer to follow.\n"
        "Never change the words. Return exactly one item per line, in order, as JSON {\"lines\": [...]}."
    )


def board_input(plan: dict) -> str:
    return "\n".join(f"{i + 1}. {line['text']}" for i, line in enumerate(plan["lines"]))


def apply_board(plan: dict, board: dict) -> dict:
    """The storyboard's picks on the lines (a missing or invalid pick keeps the default)."""
    picks = (board or {}).get("lines") or []
    for line, pick in zip(plan["lines"], picks):
        emphasis = str(pick.get("emphasis") or "").strip()
        if emphasis and emphasis.lower() in line["text"].lower():
            line["emphasis"] = emphasis
        line["subjects"] = [str(s) for s in (pick.get("subjects") or [])][:3]
        if pick.get("visual") in VISUAL_CUES:
            line["visual"] = pick["visual"]
        line["label"] = str(pick.get("label") or "")[:40]
        line["follow"] = bool(pick.get("follow")) or line["follow"]
        if line["follow"]:
            line["section"] = "cta"
    for line in plan["lines"]:
        if not line["emphasis"]:
            words = [w.strip(",.?!:;\"'") for w in line["text"].split()]
            numbers = [w for w in words if any(ch.isdigit() for ch in w)]
            line["emphasis"] = numbers[0] if numbers else max(words, key=len, default="")
    return plan
