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
EXAMPLE_FILE_2 = Path(__file__).resolve().parents[3] / "config" / "story-example-2.txt"
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


OFFER_FILE = Path(__file__).resolve().parents[3] / "config" / "script-offer.json"


def script_offer(format_name: str) -> str:
    """What the viewer is given at the end (owner 2026-11-10: people click where they get something).
    Empty until the owner sets it in config/script-offer.json."""
    import json

    try:
        return str(json.loads(OFFER_FILE.read_text(encoding="utf-8")).get(format_name, "")).strip()
    except (OSError, ValueError):
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
    # the method examples are long-video stories; a Short follows its own shape (2026-11-10)
    example = _read(EXAMPLE_FILE) if format_name == "long" else ""
    example_2 = _read(EXAMPLE_FILE_2) if format_name == "long" else ""
    # 2026-11-12 (owner: why does it exceed the length?): the examples are 2,089 and 3,523 words and the length
    # was one line at the bottom, so the writer copied the examples' size. The length now leads, each part gets
    # its own budget, and every example says how long it is.
    lo, hi = target["words_min"], target["words_max"]
    if format_name == "long":
        intro, close = round(hi * .12 / 10) * 10, round(hi * .08 / 10) * 10
        body = round(((lo + hi) / 2 - intro - close) / 10) * 10
        budget = (f"Budget: Intro about {intro} words; the numbered chapters together about {body} words, shared evenly "
                  f"(with 4 chapters about {body // 4} each, with 6 about {body // 6} each); Close about {close} words.")
    else:
        budget = ""
    length = (f"LENGTH (the first rule): this script is {lo} to {hi} spoken words, about {target['seconds']} seconds "
              f"read aloud. Not more, not less. {budget} The model scripts and method examples below are longer: copy "
              "how they tell it, never their length.\n\n")

    def sized(text: str) -> str:
        n = len(text.split())
        return f"({n} words, about {n / 150:.0f} minutes: far longer than yours, for method only)"
    guide = _read(GUIDE_FILE)
    offer = script_offer(format_name)
    if format_name == "short":
        shape = (
            "A SHORT HAS ITS OWN SHAPE (owner 2026-11-10: never a cut-down long video). Do what the shorts that work "
            "do (models: 29-million-view story shorts, the \"You're Elon Musk...\" chain, the \"too small, not too big\" "
            "answer):\n"
            "- The very first sentence is the hook, with no intro and no greeting: a contradiction (\"74 soldiers knocked "
            "down an iron bridge just by walking across it\"), or put the viewer in someone's shoes (\"You're the boss "
            "of...\"), or the question everyone has followed by the opposite of what they expect.\n"
            "- Then escalate step by step, each sentence one move further (\"So... Then... Still not enough?\").\n"
            "- Then the turn where the real reason comes out (\"Here's the thing.\" or \"You see,\"; vary it).\n"
            "- Then the payoff: the one thing the viewer now knows or can do, said plainly.\n"
            "- The last line lands a twist that ties back to the first sentence, so the Short loops.\n"
            "- Relentless delivery: short sentences, no dead air, no recap, no \"in this video\".\n"
            "- One sentence asking the viewer to follow the channel, with a real reason, just before the last line.\n")
    else:
        shape = (
            "THE ESSENCE (owner 2026-11-10): this channel is not news. Every video explains how something is made, "
            "how it happened, how to do it, the steps, or the solution. The viewer must leave with something they "
            "can use. Do what the long videos that work do:\n"
            "- Open on the most striking real moment (a date, a number, a person), then why it matters to the viewer, "
            "then say plainly what they will have by the end (\"By the end of this video you'll know exactly how... "
            "and how to...\").\n"
            "- Tell it as a story in the order things happened: real moments, times, amounts, names, places, and who "
            "said what (name the source). Explain a technical step at the moment it happens, with one simple everyday "
            "picture when it is needed, and come back to that picture later.\n"
            "- Give the viewer real things to use along the way: the steps, the tools, the setting, the number, the "
            "check to make. Say them as tips (\"Here's the tip:...\") the moment they are useful.\n"
            "- Ask the question the viewer is asking at that point and answer it; say the viewer's doubt out loud "
            "(\"you might be wondering why not just...\") and give the honest answer, including what does not work "
            "yet.\n"
            "- Keep it connected: one picture runs through the whole video. Every part ends on what is still missing, "
            "and the next part picks it up, so the viewer is pulled forward.\n"
            "- Close: add up what the viewer now has in two or three sentences, tie back to the opening moment, then "
            "one sentence asking them to follow the channel, with a real reason to come back.\n"
            "- When the story is a product rather than an event, tell the story of it the same way and end on how the "
            "viewer can use it or decide about it.\n")
    return (
        f"You write the narration for {kind} about a technology, AI or science story. "
        "It is read aloud, and animated pictures follow the words.\n\n"
        + length
        + "WRITE IT THE WAY THE VIDEOS THAT WORK DO. Study the MODEL SCRIPTS you are given (videos working on "
        "YouTube now) and do what they do, with our research and our own words.\n"
        + shape
        + (f"- What the viewer gets (say it once, near the end, in one natural sentence, separate from the follow "
           f"sentence): {offer}\n" if offer else "")
        + "Facts only from VERIFIED RESEARCH. A company's own figure is said as their claim. Never reuse a sentence "
        "from a model script or a method example: we copy how they tell it, not what they say.\n\n"
        + (f"SCRIPT VOICE GUIDE (the owner's)\n{guide}\n\n" if guide else "")
        + "HOW THE OWNER TALKS\n" + voice_pairs() + owner_voice() + "\n"
        + (f"METHOD EXAMPLE 1, a news story {sized(example)} (a script that works; how it tells the story, not its "
           f"words)\n{example}\n\n" if example else "")
        + (f"METHOD EXAMPLE 2, a tool or product {sized(example_2)} (how it stays connected from start to end, not "
           f"its words)\n{example_2}\n\n" if example_2 else "")
        + "TECHNICAL (the pipeline needs these)\n"
        f"- {lo} to {hi} spoken words (about {target['seconds']} seconds): count them before you answer.\n"
        + chapters
        + "- Numbers as digits (6.3 billion, 93 cents, 4:20, 2026, 18,270); fractions and everyday ordinals stay "
        "words, and \"one\" on its own stays a word.\n"
        "- Never say the brand name aloud; say \"follow the channel\" or \"follow us\".\n"
        "- SPOKEN DELIVERY (owner 2026-11-13): this script is PERFORMED by an expressive AI voice. A flat, article-like "
        "script is read flat; the voice can only perform what the text gives it. Write it the way a sharp YouTuber "
        "talks to one friend:\n"
        "  * questions to the viewer and to yourself (\"So what changed?\", \"Sounds great, right?\") - at least one in "
        "every chapter, usually more;\n"
        "  * real reactions where the facts earn them, with ! (\"That's a lot of money!\", \"Wait. Read that again.\"), "
        "and short reaction words (\"Okay.\", \"Look,\", \"Honestly?\", \"Yeah...\", \"Hmm.\", \"No, really.\");\n"
        "  * \"...\" where a person pauses to let something land or trails off; a dash for a quick aside;\n"
        "  * ONE word in CAPITALS where a person would hit it (about one every 3 or 4 sentences), never a number or name;\n"
        "  * short sentences next to longer ones; contractions always; never three long sentences in a row;\n"
        "  * the odd self-correction or aside when it helps (\"...in this video - no, in the next five minutes - \").\n"
        "  Every reaction must be honest: excitement only for something exciting, doubt for something doubtful. Facts "
        "never change for the sake of delivery.\n"
        "- VOICE TAGS (Eleven v3 audio tags, from ElevenLabs' v3 guide): lowercase words in square brackets, performed "
        "and never said, placed directly before the words they colour. Use the tags v3 knows: emotion [excited], "
        "[curious], [happily], [sad], [serious], [surprised], [awe], [sarcastic], [skeptical], [mischievously]; delivery "
        "[whispers], [softly], [quietly], [slowly], [rushed], [drawn out], [pause]; reactions [laughs], [chuckles], "
        "[sighs], [exhales], [gasps], [clears throat]. Combine two for a layered read ([curious][softly]). Open EVERY "
        "paragraph with a tag for how it is said, and add one where the feeling turns, about one per 2 sentences; "
        "never inside a number or name. Build each chapter toward a peak, and set up a reveal with [quietly] and a "
        "line break before it (a line break is a pause). Tags are not counted as words. No other brackets.\n"
        "- \"title\": the working title of the video.\n"
        "Return JSON."
    )


