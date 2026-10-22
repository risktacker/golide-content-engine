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

import re

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
Owner direction 2026-10-13: no formula hooks. "Most people never notice this about
X" and "You're treating X like Y" were used so often they read as AI. Every hook is
written fresh for THIS story.
- 4 to 10 words. It must stop the scroll on its own and sound like a person said it.
- Lead with the news itself when there is news: name the company, product or person
  and what happened ("Apple just put an AI doctor in your watch.", "Nvidia is now
  worth more than most countries."). A surprising true number, a sharp consequence
  ("Your next job interview may be with a bot."), a clean contrast, or a question
  people will argue about are all good. Choose whichever fits the story best.
- Never use these worn shapes: "Most people never notice...", "You're treating...",
  "You're trusting...", "...people learn too late", "The N levels of...", "Here's
  why...", "Nobody is talking about...", "This changes everything".
- Never start with the same two words as any hook in RECENT_POSTS, and never reuse a
  recent hook's sentence shape.
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
    that make people swipe ("Swipe through the story."), then the debate question.
  * facebook: TWO paragraphs of about five lines each (4 to 6 sentences, 60 to 90 words
    per paragraph; shorter paragraphs are not acceptable). Paragraph one is a concrete,
    everyday scenario the reader recognises from their own life ("You've sent forty
    applications this month and heard back from two."). Paragraph two explains what is
    really going on and what to do about it, using the points. End with the debate question.
  * linkedin: the same two-paragraph shape and length (60 to 90 words per paragraph)
    for professionals. Paragraph one is a
    workplace scenario a manager, engineer or job seeker has lived; paragraph two gives
    the insight and the practical move. End with a debate question professionals can
    answer from experience (the same two-sides rule). LinkedIn readers read, so the copy must carry real weight.
  * x: under 260 characters, no links, no hashtags. The hook plus the sharpest point.
- x_replies: exactly two replies posted under the X post, each under 260 characters,
  no links, no hashtags. Reply one adds the most practical step. Reply two is the
  debate question.
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
  days). The lane is AI and automation, seen across the WHOLE tech industry, not one
  company (owner direction 2026-10-13: "the companies are not just OpenAI"). Look wide:
  AI labs (OpenAI, Anthropic, Google DeepMind, Meta, xAI, Mistral, DeepSeek, Alibaba
  Qwen), big tech (Apple, Microsoft, Amazon, Google, Samsung), chips (Nvidia, AMD,
  Intel, TSMC, Qualcomm), automation and work tools (Zapier, UiPath, Salesforce,
  ServiceNow, Notion, Canva, Adobe, Figma), robots and self-driving (Tesla Optimus,
  Figure, Boston Dynamics, Unitree, Waymo), apps people use daily (TikTok, YouTube,
  WhatsApp, Spotify, Netflix, Uber), money and shopping tech (Stripe, Shopify, PayPal),
  phones, wearables and smart glasses, and what known leaders said or did.
- Check what is actually trending before choosing: tech news front pages, Google
  Trends, YouTube and X tech conversations, Hacker News, Product Hunt.
- Spread it out: never make the same company the main subject twice in the last five
  RECENT topics, and never repeat a recent angle. If OpenAI was recent, look elsewhere
  unless their story is clearly the biggest one this week.
- Pick the story with the widest reach: a launch, a viral demo, a big company move, a
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
  watch for. Then end with a question that splits people into two sides (see THE
  QUESTION THAT STARTS THE COMMENTS), because the goal is conversation.
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


STATIC_SEO_RULES = """\
SEO (owner direction 2026-10-13, every platform)
- keywords: 12 to 15 search phrases people are typing right now about this story (use
  web search for what is trending), most specific first, each 1 to 4 words. Code adds
  them to the captions as one comma-separated line; never put them in platform_copy.
- hashtags: 5 to 8 relevant hashtags (no spaces), mixing the specific story (#CanvaAI)
  with the wider lane (#AI, #TechNews). Code adds them at the very end; never write
  hashtags inside platform_copy.
"""

STATIC_HUMAN_RULES = """\
SOUND HUMAN (owner direction 2026-10-13)
- Captions and slides must read like a sharp person wrote them today, not a template.
  Vary sentence openings; never start two slides or two caption sentences with the same
  word. No "Here's the thing", "Let's dive in", "game-changer", "unlock", "landscape",
  "delve", "in today's world", "seamless", "revolutionize".
- Name real companies, products and people from the story instead of generic "AI".
"""


STATIC_PULSE_RULES = """\
FRESH_HEADLINES (owner direction 2026-10-18: posts use the same trend signal as videos)
- FRESH_HEADLINES lists what people discussed in the last 48 hours on Hacker News and
  Reddit, most-discussed first. Prefer a story from it that is broad and AI or tech,
  then confirm it with web search and cite the original source. Ignore niche,
  political or gossip items. If it is empty or nothing fits, use web search alone.
- Never call a story trending, new or "this week" unless web search shows it is.
"""


def static_post_instructions(slot: str, has_product: bool = True) -> str:
    lane = (POST_A_TREND_RULES if slot == "post-a" else POST_B_PRODUCT_RULES) + STATIC_PULSE_RULES + (
        PRODUCT_SLIDE_RULES if has_product else PRODUCT_SLIDE_EMPTY)
    return (
        "You write one static social post for GOLIDE, a marketplace for digital products, "
        "software and tools. The operator supplies no topic.\n\n"
        + lane + "\n" + VOICE_RULES + "\n" + HOOK_RULES + "\n" + STATIC_HUMAN_RULES + "\n" + STATIC_SEO_RULES + "\n"
        + IMAGE_CONCEPT_RULES + "\n" + STATIC_STRUCTURE_RULES + "\n" + DEBATE_QUESTION_RULES
    )


# ---------------------------------------------------------------------------
# Video scripts (owner reads these aloud; the recording is the master timeline)
# ---------------------------------------------------------------------------

SCRIPT_LENGTH_TARGETS = {
    # Spoken words at ~150 wpm, set below the recording window so the owner
    # has room to breathe. Windows: short 0:30-1:30, long 3:30-5:00.
    "short": {"words_min": 150, "words_max": 185, "seconds": "60 to 75"},
    # 2026-10-22: the owner reads fast (about 170 words a minute: 885 words took 5:07),
    # so 700 to 800 words came out under 5 minutes. 1,300 to 1,450 words is about 8
    # minutes at his pace, past the 8-minute mark where YouTube allows mid-roll ads.
    "long": {"words_min": 1300, "words_max": 1450, "seconds": "450 to 510"},
}


def length_problems(plan: dict, format_name: str) -> list[str]:
    """The model writes short when nothing checks it (scripts came in at 580 to 660 words)."""
    target = SCRIPT_LENGTH_TARGETS.get(format_name)
    if not target:
        return []
    words = sum(len(str(line.get("text", "")).split()) for line in plan.get("lines", []))
    if words < target["words_min"] * 0.92:
        return [f"too short: {words} spoken words, write {target['words_min']} to {target['words_max']} "
                "(go deeper inside the chapters with real facts and the how-it-works, never padding)"]
    if words > target["words_max"] * 1.1:
        return [f"too long: {words} spoken words, cut to {target['words_min']} to {target['words_max']}"]
    return []

SCRIPT_STRUCTURE_RULES = """\
SCRIPT STRUCTURE (in this order)
The sections are the shape of the argument; the viewer should never hear the joins.
1. CLAIM: open straight on the topic with one blunt sentence that flips a common
   belief. Example shape: "AI doesn't decide who gets hired. Systems do."
   Never open with "Imagine", "What if", "Picture this" or a question.
2. PROOF: one concrete, true example anyone already understands.
3. PATTERN: show the rule behind the proof, with 2 to 4 cases of the same rule said
   as ONE flowing sentence, never as separate statements.
4. COST: what happens to people who ignore the rule. Make it specific and familiar.
5. REFRAME: the one sentence the viewer should remember.
6. CLOSE: the verdict in one line (what it means), then the follow call-out, then
   one short closing sentence. No homework: never tell the viewer to go and check,
   open or do something unless the topic itself is a how-to.

NARRATION (owner direction 2026-10-09): the structure above is the order of the
ideas, but it is SPOKEN AS ONE CONNECTED EXPLANATION, like a teacher talking a friend
through it. It must never sound like a list of points read out one by one.
- Every sentence grows out of the one before it. Join them with a spoken word (and,
  but, because, then, for example) only where the meaning connects; never chain
  "which is why" and "that means" by rule (2026-10-22: that reads as AI).
- Each section is entered with a bridge from the last, written fresh for this
  topic, never a stock phrase (see VARIETY).
- Never compress ideas into noun piles ("identity, limits and an audit trail"): say
  what each thing means for the viewer. No colons, no "X: a, b, c" lists.
"""

LONG_STRUCTURE_RULES = """\
LONG VIDEO STRUCTURE: A LESSON IN CHAPTERS
The viewer must always know where they are: "now we're on this, next we're on that".
- "chapters" lists the parts in order. Each has "number" and "title":
  * INTRO first: number "" and title "Intro".
  * Then 4 to 6 numbered chapters, number "01", "02", ... Each chapter has ONE job.
    Title: 2 to 4 plain words, no punctuation, specific to THIS topic.
- MODEL THE SOURCE (owner direction 2026-10-22): when a SOURCE VIDEO is given, the
  chapters follow its angle and the order it tells the story in (a reveal stays a
  reveal, a breakdown of models stays a breakdown, "is it real?" ends in a verdict),
  told more clearly and with our facts. Otherwise choose the shape that fits:
  * a how-to or skill: the stages a viewer would actually go through, in order;
  * an explainer of something new: what it is, how it works, why it matters now;
  * a comparison or decision: the options and what each one really gives you;
  * a trend or news shift: what happened, why now, who it affects, what it means;
  * a mistake or myth: the belief, why it fails, what is actually true.
  These are shapes, not titles. Name each chapter after its real content.
  * CLOSE last: number "" and title "Close".
- Every line sets "chapter" to the index (from 0) of the chapter it belongs to, in order.
- INTRO: the blunt opening claim that flips a common belief, then ONE sentence that
  tells the viewer the route in plain words, naming the numbered chapters in order,
  worded fresh every time (never a stock "In the next few minutes" line).
- Each numbered chapter OPENS with a spoken signpost, written for this topic, that
  makes the new stage obvious (often a question the viewer would ask next, or a
  bridge from the last chapter) and ENDS on what it means: a verdict, a reveal or a
  consequence in one line (never homework) before the next chapter starts. Vary the signposts; never open two chapters the same way. The
  chapter title is never read aloud as a label.
- THE VIEWER LEAVES KNOWING (owner direction 2026-10-22, replaces the 2026-10-13
  steps rule: "things you should do... what are the people going to do about it? It's
  just the verdict"): the payoff is understanding and a clear verdict, not a to-do
  list. Never end a chapter or the video with "check this", "open that", "this week,
  try...", "use these checks". Numbered steps appear ONLY when the topic itself is a
  how-to the viewer will really do (the source video is a tutorial).
- LEARNING, NOT SHOPPING (owner direction 2026-10-17): these are tech news and
  learning videos, never adverts or reviews. Buying advice appears only when the
  product is affordable, widely available and the decision is the point of the
  story, and then as a few lines inside a chapter, never a chapter of its own, and
  never prices repeated as a sales line.
- SCIENCE FIRST (owner direction 2026-10-17): when the topic has science or
  engineering underneath it, give it one or two full paragraphs (its own chapter
  or most of one) with the real numbers from the research turned into something a
  viewer can feel (a speed into metres every second, a force into a weight, a
  pressure into "times the air around you"). This comes BEFORE any verdict or
  buying part. Use only numbers the research gives or simple arithmetic on them,
  and say when a number is the company's claim.
- Keep chapters balanced: none longer than a third of the script.
- Use concrete, true examples inside the chapters; the CLOSE gives the one sentence
  to remember (the verdict), a line that loops back to the opening claim, then the
  follow call-out, then one short closing sentence.
- "section" still tags each line: intro lines "claim", explanation and examples
  "proof" or "pattern", consequences "cost", the line to remember "reframe",
  the follow call-out and final line "cta".
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
  1. the takeaway (what it means, never homework) comes first;
  2. then the follow sentence, joined to the takeaway before it with a connective
     that the sentence before it did NOT start with (owner direction 2026-10-13:
     never two "So" sentences in a row). Vary it from video to video, for example
     "And if this helped, follow the channel...", "That's exactly why you should
     follow us...", "If you want the next one, follow the channel...";
  3. then ONE short closing QUESTION (one or two lines) that is joined to the follow
     sentence with a connective ("Which leaves one question...", "So here's the real
     question...", "And that leaves you with this...") and is written by THE QUESTION
     THAT STARTS THE COMMENTS rules below; it may loop back to the opening idea.
     Never a cold question with no bridge. Nothing else after it.
  * short and long alike: exactly ONE follow sentence, one or two lines.
"""

DEBATE_QUESTION_RULES = """\
THE QUESTION THAT STARTS THE COMMENTS (owner direction 2026-10-20: views without
comments plateau, and polite questions get scrolled past)
- End on ONE question that splits people into two reasonable sides, so a viewer
  feels they must pick one and say why. Put the two sides in the question when it
  helps: "Should OpenCode pay back everyone who lost money, or is a leaked key the
  user's own fault?", "Would you let an AI agent spend your money, yes or no?",
  "Is a fifty-thousand-dollar flying car a breakthrough or a toy?"
- About THIS story and specific: name the company, product, number or choice. Short
  (under 20 words) and answerable in a word or two plus a reason.
- Never polite, empty or rhetorical: not "What do you think?", "Would you trust it?",
  "Let me know", "Interesting, right?", "Is this a good move?". Never ask people to
  comment or type anything; the question itself makes them want to answer.
"""


TEACHING_STYLE_RULES = """\
TEACHING STYLE (owner direction 2026-10-09, locked): explain it so a child follows
it and an expert finds nothing wrong or watered down (the Feynman way).
- THE REAL THING FIRST (owner direction 2026-10-21: "our way of giving examples is
  a distraction amid someone trying to understand"). Explain with the story's own
  concrete facts: what actually happens, step by step, with the real names and
  numbers ("the agent tries a login, reads the error, changes one thing and tries
  again, a thousand times an hour"). That is the example.
- A COMPARISON ONLY IF IT HELPS: use one only where the real mechanism is hard to see,
  and then exactly ONE, chosen because it fits this mechanism closely (a feedback loop
  is like adjusting a shower until the water is right), never a world unrelated to the
  topic. Bridge into it in a few plain words ("it works the way..."), say it in one or
  two sentences right where the hard idea is, then go straight back to the real story
  and never return to it. Many scripts need no comparison at all.
- Keep the real substance: real names, real facts, the real mechanism. Simple words,
  never simplified facts.
- Example before the name: say what happens first, then what it's called.
- Explain every technical word the moment it appears, in the same sentence.
- HOW IT WORKS (owner direction 2026-10-16, this is the value of the channel):
  after the news, give a short plain-words passage on the science or engineering
  underneath it (a short: 3 to 5 lines; a long video: a full stretch inside the
  chapters). Name the real principle (for example Newton's third law, pressure,
  a neural network's training, a battery's chemistry), say what it does in one
  sentence, then show it working in this story and tie it back to the picture.
  Simple and fast, never a lecture, never a list.
"""

# Owner direction 2026-10-13: scripts must not all follow one template. Each
# production gets its own way in and its own turn (2026-10-21: no assigned
# comparison world any more; a comparison is chosen only when it fits),
# chosen from its id, so two scripts in a row never share a pattern.
OPENING_STYLES = (
    "a blunt claim that flips what most people believe",
    "one surprising true number from the research, said plainly",
    "the news itself in one sharp sentence: who did what, and when",
    "a then-and-now contrast in one breath (how it used to work, how it works now)",
    "the consequence first: what is about to change for the viewer, then why",
)


def script_variety(seed: str) -> str:
    import hashlib
    from datetime import date
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", seed)
    if match:  # rotate by day, so scripts on neighbouring days never share a pattern
        n = date(*map(int, match.groups())).toordinal() * 2 + (1 if "long" in seed else 0)
    else:
        n = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16)
    opening = OPENING_STYLES[n % len(OPENING_STYLES)]
    return (
        "VARIETY (this script only; every script is different)\n"
        f"- Open with {opening}.\n"
        "- Bring in the turn (the risk, the cost, the catch) in fresh words written for\n"
        "  this topic; never a stock bridge (2026-10-22: rotating stock turns read as a template).\n"
        "- Never use these stock phrases: \"here's the catch\", \"think of\", \"picture this\",\n"
        "  \"here's the thing\", \"but here's the risk\", \"the catch is\".\n"
    )


