# GOLIDE Content Engine: standing instructions

Owner: Esiah (Lusaka, UTC+2). Direct, no sugar-coating. Studio: studio.golidee.com
(Cloudflare Worker `worker/index.js`, D1, R2). Engine: Python on GitHub Actions
(`production-scheduler.yml`), daily Short and long video.

## Owner's rules (always)
- Talk before code on anything that costs money or changes visuals; state costs first. "Approved" or "Perfect" = go.
- Show a preview (still frames / contact sheet) before pushing visual changes. Not a full video unless asked.
- Never touch the music videos. Licence-clear music and assets.
- Real photos (owner 2026-11-17): people, products and news photos are used as they are (no face blurring), always as
  commentary: framed card with the source named on screen and in the description, never a full-screen background.
  Search order: official/Wikipedia first, then news and social pictures. Thumbnails show the person's real photo when
  the title is about one person (`photo_card` design). Never fake a person's quote or make a look-alike.
- Thumbnails (owner 2026-11-10): real logos of the products and apps in the story are used; no owner avatar
  (only when he is in the video); real objects, never generative look-alikes; real people's photos allowed (2026-11-17).
- Thumbnail engine (owner 2026-11-12, `vector/thumb_engine.py`): long videos only. Designs copied from the owner's
  model thumbnails with Goli in place of the person; each keeps its model's own lettering and finish (no blanket
  shadows or glow). Picked per video against the modelled video's thumbnail; never the last two designs; every
  design passes the collision, small-words and empty-frame checks before use. Add a design only with a model.
