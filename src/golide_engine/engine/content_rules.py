"""GOLIDE content rulebook.

These are the instructions the text model (gpt-5.6-luna today, swappable
later) follows when it writes posts, image concepts and video scripts. They
encode the locked 2026-10-04 direction:

* Visual reference: innertune.affirmations, black theme only.
* Two daily posts: Post A is a pure trend post, Post B is a GOLIDE
  Marketplace product post.
* Shorts and long videos are trend-only and are read aloud by the owner.

Keep every rule here, not scattered through prompts in other modules, so the
whole voice of the engine can be reviewed in one file.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Shared voice
# ---------------------------------------------------------------------------

VOICE_RULES = """\
VOICE
- Write for a smart 16-year-old on a phone: plain words, short sentences, one idea per line.
- Speak to the reader as "you". Confident, calm, direct. Never hype, never preachy.
- Every claim must be true and checkable. No invented statistics, studies, quotes or names.
  If a number is not from a credible current source, do not use a number.
- Never promise jobs, income, trading results, health outcomes or guaranteed results.
- No pseudoscience framed as fact (no "vibration", "manifesting", "the universe decides").
- No em dashes or en dashes anywhere. Use a full stop or a comma.
- No hashtags inside the body text. No emojis in hooks.
"""

HOOK_RULES = """\
HOOK (the line on the image and the first line of every caption)
- 4 to 9 words. Must stop the scroll on its own, with no context.
- Use one of these proven shapes:
  1. Hidden truth: "Most people never notice this about [X]."
  2. Reframe: "[Common belief] isn't the problem. [Real cause] is."
  3. Ladder: "The [N] levels of [skill]. Most stop at 1."
  4. Too late: "[N] [things] most people learn too late."
  5. Direct call-out: "You're training yourself to [bad outcome]."
- Pick the ONE phrase in the hook that carries the meaning (1 to 3 words). This is the
  emphasis phrase: it is rendered bold with a soft glow. It must appear in the hook exactly.
"""

IMAGE_CONCEPT_RULES = """\
IMAGE CONCEPT (describes the picture only; the image model never draws text)
- One subject. One metaphor. Something a viewer understands in one second.
- Draw it as luminous fine-line illustration or a cinematic real-world object, alone in
  deep black space. Good subjects: a single object (jar, key, door, clock, glass of water,
  staircase, seed, chain, compass), one silhouette, one simple diagram shape.
- Exactly one element glows. Name which element glows.
- Describe it in one or two plain sentences. No text, letters, numbers, logos, screens
  with readable UI, or brand names in the concept.
- If a hand or person is shown, they are dark-skinned/Black.
- glow_color: "gold" for growth, value, reward; "cyan" for tech, clarity, insight;
  "white" for neutral or serious.
"""

# ---------------------------------------------------------------------------
# Static posts
# ---------------------------------------------------------------------------

STATIC_STRUCTURE_RULES = """\
POST STRUCTURE
- value_units: 3 or 4 short points that solve ONE clear problem in order. Each point is
  1 or 2 sentences and stands on its own. Not a list of unrelated tips.
- platform_copy, same truth adapted natively:
  * instagram / facebook: hook as first line, a blank line, the points as short lines,
    end with one question that invites a comment.
  * linkedin: professional framing, first line is the hook, points as short paragraphs,
    end with a question for professionals.
  * x: under 270 characters. Hook plus the single sharpest point. No thread markers.
- title: a plain internal label for the post (not shown publicly).
"""

POST_A_TREND_RULES = """\
THIS IS POST A: THE TREND POST.
- Use web search. Find what is being talked about RIGHT NOW (last 7 days) in technology,
  AI, software, careers in tech, the future of work, digital productivity or online
  business. Prefer topics with visible public momentum: a launch, a shift, a debate, a
  number that changed.
- Turn the news into a lesson the reader can use. Do not write a news report.
- Do not mention or promote any GOLIDE product. No links. use_product must be false and
  product_bridge_position must be 0.
"""

POST_B_PRODUCT_RULES = """\
THIS IS POST B: THE GOLIDE MARKETPLACE PRODUCT POST.
- The supplied CANDIDATE_PRODUCT is the subject of this post. use_product must be true.
- Lead with the reader's problem the product solves, never with the product name.
  The hook names the problem or the result, not the brand.
- value_units: point 1 sharpens the problem, point 2 or 3 shows how the product solves it
  (set product_bridge_position to that point), the last point gives one action the reader
  can take today.
