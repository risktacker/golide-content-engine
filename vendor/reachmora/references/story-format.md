# story.json reference

`story.json` is the whole video. The engine turns it into frames, timed to the voiceover. You never write drawing code for a normal video: you pick shot kinds and fill in their fields.

```json
{
  "title": "The Man Who Sold the Eiffel Tower",
  "mood": "mystery",
  "cast": { "victor": {"skin": "tan", "outfit": "suit", "color": "#3B4660", "hair": "slick", "moustache": true, "hat": "fedora"} },
  "shots": [ {"kind": "skyline", "s": [0, 1], "time": "night", "tag": "PARIS · 1925"}, ... ]
}
```

- `title` names the output file. `mood` picks the music: `mystery` (sneaky, swing, money and crime stories), `upbeat` (pop, self-improvement and business wins), `dramatic` (slow and heavy, rise and fall, disasters), `calm` (soft, life lessons and psychology), `tense` (pulsing, scams, survival, countdowns).
- `s` is the sentence range a shot covers, using the numbers printed by `python3 -m engine sentences <P>`: `[4]` is one sentence, `[4, 6]` covers 4, 5 and 6. Shots must cover every sentence once, in order. The shot starts just before its first sentence and ends just before the next shot's.
- A shot **without** `s` is silent. It inserts a pause of `hold` seconds (default 1.6) into the timeline. Use this only for chapter cards (`title`), at most one every 2-3 minutes. The voice is shifted, never cut.

## Cues: `at`

Anything that happens mid-shot has an `at`:
- a **word or short phrase** from the shot's own sentences: `"at": "fortune"` fires when that word is spoken (exact match first, then a prefix match).
- a **fraction** of the shot: `"at": 0.5`.
- **seconds** after the shot start: `"at": "+1.2"`.

Use words wherever you can: that is what makes the picture land on the voice. `plan` warns when a word is not found.

## Cast

Every character is an original round-head puppet. Real people are generic puppets plus a name tag (`lower_third`), never a likeness.

| key | values |
|---|---|
| `skin` | `light`, `fair`, `tan`, `olive`, `brown`, `dark` or a hex colour |
| `outfit` | `suit`, `hoodie`, `tshirt`, `sweater`, `dress` |
| `color` | main clothing colour (hex) |
| `shirt`, `tie` | suit shirt and tie colours; `"tie": "none"` for an open collar; `bowtie: true` |
| `hair` | `short`, `slick`, `bun`, `long`, `curly`, `bald`, `none` |
| `hair_col` | hex |
| `glasses`, `moustache`, `beard` | true/false |
| `hat` | `fedora`, `cap` (with `hat_col`) |

Give every main character a distinct silhouette and colour (hair shape plus outfit colour), so they read at a glance in wide shots. 2-4 recurring characters is the sweet spot. Kids use `"s": 0.75-0.85` in `chars`.

## Characters inside a shot (`chars`, `who`)

```json
{"id": "victor", "x": 1000, "s": 1.0, "face": -0.7, "emotion": "smug", "pose": "present",
 "talk": true, "enter": "left", "beats": [{"at": "sold", "pose": "celebrate", "emotion": "excited"}]}
```
- `x` is the feet position (0-1920), `s` the scale (1 = wide shot), `face` runs from -1 (looking left) to 1 (looking right).
- **emotion**: `neutral calm happy smile smug shocked nervous sad angry thinking excited tired confident worried embarrassed greedy`. Sweat drops and sparkles come with the emotion.
- **pose**: `idle present present_left explain think pockets celebrate shrug point hips hold tiphat wave arms_crossed facepalm stressed push`.
- **beats** change pose, emotion or face on a cue, with a snap-and-overshoot plus squash. Two or three beats per shot keep characters alive. Beats can also sit at shot level with `"who"`.
- **talk**: `true` makes the mouth follow the voiceover during the shot's sentences; a list of sentence numbers limits it to those. Use it for dialogue lines and for a character "telling" the story to camera. Narration over a character usually looks better without it.
- `enter` / `exit`: `left` or `right` walks the character in or out. `walk: [x0, x1]` walks across the whole shot.
- Characters always idle-bob, blink and squash on cuts. You don't need to animate that.

## Shared fields (any shot)

| field | what it does |
|---|---|
| `labels` | `[{"text": "A FORTUNE", "at": "fortune", "color": "lime", "x": 1420, "y": 330, "size": 120, "font": "marker"}]`: hand-lettered pop-in words. Colours: `lime cream red gold sky pink white green orange` or hex. Positions default to the empty side of frame. Up to 3 per shot, 1-4 words each. |
| `stamp` | `{"text": "SOLD", "at": "sold", "x": .., "y": .., "color": "red", "size": 130}`: rubber stamp slam with camera shake and a thud. At most one per shot. |
| `tag` | `"PARIS · 1925"`: location/time tag, lower left, on the first shot in a new place or era. |
| `lower_third` | `{"name": "VICTOR LUSTIG", "sub": "CON MAN", "at": "lustig"}`: name card, the first time a person appears. |
| `props` | `[{"icon": "moneybag", "x": 1500, "y": 760, "s": 0.6, "at": "cash"}]`: world props that pop in (icons below). |
| `bubble` | `{"who": "sam", "text": "What if...?", "icon": "bulb", "at": "idea", "thought": true}`: a thought or speech bubble. |
| `time` | `night` (default, moody), `dusk`, `day`. |
| `cam` | `{"zoom": [1.0, 1.12], "focus": [[960, 545], [1100, 500]]}`: override the default slow push-in. Avoid `rot` on world shots: a rotated full-frame draw is about 3x slower to render (table shots drift-rotate only the papers, which is cheap). |
| `whip` | `true`/`false`: force or stop a whip-pan out of this shot. By default whips happen only on a change of place between world shots. |
| `sfx` | `[{"name": "ding", "at": "idea"}]`: extra sounds: `pop thud whoosh tick shutter scribble boom ding paper step sting`. |
| `polaroid` | `{"at": "twice", "who": "victor", "caption": "SOLD IT... TWICE"}`: the ending. Camera flash, frame freezes into a tilted polaroid, red ring around the character, handwritten payoff. Put it on the last shot, cued 1-2 s before the end. |

