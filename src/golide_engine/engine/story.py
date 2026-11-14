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
# 2026-11-14 (owner): the fixed method examples are the writer's real model ("3 is the key"); Shorts had none
EXAMPLE_FILE_SHORT = Path(__file__).resolve().parents[3] / "config" / "story-example-short.txt"
EXAMPLE_FILE_3 = Path(__file__).resolve().parents[3] / "config" / "story-example-3.txt"
SHORT_EXAMPLES = [Path(__file__).resolve().parents[3] / "config" / f"story-example-short{n}.txt" for n in ("", "-2", "-3")]
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
    example_3 = _read(EXAMPLE_FILE_3) if format_name == "long" else ""
    shorts = [x for x in (_read(f) for f in SHORT_EXAMPLES) if x] if format_name == "short" else []
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
            "A SHORT HAS ITS OWN SHAPE (owner 2026-11-10 and 2026-11-13: never a cut-down long video, and never a pile "
            "of loose sentences). A Short wins or loses in the first 2 seconds and keeps people only if every sentence "
            "pulls them into the next. Model the Shorts that work (the \"You're Elon Musk...\" chain, and the "
            "\"Imagine you're Mark Zuckerberg, but you're losing the AI race\" Short: 666K views in 3 days) exactly "
            "in METHOD:\n"
            "- ONE DIRECTION. Before writing, decide the one question the Short answers and the one person or thing it "
            "follows (the company, the founder, the viewer holding the device). Every sentence moves that one story "
            "forward; nothing is a side fact.\n"
            "- THE HOOK is sentence 1: put the viewer in someone's shoes with a problem (\"Imagine you're X, but...\", "
            "\"You're the boss of X and...\") or a contradiction they can see. Sentence 2 gives the hidden strength or "
            "the stakes, with one hard number (\"Every night, 280 million screens are waiting on you.\").\n"
            "- THE CHAIN: then the story moves in steps where each step CAUSES the next. A need, the move that answers it, "
            "the new need that move creates: \"So you...\", \"First...\", \"Then...\", \"Now you need...\", \"But one "
            "is not enough, so...\", \"Still not enough?\". Every step has a real name, amount or place from the "
            "research. Even a how-to is told as this chain (\"You plug it in. Nothing. So you check...\"), never as a "
            "list of tips.\n"
            "- THE TURN: one line that flips what the viewer thought (\"And the insane part?\", \"Here's the thing.\"; "
            "vary it), then the strongest fact.\n"
            "- THE PAYOFF: the last 2 sentences say what it all adds up to, in one plain verdict that ties back to the "
            "first sentence, ending on a short punch line (\"That's the whole trick. And now you're ahead.\").\n"
            "- Each sentence starts from the one before (a connective, or the same subject carried on). No sentence "
            "could be moved elsewhere without breaking the story. Never say the same thing twice.\n"
            "- Relentless: no intro, no recap, no \"in this video\", no dead air, NO \"...\" anywhere (the voice stops "
            "dead on it).\n"
            "- The follow ask (and what the viewer gets, if given below) is ONE short sentence just before the punch "
            "line, never in the middle.\n")
    else:
        shape = (
            "THE ESSENCE (owner 2026-11-10): this channel is not news. Every video explains how something is made, "
            "how it happened, how to do it, the steps, or the solution. The viewer must leave with something they "
            "can use. Do what the long videos that work do:\n"
            "- THE HOOK (owner 2026-11-13): the first 2 sentences decide if anyone stays. Open on the payoff or the "
            "most surprising consequence for the VIEWER, as a contradiction or a question they now need answered "
            "(\"Your AI can now finish a job you'd give a junior engineer... so why are investors nervous?\"), using a "
            "concrete thing the screen can show. Never open with a date, a company announcement, \"In this video\", "
            "\"Today\" or a greeting; the date and the source come in sentence 3 or later. Then why it matters to the "
            "viewer, then say plainly what they will have by the end (\"By the end of this video you'll know exactly "
            "how... and how to...\").\n"
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
        + ((f"- What the viewer gets, said in the same one sentence as the follow ask: {offer}\n"
            if format_name == "short" else
            f"- What the viewer gets (say it once, near the end, in one natural sentence, separate from the follow "
            f"sentence): {offer}\n") if offer else "")
        + "Facts only from VERIFIED RESEARCH. A company's own figure is said as their claim. Never reuse a sentence "
        "from a model script or a method example: we copy how they tell it, not what they say.\n\n"
        + (f"SCRIPT VOICE GUIDE (the owner's)\n{guide}\n\n" if guide else "")
        + "HOW THE OWNER TALKS\n" + voice_pairs() + owner_voice() + "\n"
        + (f"METHOD EXAMPLE 1, a news story {sized(example)} (a script that works; how it tells the story, not its "
           f"words)\n{example}\n\n" if example else "")
        + (f"METHOD EXAMPLE 2, a tool or product {sized(example_2)} (how it stays connected from start to end, not "
           f"its words)\n{example_2}\n\n" if example_2 else "")
        + (f"METHOD EXAMPLE 3, teaching a topic {sized(example_3)} (the owner's favourite: copy how its intro turns a "
           f"moment into the viewer's problem and how every explanation is a plain picture first, not its words)\n"
           f"{example_3}\n\n" if example_3 else "")
        + "".join(f"SHORT METHOD EXAMPLE {i} {sized(x)} (how one chain hooks and pulls the viewer to the end, not its "
                  f"words)\n{x}\n\n" for i, x in enumerate(shorts, 1))
        + "TECHNICAL (the pipeline needs these)\n"
        f"- {lo} to {hi} spoken words (about {target['seconds']} seconds): count them before you answer.\n"
        + chapters
        + "- Numbers as digits (6.3 billion, 93 cents, 4:20, 2026, 18,270); fractions and everyday ordinals stay "
        "words, and \"one\" on its own stays a word.\n"
        "- Never say the brand name aloud; say \"follow the channel\" or \"follow us\".\n"
        "- HOW IT SOUNDS (owner 2026-11-13: every delivery rule is gone): write it the way a smart person tells a "
        "friend something interesting. Plain words, contractions, sentences of different lengths, a question only where "
        "a person would really ask one. No audio tags, no words in capitals, no \"...\", no exclamation marks for "
        "hype; most of it is simply someone explaining. The voice direction is added afterwards by a separate step.\n"
        "- \"title\": the working title of the video.\n"
        "Return JSON."
    )


