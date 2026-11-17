# Ideas and scripts for ReachMora creators

## Who you are writing for

The person using this skill is a **ReachMora creator**: someone building a faceless YouTube channel with AI tools. They want long-form animated videos that get clicked, get watched to the end, and earn (watch time, high-RPM niches, bingeable series), without filming, drawing or paying for tools. Their viewers are a general YouTube audience, mostly 18-44, who watch money, business, psychology, history and life-lesson channels.

So every idea must work on two levels:
1. **For the viewer**, a story or insight they can't stop watching.
2. **For the creator**, a niche that monetizes, a format they can repeat weekly, and a title that fits a series.

## Niche menu (mix these across the 10 ideas unless the user named a niche)

| niche | why it works for a faceless channel | strongest formats |
|---|---|---|
| Money stories, scams and cons | high RPM, strong curiosity, endless supply | story, rise-and-fall |
| Business rise and fall | high RPM, evergreen, search plus browse traffic | story, timeline |
| Psychology and human behaviour | huge browse traffic, very bingeable | explainer, list, versus |
| Self-improvement and life lessons | loyal subscribers, long watch time | list, versus, "the person who..." |
| How money really works (economics, investing basics) | top RPM, search traffic | explainer, counter-heavy |
| Weird history and mysteries | broad appeal, great hooks | story, map-heavy |
| Light true crime (heists, frauds, escapes; nothing graphic) | strong retention | story |

Prefer topics with a **physical, drawable cause and effect**: documents, money changing hands, a journey, a before and after, two people compared. Avoid topics that are only abstract.

## The 10-idea reply

Number them 1-10 and give each:
- **Title**: 4-9 words of curiosity-gap packaging, as you'd upload it. Patterns: "The Man Who Sold the Eiffel Tower (Twice)", "Why Smart People Stay Broke", "How One Typo Cost a Bank $900 Million", "The Psychology of People Who Never Text First", "7 Money Rules Rich People Don't Say Out Loud", "What Happens to Your Money When a Bank Collapses".
- **Thumbnail text**: 2-4 words that don't repeat the title.
- **Hook**: the first spoken line, a paradox or shocking fact stated plainly. No "In this video".
- **The payoff**: the twist or insight the video ends on, in one line.
- **Why it performs**: the niche, who clicks, and the series it could start ("works as episode 1 of a 'Greatest Cons' series").
- **Best length**: which of 3/5/10/15 min the story can actually fill without padding.
- **Fact status**: documented, disputed, or legend. For anything presented as true, run a quick web search on the key facts **before** offering it. Never present a viral myth as fact; frame it as "legend says" or swap the idea.

Mix: at least 4 niches, at least 3 formats (story, explainer, list or versus), and a range of best lengths. Ask the user to reply with a number (or "more ideas", or their own topic).

Never: medical or legal advice, personal financial advice ("buy this stock"), real private individuals, mocking real living people, graphic violence, partisan politics, copying another channel's video or series name. Explaining money concepts is fine: keep it educational and use one line like "this isn't financial advice, it's how the math works" when the video gives money tactics.

## Script length (about 150 spoken words per minute)

| length | words | shots | chapters (silent cards) |
|---|---|---|---|
| 3 min | 430-470 | 30-40 | 0-1 |
| 5 min | 720-780 | 50-65 | 1-2 |
| 10 min | 1,450-1,550 | 100-130 | 3-4 |
| 15 min | 2,200-2,300 | 150-190 | 4-6 |

Check with `python3 -m engine sentences <P>` (it prints the word count). If a story can't fill the length honestly, say so and suggest the shorter length rather than padding.

## Structure

**3 min**: hook (first 10 s) → setup (who, when, where, one concrete detail) → 3 escalating beats → the twist → payoff and a one-line takeaway → teaser line.

**5 min**: hook → promise ("by the end, you'll know why...") → chapter 1 (setup + 2 beats + mini-payoff) → chapter 2 (escalation + twist) → payoff → takeaway → teaser.

**10 min**: cold open in the middle of the action (30-45 s) → title promise → 4 chapters of about 2 min. Each chapter opens with a mini-hook and ends on an open loop ("but that wasn't the problem"). A reversal comes around minute 6, then a callback ending that returns to the cold open, and a teaser for the next video.

**15 min**: the 10 min shape with 5-6 chapters, a midpoint reversal around minute 7, two or three short two-character skits (one narrator reading both is fine), a "you" moment every ~45 s, and a bigger final act.

## Line rules (the voice is the timeline, so write for the ear)

- Short sentences: 6-14 words, average about 9. One idea per sentence, because each sentence becomes a shot beat.
- Spoken English with contractions. Write numbers the way they're said ("two hundred and forty thousand dollars").
- Every big number gets an everyday comparison ("that's six years of rent").
- Put in "you" moments that tie the story to the viewer's life about every 30-45 s.
- Re-hook every 60-90 s: "Here's the strange part.", "But that's not the crazy bit.", "And then it got worse."
- Never describe what the viewer already sees. No headings, stage directions or [brackets] in the spoken text.
- Chapter cards are silent. Put them in `script.txt` as lines starting with `# ` (the engine skips them). In the copy you give the user to record, leave them out and list the chapter titles separately.
- Optional subscribe line near the end, natural and specific: "If this changed how you see money, subscribe. Next week: the man who bought a pizza for a fortune."

## Recording tips to give the user

- One voice, one file (mp3, wav or m4a), no music, no effects. Read the text exactly; if they change words, ask for the final text.
- ElevenLabs works well: a warm narrator voice, stability about 45-55 %, similarity about 75 %, style 0-15 %, speed 1.0. For 10-15 min scripts, use ElevenLabs Studio (Projects) to export one file, or upload numbered parts; you'll join them.
- A natural pause at sentence ends (0.3-0.6 s) makes the cuts land cleanly.
- Own voice: a quiet room, phone or USB mic 15-20 cm away, one continuous take or numbered takes.