## Shot kinds

### `wide`: a set with full-body characters
`set`: `office` (`era`: `modern`/`old`, `wall`, `calendar: "MAY 1925"`), `home` (living room, `wall`), `street` (`shop: "CAFE"`, `awning`), `board`, `void`.
`wall` colours: `green blue plum teal sand grey cream brick`. 1-3 characters (default positions spread out). `dialogue` is an alias.

### `closeup`: one character, big, over the blurred set
`who`, `side` (`left`/`right`), `set`, `time`, `emotion`, `pose`, `beats`, `talk`, `bubble`, `labels` (they go on the open side). Use it for reactions, a line of dialogue, the "you" moments, and after big claims.

### `walk`: a character walks across a set (default `street`)
`chars` with no `x`; they walk from left to right unless you give `walk: [x0, x1]`. Footsteps come automatically. Use it for transitions in time ("one month later"), journeys and endings.

### `skyline`: establishing city shot
`time`, `tag`. Use it for the first shot in a city or a time jump.

### `crowd`: many small people
`count` (9-30), `emotion`, `highlight` (cast id, ringed at `at`), `set` (`void` default, or `street`). Use it for "millions of people", "most people", "everyone".

### `table`: top-down desk with documents sliding in
`items` (1-3): `{"type": "newspaper", "title": "THE DAILY", "text": "HEADLINE", "ring_at": "word", "at": "word", "stamp": {"text": "FAKE", "at": "word"}}`.
Types: `newspaper`, `letter` (`title`, `text`), `contract`, `receipt` (`rows: [["Rent", "$1,200"], ...]`, `text` = total), `photo` (`text` caption), `cash` (`text`), `phone` (`messages: ["...", "..."]`). `hand`: cast id whose sleeve pushes the first item. This is the best shot for evidence, documents, bank balances and messages.

### `map`: dotted route between places
`places: [{"name": "PARIS", "x": 520, "y": 640}, {"name": "VIENNA"}]` (positions auto-spread if omitted), `vehicle`: `train plane ship car`, `at` starts the route.

### `chart`: chalkboard or whiteboard chart
`board`: `chalk`/`white`. `chart`: `{"type": "bar" | "line", "values": [..], "labels": [..], "title": "..", "unit": "$", "suffix": "%", "highlight": 1, "trend": "down", "show_values": true, "at": "word"}`. `who` adds a presenter pointing at it. Use real numbers or no numbers (`show_values: false`). Never invent data.

### `counter`: a big number counting up
`value: {"from": 0, "to": 244000, "prefix": "$", "suffix": "", "at": "word", "short": false}`, `caption`, `icon` (left), `compare: {"text": "THAT'S 6 YEARS OF RENT", "icon": "house", "at": "word"}`. Every big number in the script gets a counter or a label, ideally with an everyday comparison.

### `icon`: 1-3 big icons popping in on paper
`icons: [{"name": "bulb", "label": "THE IDEA", "at": "idea"}]`, optional small `chars` (one character at the side). Icons: `bulb brain clock moneybag coins house trophy heart lock hourglass warning laptop gift book phone chart_up chart_down calendar (top, text) target car money marshmallow shopping (text)`. Icons that take text (`calendar`, `laptop`, `book`, `shopping`) take `text` and `top`.

### `list`: numbered point for listicles
`number`, `text` (2-6 words), `who`, `emotion`, `badge` colour. One per list item, then show the item with other kinds.

### `versus`: split screen, A vs B
`left` / `right`: `{"who": "rex", "title": "SPENDS IT ALL", "emotion": "happy", "pose": "..", "at": "spends"}`, `colors: ["#BFD9F2", "#F6C7B6"]`. This shot is the workhorse for psychology and self-improvement comparisons.

### `title`: black card with typed handwriting
Spoken (`s` given): the words type in with the voice, which suits punchlines like "Here's the strange part." Silent (no `s`): a chapter card, with `text` plus `sub` (for example "CHAPTER TWO"). The music cuts out under it with a low boom.

## Pacing rules that make long videos watchable

- **Shot length:** 3-8 s. 3 min is about 30-40 shots, 5 min 50-65, 10 min 100-130, 15 min 150-190. If a sentence runs longer than about 9 s, give it two beats or labels.
- **Never more than two of the same kind in a row.** Rotate world shots (wide, closeup, walk) with graphics (icon, counter, chart, table, versus, list).
- **Every number on screen.** Use a counter, chart or label for each figure.
- **A reaction closeup after every big claim or twist.**
- **Re-hook moments** (spoken titles, stamps, versus) every 60-90 s.
- **Chapters:** a silent `title` card every 2-3 minutes in 10-15 min videos (3-6 in total), 1-2 in 5 min videos, 0-1 in 3 min videos.
- **Places:** `tag` the first shot in each new place or era. Give a `lower_third` the first time each person appears.
- **End** on a `polaroid` shot whose caption is the payoff line.