DIRECTION_SCHEMA: dict = {
    "type": "object", "additionalProperties": False,
    "properties": {"script": {"type": "string"}},
    "required": ["script"],
}

# 2026-11-13 (owner, after his own Eleven v4 test: "the last one is way better"): the writer writes plainly and a
# separate voice director marks the performance. Tags direct, they never decorate.
DIRECTOR_TAGS = ("curious", "thoughtful", "serious", "skeptical", "quietly", "confidently", "warmly", "amused",
                 "surprised", "excited", "sighs", "chuckles")


def direction_instructions(format_name: str) -> str:
    many = "2 to 4" if format_name == "short" else "about one for every 120 to 150 words"
    return (
        "You are the voice director for an Eleven v4 narration (ElevenLabs). The script is finished. You return the "
        "SAME script with a few audio tags and light punctuation that make one real person sound like they are telling "
        "an interesting story, never like someone performing instructions.\n\n"
        "RULES\n"
        "- Tags direct the performance, they never decorate it. Most of the script has NO tag: a person mostly just "
        "explains. Aim for about 70% relaxed, plain explaining, 20% curious or thoughtful, 10% real weight on the one "
        "or two things that matter most.\n"
        f"- Use {many} tags in total. Put a tag only where the feeling really changes (the hook, the turn, the "
        "reveal, the close), at the start of that sentence. Never two tags together, never two tags in a row on "
        "neighbouring sentences.\n"
        f"- Use only these tags: {', '.join('[' + t + ']' for t in DIRECTOR_TAGS)}. [sighs] and [chuckles] at most "
        "once each, only where a person would really do it. No shouting, no whispering, no laughing out loud.\n"
        "- Emphasis: at most one word in CAPITALS per 150 words, only the word a person would really stress (a fact "
        "word like UNCONFIRMED), never a name or number. No exclamation marks unless the line is truly exciting.\n"
        "- Pace: a paragraph break is a breath; a full stop ends a thought; a comma keeps it flowing; a dash for an "
        "aside. "
        + ("No \"...\" at all.\n" if format_name == "short" else "At most one \"...\" in the whole script.\n")
        + "- You may split a long sentence in two or join two short ones with a comma or \"and\", and you may start a "
        "new paragraph where a person would breathe. You NEVER add, remove or change words, numbers, names or facts, "
        "and you keep every [[n]] chapter marker exactly where it is.\n"
        "Return JSON {\"script\": \"...\"}."
    )


def _spoken_words(text: str) -> list[str]:
    body = re.sub(r"\[\[\d+\]\]", " ", CUE.sub(" ", text))
    return [w for w in re.findall(r"[a-z0-9]+", body.lower().replace("’", "'").replace("'", "")) if w not in ("and",)]