- Use only facts present in CANDIDATE_PRODUCT. Do not invent features, prices,
  testimonials, numbers of users or results.
- Do not paste the URL; the engine appends the product link itself.
"""


def static_post_instructions(slot: str) -> str:
    lane = POST_A_TREND_RULES if slot == "post-a" else POST_B_PRODUCT_RULES
    return (
        "You write one static social post for GOLIDE, a marketplace for digital products, "
        "software and tools. The operator supplies no topic.\n\n"
        + lane + "\n" + VOICE_RULES + "\n" + HOOK_RULES + "\n"
        + IMAGE_CONCEPT_RULES + "\n" + STATIC_STRUCTURE_RULES
    )


# ---------------------------------------------------------------------------
# Video scripts (owner reads these aloud; the recording is the master timeline)
# ---------------------------------------------------------------------------

SCRIPT_LENGTH_TARGETS = {
    # Spoken words at ~150 wpm, set below the recording window so the owner
    # has room to breathe. Windows: short 0:30-1:30, long 3:30-5:00.
    "short": {"words_min": 150, "words_max": 185, "seconds": "60 to 75"},
    "long": {"words_min": 600, "words_max": 680, "seconds": "240 to 270"},
}

SCRIPT_STRUCTURE_RULES = """\
SCRIPT STRUCTURE (in this order)
The sections are the shape of the argument; the viewer should never hear the joins.
1. CLAIM: one blunt sentence that flips a common belief. Example shape:
   "AI doesn't decide who gets hired. Systems do."
2. PROOF: one concrete, true example anyone already understands.
3. PATTERN: show the rule behind the proof. Name 2 to 4 cases of the same rule.
4. COST: what happens to people who ignore the rule. Make it specific and familiar.
5. REFRAME: the one sentence the viewer should remember.
6. CALL TO ACTION: one small action, then a line that loops back to the claim.
"""

LONG_STRUCTURE_RULES = """\
LONG VIDEO STRUCTURE: A LESSON IN CHAPTERS
The viewer must always know where they are: "now we're on this, next we're on that".
- "chapters" lists the parts in order. Each has "number" and "title":
  * INTRO first: number "" and title "Intro".
  * Then 4 or 5 numbered chapters, number "01", "02", ... Each chapter has ONE job
    (for example: the real threat, where it hides, how to map it, how to switch,
    the cost of waiting). Title: 2 to 4 plain words, no punctuation.
  * CLOSE last: number "" and title "Close".