CUE = re.compile(r"\[(?!\[)[^\]\[]{1,30}\](?!\])")


def strip_cues(text: str) -> str:
    """The script without the voice cues ([excited]...), for the screen, the captions and the counts."""
    return re.sub(r"[ \t]{2,}", " ", CUE.sub("", text)).replace(" ,", ",").replace(" .", ".")


def plan_from_story(story: dict, format_name: str) -> dict:
    """The story cut into screen lines, chapter by chapter, words untouched."""
    chapters = list(story.get("chapters") or []) if format_name == "long" else []
    performed = str(story.get("script") or "")
    text = strip_cues(performed)
    if chapters:
        blocks = spoken_blocks(text)
        if blocks and blocks[0]["chapter"] == -1:
            blocks[0]["chapter"] = 0
    else:
        blocks = [{"chapter": 0, "text": " ".join(re.sub(r"\[\[\d+\]\]", " ", text).split())}]
    last = max(0, len(chapters) - 1)
    lines: list[dict] = []
    highest = 0
    for block in blocks:
        index = min(max(0, int(block["chapter"])), last)
        if chapters and index < highest:
            # a marker that goes backwards (the close marked like the intro) is the Close part
            if str(chapters[-1].get("number", "")).strip() or index == last:
                chapters.append({"number": "", "title": "Close"})
                last = len(chapters) - 1
            index = last
        highest = max(highest, index)
        for piece in split_spoken(block["text"]):
            lines.append({"chapter": index, "section": "proof", "text": piece, "emphasis": "",
                          "visual": "icon_hero", "subjects": [], "label": "",
                          "follow": "follow" in piece.lower()})
    voice = "\n\n".join(p.strip() for p in re.split(r"\[\[\d+\]\]|\n\s*\n", performed) if p.strip())
    return {"title": str(story.get("title") or ""), "chapters": chapters, "lines": lines,
            "voice_script": voice if CUE.search(performed) else ""}


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