def apply_direction(plain: str, directed: str) -> tuple[str, str]:
    """The directed script when it says exactly the same words (and keeps the chapter markers), else the plain one.
    Returns (script, why)."""
    if not directed.strip():
        return plain, "empty direction"
    if re.findall(r"\[\[\d+\]\]", plain) != re.findall(r"\[\[\d+\]\]", directed):
        return plain, "chapter markers moved"
    if _spoken_words(plain) != _spoken_words(directed):
        return plain, "words changed"
    unknown = {t.strip().lower() for t in CUE.findall(directed)} - {f"[{t}]" for t in DIRECTOR_TAGS}
    for tag in unknown:                                   # an unknown tag is dropped, never read aloud
        directed = directed.replace(tag, "").replace(tag.upper(), "")
    directed = re.sub(r"(\[[a-z ]+\])\s*(\[[a-z ]+\])", r"\1", directed)     # never two tags together
    return directed, "ok"


CUE = re.compile(r"\[(?!\[)[^\]\[]{1,30}\](?!\])")


def strip_cues(text: str) -> str:
    """The script without the voice cues ([excited]...), for the screen, the captions and the counts."""
    # 2026-11-13 (owner): "..." is the voice's pause, never shown: before a new sentence it is a full stop,
    # inside one a comma
    text = re.sub(r"(?:\.\.\.|…)(?=\s*(?:\n|$|\[|[A-Z]))", ".", CUE.sub("", text))
    text = re.sub(r"\s*(?:\.\.\.|…)\s*", ", ", text)
    return re.sub(r"[ \t]{2,}", " ", text).replace(" ,", ",").replace(" .", ".").replace("..", ".")


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


CONNECTIVES = ("so ", "then ", "but ", "and ", "now ", "first", "still ", "because ", "that's ", "that ", "this ",
               "which ", "it ", "it's ", "they ", "you ", "your ", "here's ", "yet ", "or ", "next", "after ", "even ",
               "instead", "plus ", "meanwhile", "suddenly", "and ")


def delivery_problems(script: str, fmt: str = "long") -> list[str]:
    """What would make the script sound wrong when read. 2026-11-13 (owner, after his Eleven v4 test: "break every
    rule you had set in recording"): no more quotas of questions, exclamations, capitals or tags; those made the
    voice perform instead of talk. Left: no "..." stops, a Short is one connected chain, nothing said twice, the
    hook is not a date or a greeting, no run of long sentences."""
    body = CUE.sub(" ", script)
    paras = [p for p in re.split(r"\n\s*\n", script) if p.strip() and not re.fullmatch(r"\s*\[\[?[^\]]*\]\]?\s*", p)]
    sentences = [x for x in re.split(r"(?<=[.!?…])\s+", body) if len(x.split()) >= 2]
    n = max(1, len(sentences))
    out = []
    pauses = body.count("...") + body.count("…")
    if fmt == "short" and pauses:
        out.append(f"{pauses} \"...\" in a Short (want none: the voice stops dead on each; use a full stop)")
    elif pauses > 2:
        out.append(f"{pauses} \"...\" (want at most 2: the voice stops dead on each; use a full stop)")
    if fmt == "short" and n >= 6:
        joined = sum(1 for x in sentences[1:] if x.strip().lower().lstrip("\"'([").startswith(CONNECTIVES))
        if joined < 0.4 * (n - 1):
            out.append(f"only {joined} of {n - 1} sentences carry on from the one before (want at least "
                       f"{int(0.4 * (n - 1)) + 1}): it reads as loose facts, not one chain")
    grams: dict[str, int] = {}
    words = re.findall(r"[a-z0-9']+", body.lower())
    for i in range(len(words) - 5):
        g = " ".join(words[i:i + 6])
        grams[g] = grams.get(g, 0) + 1
    repeated = [g for g, k in grams.items() if k > 1]
    if repeated:
        out.append(f"says the same thing twice (\"{repeated[0]}\")")
    first = re.split(r"(?<=[.!?…])\s+", body.strip(), maxsplit=1)[0].strip().lower()
    months = "january february march april may june july august september october november december".split()
    if re.match(r"(on |in |back in |as of )?(" + "|".join(months) + r"|\d{1,2}(st|nd|rd|th)? |\d{4})", first) or \
            re.match(r"(in this video|today|hey|hi|welcome|so today)", first):
        out.append("the first sentence opens with a date, an announcement or a greeting, not the hook")
    longs = max((len(list(g)) for k, g in __import__("itertools").groupby(len(x.split()) > 22 for x in sentences) if k),
                default=0)
    if longs >= 3:
        out.append(f"{longs} long sentences in a row")
    return out
