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
  instead of cutting to word fragments. His recording is the script: changed words rebuild lines, captions and
  blocks from what he said (`owner_changes.reading_from_audio`).
- Glass 3D (`assets/edit/g3d/glass3d.js`, three.js in the video): laptop, phone, server, chip, battery in clear glass
  with lit edges, one gold part with a callout line to its label, two other parts named. Max 4 per long video, 2 per
  Short, never two in a row. Goli faces the content (mirrored on the right).

## Shorts (owner 2026-11-13, after the broken USB Short)
- Script: 150-185 words (60-75 s), its own method (`engine/story.py` short shape): one direction, a hook that puts the
  viewer in someone's shoes, then a chain where each step causes the next, a turn, a payoff tied to the first line.
  Model: `8e4TYDVZTwk` (read for every Short, `config/model-videos.txt` "always"). No "..." in a Short; long at most 1;
  "..." is never shown on screen. One read; voice parts must add up to the script.
- Sound: no pops or ticks; whoosh on cuts, an impact only on a big number (`edit/render.py` sound_plan).
- Music: Discipline Finishes under every Short until 2026-12-13 (`short_signature`), one steady bed, no dips.
- Frame: content stays inside the phone crop (130 px left, 160 right, 230 top) at every moment (`layout.keep_inside`).
- Pace: no picture under 1.0 s (Short) / 1.5 s (long); 1 metaphor per Short, 3 per long; a strong transition
  (zoom, flash, iris, whip) at most once in three cuts, the rest glide or cut.

## Stickman (owner 2026-11-17): the third visual style, next to Inkee and Goli
- Made with the kits' own packages, imported not copied: long videos with ReachMora (`vendor/reachmora`,
  `stickman/longform.py`), Shorts with the cartoon-short-kit (`vendor/cartoon-short-kit`, `stickman/short.py`).
  The kit's rules win for these videos (its music, SFX, captions, chapter cards); our Short music rule doesn't apply.
- The characters are actors: the narrator speaks, nobody's mouth talks. Real people are generic puppets, no likeness.
- Our engine feeds only the voice, our word timings and research; Sol writes story.json (long) or the world, story,
  cast and cue table (Short) from the kit's own documents. Checks (the kit's plan check / our look check) go back to
  the writer once; a Short that fails twice is made in Goli.
- Stickman + Goli (owner 2026-11-17, `stickman/goli_layer.py`): a fourth choice in Studio, per video. The finished
  Stickman video plays in a framed panel; Goli stands full-body beside it ("beside" place in `edit/compose.py`),
  facing it, mouth on the voice, reactions on the story's events (numbers -> point, shock lines -> shock, lists and
  versus -> explain, payoff -> both hands up), at least 2.2 s apart. The video's own sound is kept untouched.
  Long videos only (owner 2026-11-17): on a Short Goli would distract, so a Stickman Short runs without him.

## No collision (owner 2026-11-17: "I don't want collision in anything")
- Recipe scenes (`edit/recipes.py`, `assets/recipes/player.html`): every word on screen is measured on 4 moments,
  overlay text and 3D text planes (trimmed to their letters); touching or leaving the frame sends the scene back.
  Words painted on a texture (silkscreen, glass marks) may not touch on the same surface; Blueprint's line lettering
  (STROKEFONT, `assets/recipes/strokefont.js`) is registered by the scene with K.words and measured too. 3D words may
  pass the frame edge while the camera travels (the recipes' own camera language), never on the held last frame.
- Stickman long (`stickman/collide.py`): real frames of every shot; text touching text, leaving the frame or over a
  head goes back to Sol, and whatever still collides is taken out of the story. Goli never covers the panel.
- All six Futurepedia prompts are recipes (owner 2026-11-17): xray, layers, white, circuit, glass, blueprint.
- Recipes ship OFF (`config/edit-engine.json` recipes.enabled): no Sol spend without the owner's go.

## Checks
`python3 -m pytest -q` must pass before every push (467 tests as of 2026-11-06).