SCRIPT_LINE_RULES = """\
FLOW (the most important rule: this is one person talking, not a list of facts)
- Write connected speech. Each sentence must grow out of the one before it, the way a
  good teacher explains something across a table.
- Link ideas the way people talk (and, but, because, then, now, the problem is, for
  example, if, when, until, instead) where the meaning really connects. Plenty of
  sentences simply follow on without a connective; never chain them by rule.
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


HUMANIZER_RULES = """\
SOUND HUMAN, NOT AI (owner direction 2026-10-13)
- Read it aloud in your head: it must sound like one real person talking, not a
  generated script.
- Never start two sentences in a row with the same word. Use "So" to open a
  sentence at most twice in the whole script, and never back to back. Rotate the
  bridges: and, but, because, that's why, which means, then, now, instead, until,
  in other words, the problem is, the thing nobody says, even so, still.
- Talk like the owner talks: short plain sentences, direct, sometimes blunt ("That's
  the fans.", "Anyone calling that flying is wrong."). Connect ideas where the
  meaning connects; do not chain every sentence with "which is why", "so" or
  "that means" (2026-10-22: chained connectives read as AI).
- Vary sentence length and rhythm; a short punch now and then, never a metronome.
- Banned AI phrases: "in today's world", "let's dive in", "dive into", "delve",
  "game-changer", "game changer", "revolutionize", "unlock", "landscape", "navigate
  the", "it's important to note", "in conclusion", "buckle up", "the future is here",
  "stay tuned", "at the end of the day", "seamless", "harness the power".
- No stacked rule-of-three lists, no "It's not X, it's Y" or "the question is not X,
  but Y" more than once, no rhetorical question followed by its own answer more
  than once.
- Never narrate the structure ("That distinction brings us to...", "That leads us
  to...", "Now the useful question is..."); just move to the next thing.
- Concrete and specific beats abstract: names, numbers from the research, what a
  person actually sees or does.
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
    "until now", "from there", "it means", "for each", "second", "third", "fourth", "finally", "within", "before", "while", "meanwhile", "suddenly",
)

STOCK_PHRASES = ("here's the catch", "think of", "picture this", "here's the thing", "but here's the risk",
                 "the catch is", "imagine ")

AI_PHRASES = (
    "in today's world", "let's dive in", "dive into", "delve", "game-changer", "game changer",
    "revolutionize", "revolutionise", "unlock", "landscape", "navigate the", "it's important to note",
    "in conclusion", "buckle up", "the future is here", "stay tuned", "at the end of the day",
    "seamless", "harness the power",
    # 2026-10-22, from the owner's marked script: structure narration and homework lines.
    "that distinction brings us", "brings us to", "leads us to", "the useful question",
    "the simple version is this", "which is why the", "and that's where it can go wrong",
    "this week, use", "use those", "before calling any", "when you replay the clip",
    "you can make this week", "checks you can make",
)


WORN_HOOKS = (
    "most people never notice", "most people don't notice", "you're treating", "you are treating",
    "you're trusting", "you are trusting", "learn too late", "the levels of", "here's why",
    "nobody is talking about", "this changes everything",
)


def hook_problems(hook: str, recent_hooks: list[str]) -> list[str]:
    """A fresh hook: no worn formula, and not opening like a recent one."""
    text = " ".join(hook.lower().replace("\u2019", "'").split())
    problems = [f'the hook uses a worn formula ("{w}"); write a fresh hook for this story'
                for w in WORN_HOOKS if w in text]
    if re.search(r"\bthe \d+ levels\b", text):
        problems.append("the hook uses the worn 'levels' formula; write a fresh hook")
    head = " ".join(text.split()[:2])
    for old in recent_hooks:
        old_head = " ".join(" ".join(str(old).lower().replace("\u2019", "'").split()).split()[:2])
        if head and head == old_head:
            problems.append(f'the hook opens like a recent one ("{old}"); open it differently')
            break
    return problems


def _sentences(lines: list[str]) -> list[str]:
    sentences, current = [], []
    for text in lines:
        current.append(text)
        if text.endswith((".", "!", "?")):
            sentences.append(" ".join(current)); current = []
    if current:
        sentences.append(" ".join(current))
    return sentences


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower().replace("\u2019", "'"))