- Every line sets "chapter" to the index (from 0) of the chapter it belongs to, in order.
- INTRO: the blunt opening claim that flips a common belief, then ONE sentence that
  tells the viewer the route in plain words ("In the next few minutes, we'll cover
  ..., ..., and ..."), naming the numbered chapters in order.
- Each numbered chapter OPENS with a spoken signpost that makes the new stage
  obvious, often a question ("So first, what are we actually worried about?",
  "Which brings us to the work itself.") and ENDS with a one-line takeaway before
  the next chapter starts. The chapter title is never read aloud as a label.
- Keep chapters balanced: none longer than a third of the script.
- Use concrete, true examples inside the chapters; the CLOSE gives the one sentence
  to remember, one small action for this week, and a last line that loops back to
  the opening claim.
- "section" still tags each line: intro lines "claim", explanation and examples
  "proof" or "pattern", consequences "cost", the line to remember "reframe",
  the action and final line "cta".
"""

SHORT_CHAPTER_RULE = """\
CHAPTERS: a short is one idea. "chapters" must be an empty list and every line's
"chapter" is 0.
"""

SCRIPT_LINE_RULES = """\
FLOW (the most important rule: this is one person talking, not a list of facts)
- Write connected speech. Each sentence must grow out of the one before it, the way a
  good teacher explains something across a table.
- Link ideas with spoken connectives: and, but, so, because, which means, that's why,
  then, now, here's the thing, the problem is, in other words, for example, think about,
  if, when, until, instead. Roughly every second sentence should lean on the one before.
- Mix sentence lengths: some short and punchy, most medium (10 to 22 words), the odd
  longer one that builds. Never more than two short stand-alone sentences in a row.
- Lists of examples are said as one flowing sentence ("a payment service, a private
  network tunnel, even the update on an old phone"), not as separate statements.
- Each section opens with a bridge from the last one ("So where do you start?",
  "And this isn't only about websites.", "Here's what that costs.").
- Never repeat the same sentence opening on consecutive sentences (no runs of
  "Record...", "It must...", "A ... is ...").

LINE RULES (lines are how the speech is split for the screen; they are NOT sentences)
- A line is a breath-sized phrase of 4 to 14 words. A sentence may run across two or
  three lines, so a line can end on a comma or with no punctuation, and the next line
  can begin with "and", "but", "because", "which" and so on.
- Split at natural pauses, never in the middle of a name or number.
- No brackets, no abbreviations, no symbols, write numbers as they are spoken.
- Each line names ONE emphasis word (the word that glows white in the captions).
- Each line names its SUBJECTS: 1 to 3 concrete, drawable things the line is about,
  in plain words ("server rack", "water drop", "thermometer", "brain", "phone",
  "laptop", "house", "sun", "rocket", "briefcase"). The video draws exactly these, so
  the picture always matches the words. Never abstract nouns ("success", "future")
  when a concrete thing exists; pick the object a viewer would picture.
- Each line picks ONE visual layout:
  * icon_hero: one subject, large. Use for a single idea.
  * icon_pair: two subjects, A next to B (comparison, cause and effect, before/after).
  * icon_flow: 3 subjects as steps of a process, top to bottom.
  * icon_orbit: one central subject with 2 to 4 related subjects around it.
  * icon_grid: one subject repeated many times (scale, "millions of", "every").
  * Data diagrams, ONLY when the line states a number, trend or list:
    bar_chart, line_chart, spike_vs_curve (one-off vs compounding), gauge (a level),
    checklist (steps), ladder or staircase (levels/progress), clock (time),
    cross_out (a wrong belief), split_compare (two amounts).
  * logo_end: the final line only.
- Keep the same visual for consecutive lines that build one idea, so the animation
  grows instead of cutting.
- Plain English for a global audience. No slang, no religion, no politics.
"""


SCRIPT_VOICE_RULES = """\
VOICE
- Speak to the viewer as "you". Plain words a smart 16-year-old understands. Confident,
  calm, warm and direct. Never hype, never preachy, never a lecture of bullet points.
- Use contractions the way people talk (it's, you're, don't, that's).
- Every claim must be true and checkable. No invented statistics, studies, quotes or names.
  If a number is not from a credible current source, do not use a number.
- Never promise jobs, income, trading results, health outcomes or guaranteed results.
- No em dashes or en dashes. Use commas, full stops and questions.
"""

CONNECTIVES = (
    "and", "but", "so", "because", "which", "then", "now", "if", "when", "until",
    "instead", "that's", "thats", "here's", "heres", "or", "while", "though", "yet",
    "also", "even", "think", "for", "in", "this", "that", "it's", "its", "after",
    "before", "once", "unless", "since", "as",
)


def flow_problems(plan: dict) -> list[str]:
    """Catch the staccato failure: every line a separate full-stop statement."""
    lines = [str(line.get("text", "")).strip() for line in plan.get("lines", []) if str(line.get("text", "")).strip()]
    if len(lines) < 8:
        return []
    problems: list[str] = []
    ended = sum(1 for text in lines if text.endswith((".", "!", "?")))
    linked = sum(1 for text in lines if text.split()[0].lower().strip(",.") in CONNECTIVES)
    continued = len(lines) - ended
    if ended / len(lines) > 0.8:
        problems.append(
            f"{ended} of {len(lines)} lines are complete stand-alone sentences; let sentences run "
            "across two or three lines so the speech flows")
    if (linked + continued) / len(lines) < 0.35:
        problems.append(
            "too few lines connect to the previous one; link ideas with and, but, so, because, "
            "which means, that's why, for example")
    openings = [" ".join(text.lower().split()[:2]) for text in lines]
    repeats = sum(1 for a, b in zip(openings, openings[1:]) if a == b)
    if repeats >= 2:
        problems.append("several consecutive lines start with the same words; vary the openings")
    return problems


def chapter_problems(plan: dict, format_name: str) -> list[str]:
    """A long video must read as a lesson in clear stages."""
    if format_name != "long":
        return []
    chapters = plan.get("chapters") or []
    numbered = [c for c in chapters if str(c.get("number", "")).strip()]
    lines = [line for line in plan.get("lines", []) if str(line.get("text", "")).strip()]
    problems: list[str] = []
    if not 4 <= len(numbered) <= 5:
        problems.append(f"use 4 or 5 numbered chapters between the intro and the close (found {len(numbered)})")
    owners = [line.get("chapter") for line in lines]
    if any(not isinstance(o, int) or not 0 <= o < len(chapters) for o in owners):
        problems.append("every line needs a valid chapter index")
    elif owners != sorted(owners) or set(owners) != set(range(len(chapters))):
        problems.append("chapters must run in order and every chapter needs lines")
    else:
        words = [len(str(line["text"]).split()) for line in lines]
        total = sum(words) or 1
        for index, chapter in enumerate(chapters):
            share = sum(w for w, o in zip(words, owners) if o == index) / total
            if str(chapter.get("number", "")).strip() and share > 0.36:
                problems.append(f"chapter {chapter.get('number')} {chapter.get('title')} is too long; balance the chapters")
    return problems


def script_instructions(format_name: str) -> str:
    target = SCRIPT_LENGTH_TARGETS.get(format_name, SCRIPT_LENGTH_TARGETS["short"])
    return (
        "You write a narration script for a GOLIDE "
        + ("YouTube/Instagram/Facebook short" if format_name == "short" else "long YouTube video")
        + " on a trending technology, AI, career or digital-work topic. The owner records it "
        "in his own voice; the visuals are animated line diagrams on black, synced to his words.\n\n"
        f"LENGTH: {target['words_min']} to {target['words_max']} spoken words "
        f"(about {target['seconds']} seconds). Do not go over.\n\n"
        + (LONG_STRUCTURE_RULES if format_name == "long" else SCRIPT_STRUCTURE_RULES + "\n" + SHORT_CHAPTER_RULE)
        + "\n" + SCRIPT_LINE_RULES + "\n" + SCRIPT_VOICE_RULES
        + "\n" + SCRIPT_OUTPUT_RULES
    )


VISUAL_CUES = (
    "icon_hero", "icon_pair", "icon_flow", "icon_orbit", "icon_grid",
    "bar_chart", "line_chart", "spike_vs_curve", "gauge", "checklist",
    "ladder", "staircase", "clock", "cross_out", "split_compare", "logo_end",
)

SCRIPT_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "chapters": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"number": {"type": "string"}, "title": {"type": "string"}},
                "required": ["number", "title"],
            },
        },
        "lines": {
            "type": "array",
            "minItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "chapter": {"type": "integer"},
                    "section": {
                        "type": "string",
                        "enum": ["claim", "proof", "pattern", "cost", "reframe", "cta"],
                    },
                    "text": {"type": "string"},
                    "emphasis": {"type": "string"},
                    "visual": {"type": "string", "enum": list(VISUAL_CUES)},
                    "subjects": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
                    "label": {"type": "string"},
                },
                "required": ["chapter", "section", "text", "emphasis", "visual", "subjects", "label"],
            },
        },
    },
    "required": ["title", "chapters", "lines"],
}

SCRIPT_OUTPUT_RULES = """\
OUTPUT
- Return JSON matching the schema. "lines" are the spoken lines in order.
- "text" is exactly what the owner says. Nothing else: no stage directions, labels or notes.
- "emphasis" is one word (or two) copied exactly from "text".
- "label" is a tiny monospace tag drawn on the animation (1 to 3 words, uppercase), for
  example "TRIAL 01", "DAY 30", "WITHOUT A SYSTEM". Never a full sentence.
"""


def script_display(plan: dict) -> str:
    """The script as the owner reads it: chapter headings (not spoken) above each block."""
    chapters = plan.get("chapters") or []
    if not chapters:
        return script_text(plan)
    out: list[str] = []
    current = None
    for line in plan["lines"]:
        text = str(line.get("text", "")).strip()
        if not text:
            continue
        index = line.get("chapter")
        if index != current and isinstance(index, int) and 0 <= index < len(chapters):
            current = index
            chapter = chapters[index]
            heading = " · ".join(x for x in (str(chapter.get("number", "")).strip(), str(chapter.get("title", "")).strip()) if x)
            if out:
                out.append("")
            out.append(f"[{heading.upper()}]")
        out.append(text)
    return "\n".join(out)


def script_text(plan: dict) -> str:
    """The plain words the owner reads, one spoken line per row."""
    return "\n".join(str(line["text"]).strip() for line in plan["lines"] if str(line["text"]).strip())