def delivery_problems(script: str) -> list[str]:
    """2026-11-13 (owner): why a script would be read flat. The 2026-11-12 long video had, in 59 sentences, 2
    questions, no exclamation, no pause and 2 stressed words, and sounded like someone reading an article."""
    body = CUE.sub(" ", script)
    paras = [p for p in re.split(r"\n\s*\n", script) if p.strip() and not re.fullmatch(r"\s*\[\[?[^\]]*\]\]?\s*", p)]
    sentences = [x for x in re.split(r"(?<=[.!?…])\s+", body) if len(x.split()) >= 2]
    n = max(1, len(sentences))
    out = []
    if body.count("?") < max(2, n // 12):
        out.append(f"{body.count('?')} questions in {n} sentences (want at least {max(2, n // 12)})")
    if body.count("!") < max(1, n // 25):
        out.append(f"{body.count('!')} exclamations (want at least {max(1, n // 25)})")
    pauses = body.count("...") + body.count("…")
    if pauses < max(2, n // 15):
        out.append(f"{pauses} pauses with ... (want at least {max(2, n // 15)})")
    caps = len(re.findall(r"\b[A-Z]{2,}[a-z]*\b(?<![A-Z]{2}\b)|\b[A-Z]{3,}\b", body))
    if caps < max(1, n // 10):
        out.append(f"{caps} stressed CAPITAL words (want at least {max(1, n // 10)})")
    opened = sum(1 for p in paras if CUE.match(p.strip()))
    if paras and opened < len(paras) * 0.6:
        out.append(f"{opened} of {len(paras)} paragraphs open with a direction tag")
    longs = max((len(list(g)) for k, g in __import__("itertools").groupby(len(x.split()) > 22 for x in sentences) if k),
                default=0)
    if longs >= 3:
        out.append(f"{longs} long sentences in a row")
    return out