def repeat_problems(plan: dict, previous: list[str], opener_words: int = 3, phrase_words: int = 5) -> list[str]:
    """Openings and phrases already used in recent scripts (owner direction 2026-10-22:
    "after 3, 4 or 5 scripts... it feels like the same thing, just different titles")."""
    lines = [str(line.get("text", "")).strip() for line in plan.get("lines", []) if str(line.get("text", "")).strip()]
    if not lines or not previous:
        return []
    old_openers: set[tuple] = set()
    old_phrases: set[tuple] = set()
    for script in previous:
        for sentence in _sentences([r.strip() for r in str(script).splitlines() if r.strip() and not r.startswith("[")]):
            words = _words(sentence)
            if len(words) >= opener_words:
                old_openers.add(tuple(words[:opener_words]))
            old_phrases.update(tuple(words[i:i + phrase_words]) for i in range(len(words) - phrase_words + 1))
    reused_openers, reused_phrases = [], []
    for sentence in _sentences(lines):
        words = _words(sentence)
        if len(words) >= opener_words and tuple(words[:opener_words]) in old_openers:
            reused_openers.append(" ".join(words[:opener_words]))
        for i in range(len(words) - phrase_words + 1):
            gram = tuple(words[i:i + phrase_words])
            if gram in old_phrases:
                reused_phrases.append(" ".join(gram))
    problems = []
    if reused_openers:
        problems.append("these sentence openings were already used in recent scripts, write new ones: "
                        + ", ".join(f'"{o}..."' for o in dict.fromkeys(reused_openers)))
    if len(set(reused_phrases)) >= 2:
        problems.append("these phrases were already used in recent scripts, say it fresh: "
                        + ", ".join(f'"{x}"' for x in list(dict.fromkeys(reused_phrases))[:6]))
    return problems


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
    # 2026-10-22: 0.45 forced a connective onto most sentences, which read as AI. The
    # owner-approved Roadster rewrite sits at 0.58; a real list of points at 0.67.
    if body and len(loose) / len(body) > 0.62:
        problems.append(
            "it reads as a list of points, not narration: these sentences do not grow out of the one "
            "before (open them with a bridge such as so, but, because, then, that means, here's the "
            "catch, say you...): " + " | ".join(loose[:5]))
    if any(":" in text for text in lines):
        problems.append("no colons or 'X: a, b, c' lists; say it as a normal spoken sentence")
    first = lines[0].lower().replace(",", " ").split()
    if first and (first[0] in ("imagine", "picture") or first[:2] == ["what", "if"]):
        problems.append("open straight on the topic with a blunt claim, never with Imagine or What if")
    # The ending comes back to the idea the script opened on.
    stop = {"that", "this", "with", "your", "from", "what", "have", "they", "their", "would",
            "only", "just", "about", "there", "when", "will", "into", "than", "then", "because",
            "these", "those", "which", "were", "been", "does", "could", "should", "follow", "channel"}
    words = lambda t: {w.strip(".,?!'\u2019").lower() for w in t.split()} - stop
    early = set().union(*(words(x) for x in sentences[:3])) if sentences else set()
    if len(sentences) >= 6 and not {w for w in words(sentences[-1]) & early if len(w) > 3}:
        problems.append("the final sentence must come back to the idea the script opened on")
    # 2026-10-13 humanizer checks: same opener twice in a row, "So" overuse,
    # a cold (unbridged) closing line, and AI-sounding phrases.
    first_words = [sent.lower().replace(",", " ").split()[0] for sent in sentences if sent.split()]
    twins = sorted({a for a, b in zip(first_words, first_words[1:]) if a == b})
    if twins:
        problems.append("two sentences in a row start with the same word (" + ", ".join(twins)
                        + "); change one opener so each sentence is bridged differently")
    if first_words.count("so") > 2:
        problems.append(f'{first_words.count("so")} sentences start with "So"; use it at most twice and rotate the bridges')
    follow_idx = [i for i, line in enumerate(plan.get("lines", [])) if line.get("follow") is True]
    if follow_idx and len(sentences) >= 2:
        last = sentences[-1]
        if not _bridged(last) and not last.lower().startswith(("because", "and", "which", "until", "then")):
            problems.append("the closing sentence after the follow call-out starts cold; join it with a bridge "
                            "(Because..., And until then..., Which leaves...)")
    text_all = " ".join(lines).lower().replace("\u2019", "'")
    used = [phrase for phrase in AI_PHRASES + STOCK_PHRASES if phrase in text_all]
    if used:
        problems.append("these phrases sound machine-written, rewrite them: " + ", ".join(used))
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
    if not 3 <= len(numbered) <= 6:  # 2026-10-22: 4 to 6 asked for an 8-minute video, 3 still accepted
        problems.append(f"use 4 to 6 numbered chapters between the intro and the close (found {len(numbered)})")
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
    shopping = [c.get("title", "") for c in chapters if SHOPPING_TITLE.search(str(c.get("title", "")))]
    if shopping:
        problems.append("learning, not shopping: no buying chapter (" + ", ".join(shopping) + "); make that "
                        "chapter what this means for the viewer, with at most a few buying lines inside it")
    return problems


