# GOLIDE Content Engine: standing instructions

Owner: Esiah (Lusaka, UTC+2). Direct, no sugar-coating. Studio: studio.golidee.com
(Cloudflare Worker `worker/index.js`, D1, R2). Engine: Python on GitHub Actions
(`production-scheduler.yml`), daily Short and long video.

## Owner's rules (always)
- Talk before code on anything that costs money or changes visuals; state costs first. "Approved" or "Perfect" = go.
- Show a preview (still frames / contact sheet) before pushing visual changes. Not a full video unless asked.
- Never touch the music videos. Never use other people's faces. Licence-clear assets only.
- Thumbnails (owner 2026-11-10): real logos of the products and apps in the story are used; no owner avatar
  (only when he is in the video); real objects, never generative look-alikes.
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
  Eleven v3 (owner 2026-11-13): one request per paragraph (each its own tone); the hook of a long video (its opening
  2-3 sentences) is read 3 times (Natural + 2x Creative) and the liveliest believable take is kept (~10k chars/month).
  The script is written to be performed (questions, reactions, "...", one CAPS word, v3 tags) and checked before voice.
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
  about 1 in 6 scenes, never the same twice in a video.
- Glass 3D (`assets/edit/g3d/glass3d.js`, three.js in the video): laptop, phone, server, chip, battery in clear glass
  with lit edges, one gold part with a callout line to its label, two other parts named. Max 2 per long video, 1 per
  Short, never two in a row. Goli faces the content (mirrored on the right).

## Shorts (owner 2026-11-13, after the broken USB Short)
- Script: 150-185 words (60-75 s), its own method (`engine/story.py` short shape): one direction, a hook that puts the
  viewer in someone's shoes, then a chain where each step causes the next, a turn, a payoff tied to the first line.
  Model: `8e4TYDVZTwk` (read for every Short, `config/model-videos.txt` "always"). No "..." in a Short; long at most 2;
  "..." is never shown on screen. Read once (no hook takes); voice parts must add up to the script.
- Sound: no pops or ticks; whoosh on cuts, an impact only on a big number (`edit/render.py` sound_plan).
- Music: Discipline Finishes under every Short until 2026-12-13 (`short_signature`), one steady bed, no dips.
- Frame: content stays inside the phone crop (130 px left, 160 right, 230 top) at every moment (`layout.keep_inside`).
- Pace: no picture under 1.0 s (Short) / 1.5 s (long); 1 metaphor per Short, 3 per long; a strong transition
  (zoom, flash, iris, whip) at most once in three cuts, the rest glide or cut.

## Checks
`python3 -m pytest -q` must pass before every push (467 tests as of 2026-11-06).