- Goli openings and endings (owner 2026-11-12, `edit/editor.py` INTROS/OUTROS, `edit/compose.py` bookends): long
  videos open with one of 7 and close with one of 5 (our own end card, not YouTube's), never one of the last 3 used.
  Goli is the default for long videos too (`config/edit-engine.json`).
- Parked (owner 2026-11-10): a Skool community (videos posted there, classroom of repos and sources) comes
  after the Advanced list.
- No cloned voice. AI voice = ElevenLabs "Mark - Natural Conversations" (UgBBYS2sOqTuMpoF3BR0), only when the
  owner taps "Use AI voice" for that video; otherwise his own recording. Monthly cap 115,000 characters.
  Eleven v4 (owner 2026-11-13, after his own test): ONE read per video (v4 takes 10,000 characters; split only past
  that, at paragraphs); no hook takes. The writer writes plainly (no tags, capitals, "..." or hype); a separate voice
  director (`engine/story.py` direction_instructions) adds 2-4 tags in a Short, about one per 120-150 words in a long
  video, only where the feeling changes, never stacked; it may not change a word (checked, else the plain script).
- Link first (owner 2026-11-14): every scheduled slot waits in Studio ("Needs your link") for the video he pastes;
  the engine writes the script from it (tagged copy shown for ElevenLabs) and waits for his recording. No link by
  the slot's time (Short 13:00, long 19:30): the engine picks the topic, reads it with the AI voice and publishes
  30 minutes after the render (`orchestration/queue.py` waiting_for_link / link_fallback). The voice is never
  processed after ElevenLabs (no EQ/compressor chain), only levelled.
- Trials are labelled as trials. Don't paste API tokens. Digits for numbers.
- Don't poll or babysit long runs; it burns the owner's usage.
- Never start with limits. Build the general capability the owner asks for, not a fixed short list.

## Script writer (`src/golide_engine/engine/story.py`)
One story call writes the whole narration the way working videos do (model scripts of the day plus
`config/story-example.txt` and `config/story-example-2.txt`), in the owner's voice guide
(`config/script-voice.md`), facts only from verified research. Code cuts it into screen lines; a separate
storyboard call picks gold words and pictures. Copy the method of model scripts, never their sentences.
Close model (owner 2026-11-22, replaces 2026-11-17): a video he pastes with its transcript (the Studio box under the link,
or the engine's own fetch: the Studio Worker reads the captions first, `worker/transcript.js`) is CONDENSED to our length
without changing its context: the model's own sentences word for word, cut repeats, side stories, intros and filler first,
then the weakest beats; a few joining words only where a cut leaves a gap; the creator's own plugs out
(`story.CLOSE_MODEL`, `spec.model_transcript`).

Model channels (owner 2026-11-22, until 2026-12-22, `config/trend-sources.json` "focus"): the engine models ONLY
Crayon Capital (suggests Stickman + Goli) and Outskill, Nate Herk, Matt Penny, Sanji Nai-Chien (suggest Goli); their
best unmodelled video of the last 45 days, no numbers bar. The channel's style is used only when the owner picked none.

## 3D engine (`src/golide_engine/vector/motion3d.py`)
- Any object: the storyboard writes `3d: object=<name>; move=<lift|slide|open|swing|spin|explode|rise>;
  on=<spoken word>; <box|cyl|sphere|cone x y z w d h [rx90] [gold] [mover]>; ...` (parsed in
  `vector/figures/devices.py`). Presets: laptop, phone, server, chip, battery.
- Look: rounded parts (convex hulls), smooth normals, key/fill/specular/rim light, polished gold, contact
  shadow, no wireframe. Rasterizer compiled with numba.
- Placement and drawing in `vector/render.py` (`_motion*`, `_draw_motion`); 3D scenes stand on the house
  floor grid and horizon glow (`vector/stage.py`, stage "grid"), floor at the object's base.
- Balance rule (in `vector/illustrate.py`): 3D for real things, line drawings/charts/diagrams for
  explanations, about half the scenes 3D, never more than 3 in a row.
- Moves 0.6 s on the spoken word; slow turn through the scene; poses reused until visibly turned.

## Edit engine scenes (owner 2026-11-13, `edit/`)
- Real runs (`edit/demos.py`): read-only commands only (allowlist), shown as a terminal with the proving line lit.
- Visual metaphors (`edit/metaphors.py`): scales, unlock, magnify, funnel, stack, gauge, transform, iceberg, cycle;
  about 1 in 4 scenes of a long video (max 6), 1 per Short, never the same twice in a video.
- Owner review 2026-11-14: long videos are mostly pictures (glass 3D up to 4, metaphors, nodes, real runs); a words
  block is rare and shows a complete headline phrase, never a cut sentence or keyword pile; a long picture holds
  instead of cutting to word fragments; owner 2026-11-17: NO words blocks at all (`editor.WORDS_MAX = 0`). Text only where it is the
  content: a real quote, a prompt to copy, the key number. His recording is the script: changed words rebuild lines, captions and
  blocks from what he said (`owner_changes.reading_from_audio`).
- Glass 3D (`assets/edit/g3d/glass3d.js`, three.js in the video): laptop, phone, server, chip, battery in clear glass
  with lit edges, one gold part with a callout line to its label, two other parts named. Max 4 per long video, 2 per
  Short, never two in a row. Goli faces the content (mirrored on the right).

## Shorts (owner 2026-11-13, after the broken USB Short)
- Length (owner 2026-11-18, no two ways): every Short is 45-75 s. Studio refuses a recording outside it, the engine
  stops one before the paid work.
- Script: 115-185 words (45-75 s), its own method (`engine/story.py` short shape): one direction, a hook that puts the
  viewer in someone's shoes, then a chain where each step causes the next, a turn, a payoff tied to the first line.
  Model: `8e4TYDVZTwk` (read for every Short, `config/model-videos.txt` "always"). No "..." in a Short; long at most 1;
  "..." is never shown on screen. One read; voice parts must add up to the script.
- Sound: no pops or ticks; whoosh on cuts, an impact only on a big number (`edit/render.py` sound_plan).
- Music: Discipline Finishes under every Short until 2026-12-13 (`short_signature`), 3D Shorts included, one steady
  bed, no dips.
- Frame: content stays inside the phone crop (130 px left, 160 right, 230 top) at every moment (`layout.keep_inside`).
- Pace: no picture under 1.0 s (Short) / 1.5 s (long); 1 metaphor per Short, 3 per long; a strong transition
  (zoom, flash, iris, whip) at most once in three cuts, the rest glide or cut.

## Stickman (owner 2026-11-17): the third visual style, next to Inkee and Goli
- Long videos are made with ReachMora's own package, imported not copied (`vendor/reachmora`, `stickman/longform.py`);
  its rules win for them (its music, SFX, captions, chapter cards). Shorts are made in the 3D Shorts engine (see
  "3D Shorts" below); the flat-card cartoon-short-kit was removed on 2026-11-22.
- The characters are actors: the narrator speaks, nobody's mouth talks. Real people are generic puppets, no likeness.
- Our engine feeds only the voice, our word timings and research; Sol writes story.json (long) from the kit's own
  documents. No paid retries (owner 2026-11-22): Sol writes the storyboard ONCE and it is
  saved at once; the plan / look checks are repaired by the engine for free on that same storyboard (camera guard, more
  light, safe helpers, collisions taken out) and it re-renders. Nothing goes back to Sol and nothing falls back to Goli.
- Stickman + Goli (owner 2026-11-17, `stickman/goli_layer.py`): a fourth choice in Studio, per video. The finished
  Stickman video plays in a framed panel; Goli stands full-body beside it ("beside" place in `edit/compose.py`),
  facing it, mouth on the voice, reactions on the story's events (numbers -> point, shock lines -> shock, lists and
  versus -> explain, payoff -> both hands up), at least 2.2 s apart. The video's own sound is kept untouched.
  Long videos only (owner 2026-11-17): on a Short Goli would distract, so a Stickman Short runs without him.
- Stickman + Goli stays long only (a Short asked for it is a 3D Short). Stickman + Goli thumbnails are Goli
  thumbnails with Stickman small behind; the Stickman board thumbnail is for pure Stickman videos only.
- Fast cut (owner 2026-11-18, long): one shot per sentence, 1.5-4 s, from the real word timings.

## 3D Shorts (owner 2026-11-22: "Bingo. Now this is the direction")
- Engine: thuann-vn/claude-3d-animated-shorts (MIT), Ricks Clips style (white deadpan heads, pear bodies, noodle limbs,
  lit office/home sets, CC0 furniture), cloned at the pinned `ENGINE_COMMIT` (`shorts3d/build.py`), assets cached on
  GitHub; Chrome through the software-WebGL wrapper (`.github/actions/shorts3d-setup`). Our code hooks in at its skit
  branch (`assets/shorts3d/hook.py`, refuses if that line moves); the engine's own files are never edited.
- A Short in the Stickman style goes here (`production._shorts3d_short`). NOTHING IS PRE-DECIDED (owner 2026-11-23:
  "you don't know what's coming with another script, but you are prepared to make whatever will come", like Inkee).
  No sets, no prop lists, no topic examples in what Sol is told. Sol writes ONE open storyboard as data
  (`shorts3d/board.py`): the place from the script (ground, sky, walls, size), every thing the words name (name, search
  words, real height, spot, and its own 3D parts), the people (role, start, look), what each DOES on which word (walk,
  run, hold, pick up, give, throw, kick, push, pull, sit, lie, fall, jump, ride, point ... with any target), what the
  things do (move along a path, spin, shake, bend, break, fall, appear, vanish, glow, smoke, fire, change their words)
  and the shots (frame, angle, lens, move, the engine's own shot plan). Only the body moves are a vocabulary; every noun
  and place is free text. Strict schema, capped at $0.86 (output limit; the provider's re-ask off), saved at once in R2
  under a fingerprint of the recording (`shorts3d-board-v2/`), never paid twice. Everything wrong is repaired for free
  (`board.repair`). Things are found by name in free CC0 libraries on the render machine (Poly Haven's catalogue,
  Kenney's 3D kits; only when the thing's own noun matches) or built from their parts (`shorts3d/things.py`), never
  dropped. One generic scene builds any storyboard (`assets/shorts3d/board.js`); travelling subjects are followed by
  the camera. Trials are free: a storyboard for a trial is written by hand with the same instructions, never paid.
- The director (`assets/shorts3d/director.js`, owner: "heads and bodies well contained... nothing cropped and nothing
  crashing"): each shot frames its `who` inside the phone crop (130/160/230 px) and every 0.1 s checks: anyone who
  shows is whole; no head under the captions; no face hidden; heads never overlap; words in the set (TV) never cut
  or behind a head; a head never touches the TV; the camera never inside walls, props or people; nobody through
  furniture. Failures are repaired for free (step back, orbit, rise/drop, lens); a shot it cannot repair stops the
  render with its reasons. People behind a desk are framed from the desk top up (owner: "zoom a little").
- Render: `shorts3d-render.yml` (director check, then one browser per machine across `parts` machines: several
  browsers on one machine were slower than one; then join). Production hands over through R2 and waits
  (`shorts3d/remote.py`); captions ("short3d": 2 words, lower third), the voice levelled only, Discipline Finishes
  as one steady bed (`build.finish`). Trials: `shorts3d.yml` (scene trials), `shorts3d-selftest.yml` (the production
  handoff with a hand-written storyboard, free).
- First 3D Shorts upload PRIVATE with no Reels until the owner approves the engine (`config/edit-engine.json`
  shorts3d.hold_private).
- Scripts for Shorts follow the Ricks Clips formula (`engine/story.py` short shape): odd act as fact, context with
  one number, a doubter's line, a stubborn reply, early evidence for the doubters, the turn, "You see," + one number +
  one everyday comparison, payoff on the doubter, last line cut to loop. Length stays 45-75 s.

## No collision (owner 2026-11-17: "I don't want collision in anything")
- Recipe scenes (`edit/recipes.py`, `assets/recipes/player.html`): every word on screen is measured on 4 moments,
  overlay text and 3D text planes (trimmed to their letters); touching or leaving the frame sends the scene back.
  Words painted on a texture (silkscreen, glass marks) may not touch on the same surface; Blueprint's line lettering
  (STROKEFONT, `assets/recipes/strokefont.js`) is registered by the scene with K.words and measured too. 3D words may
  pass the frame edge while the camera travels (the recipes' own camera language), never on the held last frame.
- 3D Shorts: the director (see "3D Shorts").
- Stickman long (`stickman/collide.py`): real frames of every shot; text touching text, leaving the frame or over a
  head goes back to Sol, and whatever still collides is taken out of the story. Goli never covers the panel.
- All six Futurepedia prompts are recipes (owner 2026-11-17): xray, layers, white, circuit, glass, blueprint.

## Styles in Goli videos: cost in cents (owner 2026-11-17)
- Free (no model call, the storyboard fills them): Layer Stack, Circuit City, Glass and Light (the reference's own
  "content (change this block for a new topic)" block, `recipes.fill_code`, timing stretched to the beat) and
  Puppets: beats about people who are not one named real person as ONE ReachMora shot (`stickman/scene.py`, the
  kit's story format, drawn by its own engine). A free scene that fails its check is not retried: its stand-in shows.
- White Model is a free kit of pieces (owner 2026-11-18, `assets/recipes/kits/white-kit.js`): the recipe's own whites,
  daylight, accent conduits, labels and crane camera, with 35 pieces (buildings, nature, roads, vehicles, people,
  power); the storyboard names the stops and extras, `recipes.white_layout` places them (no overlaps).
- ANY object (owner 2026-11-18: "every script has different objects"): no fixed object lists. The storyboard writes
  the real thing as named parts in the engine's 3D part format ("name: box|cyl|sphere|cone x y z w d h [rx90] [gold]",
  `recipes.object_parts` reads, checks and fits it). X-Ray and Blueprint draw only from parts (any object inside, any
  structure built); White Model's 35 pieces take a "custom" piece from parts for anything else; Circuit City draws a
  part it does not know as a chip with its name. Never a look-alike swap, never a dropped thing.
- No paid styles left (2026-11-18). The paid path stays for later ones: only when switched on for the video in Studio,
  each up to the count he sets (`spec.looks = {free: [...], paid: {key: n}}`, `editor.looks_for`); scheduled
  automatic runs never switch paid ones on. Real people stay real photo cards, never puppets.

## Checks
`python3 -m pytest -q` must pass before every push (672 tests as of 2026-11-23).
