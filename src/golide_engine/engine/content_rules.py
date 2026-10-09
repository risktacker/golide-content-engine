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
- value_units: exactly 5, the same five ideas as the five story slides, in order.
- carousel (owner direction 2026-10-07). The post is 8 images: slide 1 is the image
  with the hook, then the 5 story slides, then the marketplace slide (when there is
  one), then the call-out slide. The 5 story slides are the solution, so they must be
  the clearest thing GOLIDE publishes.
  * points: exactly 5 slides that tell ONE story in order, like a short film the reader
    cannot stop swiping:
      1. WHAT HAPPENED: the news in one plain sentence (who did what, when).
      2. WHY IT MATTERS TO YOU: what it changes in an ordinary person's day.
      3. THE CATCH: the problem or risk most people miss.
      4. THE SMART MOVE: the one thing that solves it.
      5. DO THIS TODAY: one concrete step anyone can take in a few minutes.
    Each slide grows out of the one before and ends with ONE short curiosity line
    (shown in gold) that opens a gap the VERY NEXT slide closes (owner direction
    2026-10-07). It can be a question ("So what do you do?") or a teaser that is not
    a question ("But there's a catch.", "Here's the part most people miss."); mix the
    two, never the same line twice. The next slide must answer it directly in its
    first sentence. Slide 5's last line is the payoff: the result the reader gets, no
    new gap.
  * Words a 12-year-old knows. No jargon, no abstract phrases ("separate help from
    permission"), no riddles. Say the thing plainly.
  * NO TITLES (owner direction 2026-10-07): a slide is only its text, shown large
    under a small number. text: two or three short sentences, at most 30 words, that
    say the point plainly and end with the short pull to the next slide. emphasis: the
    1 to 3 key words, copied exactly from the text, shown in bold.
  * callout: the last slide asks the reader to follow. text: one or two short
    sentences with the reason ("Want one clear AI update every day? Follow GOLIDE so
    the next one finds you."). emphasis copied from it. Written text may say GOLIDE.
    No "comment", "like", "share" or "link". The engine adds the follow pill.
  * CONSISTENCY: if the hook promises a number, it must be 5 and every caption uses 5.
    If the hook has no number, do not mention a count anywhere.
- platform_copy, same truth adapted natively. Never put a URL in any copy; the engine
  adds links only where they belong.
  * instagram: the hook as the first line, a blank line, two or three short lines
    that make people swipe ("Swipe through the story."), then one question that
    invites a comment.
  * facebook: TWO paragraphs of about five lines each (4 to 6 sentences, 60 to 90 words
    per paragraph; shorter paragraphs are not acceptable). Paragraph one is a concrete,
    everyday scenario the reader recognises from their own life ("You've sent forty
    applications this month and heard back from two."). Paragraph two explains what is
    really going on and what to do about it, using the points. End with one question.
  * linkedin: the same two-paragraph shape and length (60 to 90 words per paragraph)
    for professionals. Paragraph one is a
    workplace scenario a manager, engineer or job seeker has lived; paragraph two gives
    the insight and the practical move. End with a question professionals can answer
    from experience. LinkedIn readers read, so the copy must carry real weight.
  * x: under 260 characters, no links, no hashtags. The hook plus the sharpest point.
- x_replies: exactly two replies posted under the X post, each under 260 characters,
  no links, no hashtags. Reply one adds the most practical step. Reply two asks a
  specific question that invites people to answer in the comments.
- source_url: the single most credible source page you used (the article itself, https).
- title: a plain internal label for the post (not shown publicly).

NEVER REPEAT YOURSELF
- RECENT_POSTS lists what GOLIDE already published in the last three weeks.
- Do not reuse any hook, hook shape ("X isn't the problem, Y is"), opening line,
  scenario or point from it, and do not paraphrase one.
- Never cover the same story or announcement as a recent post; if the same company is
  in the news again, take a clearly different story. Name the story in "weekly_theme".
- The image concept must use a different object and metaphor from the one a recent
  hook would suggest (no second funnel, staircase or door in a row).
"""

TREND_TASTE_RULES = """\
WHAT TO TALK ABOUT: THE AI AND TECH GIST EVERYONE IS DISCUSSING
- Use web search. Pick the story people are actually talking about RIGHT NOW (last 7
  days): a launch, a viral demo, a big move or statement from a company or leader
  everyone knows (OpenAI, Google, Meta, Apple, Microsoft, Nvidia, Tesla, xAI, Amazon,
  Samsung; Sam Altman, Mark Zuckerberg, Elon Musk, Jensen Huang, Sundar Pichai), a
  change that reaches ordinary people's phones, jobs, money, school or daily life, or a
  debate where people have opinions.
- The test: would a curious person who is NOT in tech stop scrolling, understand it in
  one read, and want to say what they think in the comments? Write for the AI
  enthusiast, the student, the parent, the small business owner.
- Avoid deep technical topics that need special background (cryptography internals,
  chip architecture, research papers) unless the story itself is mainstream news, and
  then explain it in everyday words with zero jargon. Never assume the reader knows a
  term; if a term is unavoidable, say what it means in plain words.
- What leaders said or did is fair game when credible outlets report it; quote or
  describe it accurately and say who said it. No rumours, no private life, no party
  politics.
- Turn the story into something useful: what it means for the reader, what to do or
  watch for. Then end with a question people want to answer ("Would you trust it?",
  "Is this a good move?"), because the goal is conversation.
- Do not mention or promote any GOLIDE product in the copy. use_product must be false
  and product_bridge_position must be 0. The product only appears on its own slide.
"""

POST_A_TREND_RULES = """\
THIS IS POST A: THE MORNING TREND POST.
""" + TREND_TASTE_RULES

PRODUCT_SLIDE_RULES = """\
- product_slide: ONE marketplace slide, second to last (after the 5 story slides,
  before the call-out). It introduces CANDIDATE_PRODUCT to the same reader as the next
  step. No title: text is one or two short sentences naming the result it gives,
  using only facts in CANDIDATE_PRODUCT (no invented features, prices, users or
  results); emphasis copied from the text. The engine adds "Link in bio". Bridge it
  naturally from the story where you can ("Want to go further?").
"""

POST_B_PRODUCT_RULES = """\
THIS IS POST B: THE EVENING TREND POST.
- A DIFFERENT story from this morning's post (it is in RECENT_POSTS): another company,
  another kind of story.
""" + TREND_TASTE_RULES

PRODUCT_SLIDE_EMPTY = """\
- product_slide: leave emphasis and text as empty strings.
"""


def static_post_instructions(slot: str, has_product: bool = True) -> str:
    lane = (POST_A_TREND_RULES if slot == "post-a" else POST_B_PRODUCT_RULES) + (
        PRODUCT_SLIDE_RULES if has_product else PRODUCT_SLIDE_EMPTY)
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
SCRIPT STRUCTURE: A STORY TOLD BY A TEACHER (owner direction 2026-10-09)
This is NARRATION. One person explains one thing to a friend who has never heard of
it, from start to finish. It is never a list of points, a briefing or a summary.
Every sentence answers the question the sentence before it raises in the listener's
head ("what does that mean?", "how?", "so what?", "what do I do?"), and the
listener always knows where the story is going.
Tell it in these stages, in order, joined by spoken bridges:
1. HOOK (2 to 3 lines): put the viewer inside a situation they recognise, in the
   second person ("Imagine...", "You know when...", "What if..."), then say what
   just changed.
2. WHAT'S HAPPENING: explain the news in plain words, as if the listener has never
   heard of it. Say how things worked until now, then what is different
   ("Until now..., but this...").
3. WALK-THROUGH: ONE concrete example told step by step as a little story
   ("Say you ask it for... First it..., then..., and by the time..."). One example
   told well, never a list of several.
4. THE CATCH: the turn, opened with a bridge ("But here's the catch...",
   "The problem is..."), told as a consequence for the viewer, with a familiar
   picture of what could go wrong.
5. WHAT TO DO: answer "so what do I do?" with one small, practical step, said the way
   you'd advise a friend.
6. CLOSE: the follow call-out, then one short closing sentence.
Never compress ideas into noun piles ("identity, limits and an audit trail"):
say what each thing means for the viewer in a normal sentence. Explain every
technical word the first time it appears. No colons, no "X: a, b, c" lists.
"section" tags each line: hook "claim", what's happening "proof", walk-through
"pattern", the catch "cost", the one line to remember "reframe", what to do and
the close "cta".
"""

LONG_STRUCTURE_RULES = """\
LONG VIDEO STRUCTURE: A LESSON IN CHAPTERS
The viewer must always know where they are: "now we're on this, next we're on that".
- "chapters" lists the parts in order. Each has "number" and "title":
  * INTRO first: number "" and title "Intro".
  * Then 3 to 5 numbered chapters, number "01", "02", ... Each chapter has ONE job.
    Title: 2 to 4 plain words, no punctuation, specific to THIS topic.
- Choose the chapter shape that fits the topic; do not reuse a fixed template:
  * a how-to or skill: the stages a viewer would actually go through, in order;
  * an explainer of something new: what it is, how it works, why it matters now,
    what changes for you;
  * a comparison or decision: the options, what each costs you, how to choose;
  * a trend or news shift: what happened, why now, who it affects, what to do;
  * a mistake or myth: the belief, why it fails, what works instead.
  These are shapes, not titles. Name each chapter after its real content.
  * CLOSE last: number "" and title "Close".
- Every line sets "chapter" to the index (from 0) of the chapter it belongs to, in order.
- INTRO: the blunt opening claim that flips a common belief, then ONE sentence that
  tells the viewer the route in plain words ("In the next few minutes, we'll cover
  ..., ..., and ..."), naming the numbered chapters in order.
- Each numbered chapter OPENS with a spoken signpost, written for this topic, that
  makes the new stage obvious (often a question the viewer would ask next, or a
  bridge from the last chapter) and ENDS with a one-line takeaway before the next
  chapter starts. Vary the signposts; never open two chapters the same way. The
  chapter title is never read aloud as a label.
- Keep chapters balanced: none longer than a third of the script.
- Use concrete, true examples inside the chapters; the CLOSE gives the one sentence
  to remember, one small action for this week, a line that loops back to the
  opening claim, then the follow call-out, then one short closing sentence.
- "section" still tags each line: intro lines "claim", explanation and examples
  "proof" or "pattern", consequences "cost", the line to remember "reframe",
  the action and final line "cta".
"""

SHORT_CHAPTER_RULE = """\
CHAPTERS: a short is one idea. "chapters" must be an empty list and every line's
"chapter" is 0.
"""

FOLLOW_RULES = """\
FOLLOW CALL-OUT (owner direction 2026-10-07: viewers should follow and come back)
- Ask the viewer to follow in one natural spoken sentence, said in the owner's
  voice as part of the talk, never read like an advert.
- Say "follow us" or "follow the channel". NEVER say the brand name aloud anywhere
  in the script (owner direction 2026-10-07: it is a Bantu word for gold and is
  easily mispronounced and misheard). The screen shows "FOLLOW GOLIDE" for you.
- Give the reason to follow, not a plea: what they will miss or keep getting
  ("the feed won't show us to you again unless you follow", "we break down one
  of these every day", "the next one picks up exactly where this ends").
  A little urgency is good; guilt, begging and hype are not.
- NEVER ask people to comment, like, share, type a word, or "comment X to receive"
  anything. NEVER mention links or the bio. Only follow (or subscribe) and come back.
- Write it fresh for this topic every time. Never reuse the example wording above.
- Set "follow": true on the line or lines of that sentence; every other line false.
- Placement and shape (owner direction 2026-10-07, from the reference channel's
  endings): the call-out comes at the END, only after the value is given.
  1. the takeaway and the small action come first;
  2. then the follow sentence, starting with "So" ("So follow the channel, ...");
  3. then ONE short closing sentence (one or two lines) that pays off the follow
     or loops back to the opening idea ("...because tomorrow there is a new one
     waiting for you"). Nothing else after it.
  * short and long alike: exactly ONE follow sentence, one or two lines.
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
- Each line names ONE emphasis: the key term of that line, shown in gold in the captions.
  Pick what the viewer must remember: a name ("Nvidia", "Sam Altman"), a number
  ("25 percent"), or the key idea or term ("crypto agility", "inventory"). Never a
  filler word ("really", "just", "the"). One or two words, copied exactly from the line.
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

# Words that, near the start of a sentence, show it grows out of the one before
# (2026-10-09: sentence-level check, because comma-split lines hid a list of claims).
BRIDGES = (
    "and", "but", "so", "because", "which", "then", "now", "if", "when", "until",
    "instead", "that's", "here's", "first", "next", "after", "say", "imagine",
    "picture", "think", "for example", "in other words", "that means", "which means",
    "the problem", "the catch", "worse", "still", "once", "by the time", "even",
    "only", "what if", "you know", "or", "yet", "this means", "that way", "otherwise",
    "until now", "from there", "it means", "for each", "within", "before", "while", "meanwhile", "suddenly",
)

def _sentences(lines: list[str]) -> list[str]:
    sentences, current = [], []
    for text in lines:
        current.append(text)
        if text.endswith((".", "!", "?")):
            sentences.append(" ".join(current)); current = []
    if current:
        sentences.append(" ".join(current))
    return sentences


def _bridged(sentence: str) -> bool:
    head = " ".join(sentence.lower().replace("\u2019", "'").replace(",", " ").split()[:4])
    return any(head == b or head.startswith(b + " ") or (" " + b + " ") in (" " + head + " ") for b in BRIDGES)


def flow_problems(plan: dict) -> list[str]:
    """Catch a script that reads as a list of points instead of narration."""
    lines = [str(line.get("text", "")).strip() for line in plan.get("lines", []) if str(line.get("text", "")).strip()]
    if len(lines) < 8:
        return []
    problems: list[str] = []
    ended = sum(1 for text in lines if text.endswith((".", "!", "?")))
    if ended / len(lines) > 0.8:
        problems.append(
            f"{ended} of {len(lines)} lines are complete stand-alone sentences; let sentences run "
            "across two or three lines so the speech flows")
    sentences = _sentences(lines)
    body = sentences[1:]
    loose = [s for s in body if not _bridged(s)]
    if body and len(loose) / len(body) > 0.45:
        problems.append(
            "it reads as a list of points, not narration: these sentences do not grow out of the one "
            "before (open them with a bridge such as so, but, because, then, that means, here's the "
            "catch, say you...): " + " | ".join(loose[:5]))
    if any(":" in text for text in lines):
        problems.append("no colons or 'X: a, b, c' lists; say it as a normal spoken sentence")
    opening = " ".join(sentences[:2]).lower()
    if not any(w in opening.replace("\u2019", "'").split() for w in ("you", "your", "you're", "imagine", "you've")):
        problems.append("the hook must put the viewer in the story (talk to 'you' in the first two sentences)")
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
    if not 3 <= len(numbered) <= 5:
        problems.append(f"use 3 to 5 numbered chapters between the intro and the close (found {len(numbered)})")
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


FOLLOW_ASKS = ("comment", "hit like", "like the video", "like this video", "leave a like", "share", "link", " bio", "type ")


def follow_problems(plan: dict, format_name: str) -> list[str]:
    """The follow call-out is present, early, short, and never asks for comments."""
    lines = [line for line in plan.get("lines", []) if str(line.get("text", "")).strip()]
    if len(lines) < 8:
        return []
    marked = [i for i, line in enumerate(lines) if line.get("follow") is True]
    problems: list[str] = []
    if not marked:
        return ["add the follow call-out sentence and mark its lines with \"follow\": true"]
    after = len(lines) - 1 - marked[-1]
    if marked[0] < len(lines) - 4 or marked != list(range(marked[0], marked[-1] + 1)):
        problems.append("the follow call-out must come at the end, after the value; "
                        "move it there and remove it from anywhere earlier")
    elif not 1 <= after <= 2:
        problems.append("after the follow sentence, end with ONE short closing sentence (one or two lines)")
    if len(marked) > 2:
        problems.append(f"the follow call-out is too long ({len(marked)} lines); keep it to one sentence")
    said = " ".join(str(lines[i]["text"]).lower() for i in marked)
    if any("golide" in str(line.get("text", "")).lower() for line in lines):
        problems.append('never say the brand name aloud; say "follow us" or "follow the channel"')
    if "follow" not in said and "subscribe" not in said:
        problems.append("the follow call-out must actually say follow or subscribe")
    if any(word in said for word in FOLLOW_ASKS):
        problems.append("the follow call-out must not ask for comments, likes, shares or links")
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
        + "\n" + FOLLOW_RULES + "\n" + SCRIPT_LINE_RULES + "\n" + SCRIPT_VOICE_RULES
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
                    "follow": {"type": "boolean"},
                },
                "required": ["chapter", "section", "text", "emphasis", "visual", "subjects", "label", "follow"],
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