SHOPPING_TITLE = re.compile(r"\b(buy|buying|buyer|purchase|shopping|worth (it|buying)|price check|deal)\b", re.I)


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
    if 1 <= after <= 2:
        problems += closing_question_problems(" ".join(str(line["text"]) for line in lines[marked[-1] + 1:]))
    return problems


WEAK_QUESTION = re.compile(
    r"\b(what do you think|what are your thoughts|let me know|would you trust (it|this|them)\b\s*\?|"
    r"is this a good (move|idea)|interesting,? right|right\s*\?$|agree\s*\?$)", re.I)


def closing_question_problems(closing: str) -> list[str]:
    """The last sentence is a two-sided debate question, not a polite one (2026-10-20)."""
    text = closing.strip()
    if not text.endswith("?"):
        return ["end the video on ONE debate question (it must end with a question mark); see THE "
                "QUESTION THAT STARTS THE COMMENTS"]
    if WEAK_QUESTION.search(text):
        return ["the closing question is too polite to answer; make it split people into two sides about "
                "this story (for example: \"...yes or no?\", \"...a breakthrough or a toy?\")"]
    if len(text.split()) > 26:
        return ["the closing question is too long; keep it under 20 words"]
    return []


def script_instructions(format_name: str, seed: str = "") -> str:
    target = SCRIPT_LENGTH_TARGETS.get(format_name, SCRIPT_LENGTH_TARGETS["short"])
    return (
        "You write a narration script for a GOLIDE "
        + ("YouTube/Instagram/Facebook short" if format_name == "short" else "long YouTube video")
        + " on a trending technology, AI, career or digital-work topic. The owner records it "
        "in his own voice; the visuals are animated line diagrams on black, synced to his words.\n\n"
        f"LENGTH: {target['words_min']} to {target['words_max']} spoken words "
        f"(about {target['seconds']} seconds). Do not go over.\n\n"
        + (LONG_STRUCTURE_RULES if format_name == "long" else SCRIPT_STRUCTURE_RULES + "\n" + SHORT_CHAPTER_RULE)
        + "\n" + TEACHING_STYLE_RULES + "\n" + script_variety(seed or format_name) + "\n" + FOLLOW_RULES + "\n" + DEBATE_QUESTION_RULES + "\n" + SCRIPT_LINE_RULES + "\n" + HUMANIZER_RULES + "\n" + SCRIPT_VOICE_RULES
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
