"""The editor (production plan step 4): one model call turns the day's words into an edit list.

The model is the editor. It sees every spoken line with its time, the real pages captured for the
story (and the exact phrases found on each), and the house rules (skills/golide-edit/SKILL.md, in
short). It answers with scenes over line ranges. Code then does what code is good at: exact times
from the owner's recording, spoken-word times for every move, Goli's pose and mouth timing, and
checks that every reference it was given is real.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

POSES = ["talk", "explain", "point", "point_up", "point_left", "shock", "think", "thumbs_up", "shrug", "wave"]
# 2026-11-18 (owner: "draw what is being said, no text blocks except those 3"): no compare, steps, checklist,
# timeline, flow or words scenes; text only as a quote, a prompt to copy or the key number (stat)
TYPES = ["studio", "source", "terminal", "metaphor", "object3d", "recipe", "puppets", "walkthrough", "photo", "stat",
         "prompt", "quote", "logos", "icon", "chapter", "follow"]
TEXT_CARDS = {"kinetic_title", "comparison", "steps", "checklist", "timeline", "flow"}

OBJECTS3D = ("laptop", "phone", "server", "chip", "battery")
# 2026-11-17 (owner): Futurepedia style recipes, a new scene written for the beat (edit/recipes.py)
RECIPE_KEYS = ("xray", "layers", "white", "circuit", "glass", "blueprint")
# 2026-11-17 (owner): cost to cents. Free styles (the storyboard fills the reference's content block, no model call)
# and the free puppet scenes are on unless switched off for the video; paid styles (a model writes the scene) only
# when switched on for the video, each up to its count. Scheduled automatic runs use the free ones only.
FREE_LOOKS = ("layers", "circuit", "glass", "white", "xray", "blueprint", "puppets")
PAID_LOOKS: tuple[str, ...] = ()   # 2026-11-18: every style is a free kit now; the paid path stays for later ones


# 2026-11-18: Layer Stack's labels sit beside a long-lens stack: in the Short's square frame they are too small to
# read, so it is a long-video style until it is reframed for the square
NOT_IN_SHORTS = ("layers",)


def looks_for(spec_looks: Any, fmt: str | None = None) -> dict[str, Any]:
    """The styles a video may use, from its Studio switches ({"free": [...], "paid": {"blueprint": 1}}); none given
    means every free one and no paid one. A Short leaves out the styles that do not read in its frame."""
    got = spec_looks if isinstance(spec_looks, dict) else {}
    free = got.get("free")
    free = [k for k in (free if isinstance(free, list) else FREE_LOOKS) if k in FREE_LOOKS
            and not (fmt == "short" and k in NOT_IN_SHORTS)]
    paid = {k: max(0, int(v)) for k, v in (got.get("paid") or {}).items()
            if k in PAID_LOOKS and isinstance(v, (int, float)) and int(v) > 0}
    return {"free": free, "paid": paid}


# 2026-11-17 (owner): animated 3D blocks; any object, not only the five presets (built from parts3d)
MOVES3D = ("own", "explode", "assemble", "lift", "rise", "spin")
# Futurepedia 3D atlas looks (owner's picks), one per video: Glass and Light, X-Ray, Circuit City, White Model,
# Layer Stack
LOOKS3D = ("glass", "xray", "circuit", "white", "layers")
LOOK_WORDS = {
    "xray": ("chip", "gpu", "nvidia", "transistor", "semiconductor", "inside", "hidden", "teardown", "processor", "tsmc"),
    "circuit": ("data cent", "server", "cloud", "network", "power", "grid", "energy", "infrastructure", "internet"),
    "layers": ("model", "agent", "stack", "layer", "software", "system", "architecture", "framework", "api", "llm"),
    "white": ("robot", "factory", "manufactur", "design", "prototype", "humanoid", "build"),
    "glass": ("iphone", "phone", "apple", "laptop", "launch", "device", "display", "gadget", "wearable", "glasses"),
}


def pick_look(text: str, recent: list[str]) -> str:
    """One 3D look per video: the one whose words the story uses most, never the look of the last video."""
    low = str(text).lower()
    score = {k: sum(low.count(w) for w in words) for k, words in LOOK_WORDS.items()}
    order = sorted(LOOKS3D, key=lambda k: (-score[k], LOOKS3D.index(k)))
    last = recent[:1]
    return next(k for k in order if k not in last)
METAPHORS = ("scales", "unlock", "magnify", "funnel", "stack", "gauge", "transform", "iceberg", "cycle")
_str = {"type": "string"}
_nstr = {"type": ["string", "null"]}
_nnum = {"type": ["number", "null"]}

SCENE = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "type": {"type": "string", "enum": TYPES},
        "first_line": {"type": "integer"}, "last_line": {"type": "integer"},
        "goli_corner": {"type": "boolean"},
        "poses": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
            "pose": {"type": "string", "enum": POSES}, "word": _str}, "required": ["pose", "word"]}},
        "screen_words": _nstr, "punch": _nstr,
        "source": {"type": ["integer", "null"]}, "phrase": {"type": ["integer", "null"]},
        "callout": _nstr, "callout_sub": _nstr, "edge": {"type": ["string", "null"], "enum": ["glass", "fade", None]},
        "value": _nnum, "prefix": _nstr, "suffix": _nstr, "label": _nstr,
        "quote": _nstr, "quote_by": _nstr,
        "left": _nstr, "right": _nstr,
        "rows": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
            "label": _str, "a": _str, "b": _str, "winner": {"type": "string", "enum": ["left", "right", "none"]}},
            "required": ["label", "a", "b", "winner"]}},
        "items": {"type": "array", "items": _str},
        "shots": {"type": "array", "items": {"type": "integer"}},
        "points": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
            "when": _str, "what": _str}, "required": ["when", "what"]}},
        "brands": {"type": "array", "items": _str},
        "object3d": _nstr,
        "move3d": {"type": ["string", "null"], "enum": list(MOVES3D) + [None]},
        "recipe": {"type": ["string", "null"], "enum": list(RECIPE_KEYS) + [None]},
        "recipe_brief": _nstr,
        "fill": _nstr, "puppet": _nstr,
        "parts3d": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
            "shape": {"type": "string", "enum": ["box", "cyl", "sphere"]}, "x": {"type": "number"},
            "y": {"type": "number"}, "z": {"type": "number"}, "w": {"type": "number"}, "d": {"type": "number"},
            "h": {"type": "number"}, "gold": {"type": "boolean"}, "mover": {"type": "boolean"}, "name": _str},
            "required": ["shape", "x", "y", "z", "w", "d", "h", "gold", "mover", "name"]}},
        "metaphor": {"type": ["string", "null"], "enum": ["scales", "unlock", "magnify", "funnel", "stack", "gauge",
                                                          "transform", "iceberg", "cycle", None]},
    },
    "required": ["type", "first_line", "last_line", "goli_corner", "poses", "screen_words", "punch", "source", "phrase",
                 "callout", "callout_sub", "edge", "value", "prefix", "suffix", "label", "quote", "quote_by", "left",
                 "right", "rows", "items", "shots", "points", "brands", "metaphor", "object3d", "move3d", "parts3d", "recipe", "recipe_brief", "fill", "puppet"],
}
# owner 2026-11-25 ("storyboards per statement", taken from the Stickman engine): the editor first writes a PICTURE
# PLAN, one row per sentence (what it names, what real thing proves it, which block shows it), then the scenes follow
# it beat by beat. The plan comes first in the answer, so the scenes are built from it.
PLAN_ROW = {"type": "object", "additionalProperties": False,
            "properties": {"first_line": {"type": "integer"}, "last_line": {"type": "integer"},
                           "named": {"type": "string"}, "proof": {"type": "string"}, "block": {"type": "string"}},
            "required": ["first_line", "last_line", "named", "proof", "block"]}
EDIT_SCHEMA = {"type": "object", "additionalProperties": False,
               "properties": {"plan": {"type": "array", "items": PLAN_ROW}, "scenes": {"type": "array", "items": SCENE}},
               "required": ["plan", "scenes"]}


PLAN_TEXT = """PICTURE PLAN FIRST (owner 2026-11-25: "storyboards per statement"): before any scene, write `plan`, ONE row per
sentence of the narration, in order, covering every beat once (first_line/last_line = the sentence's first and last
beat). named = the thing the sentence names or is about, in its own words (a product, a page, a number, a person,
an action); proof = the real thing on screen that shows it (that product's captured page or logo, the number, the
command run, the person's photo, a puppet doing the action); block = the scene type that shows it. Then build the
scenes FROM the plan: every scene inside a sentence shows that sentence's named thing or its proof, a new picture on
every beat of a long sentence, never a picture of something the sentence does not say.
"""


def instructions(fmt: str, looks: dict[str, Any] | None = None, lessons: list[str] | None = None) -> str:
    """The editor's instructions; `lessons` are the doctor's rules from earlier videos (edit/lessons.py)."""
    learned = ("\nLESSONS FROM EARLIER VIDEOS (the doctor had to fix these after the render; do not make them again):\n"
               + "\n".join(f"- {x}" for x in lessons) + "\n") if lessons else ""
    return PLAN_TEXT + learned + _instructions(fmt, looks)


def _instructions(fmt: str, looks: dict[str, Any] | None = None) -> str:
    short = fmt == "short"
    looks = looks or looks_for(None)
    allowed = [k for k in RECIPE_KEYS if k in looks["free"] or k in looks["paid"]]
    puppets = "puppets" in looks["free"]
    return _looks_text(allowed, looks["paid"], puppets) + f"""You are the editor of GOLIDE, a faceless AI-explainer channel. Its host is Goli, an original cartoon
pangolin in a GOLIDE hoodie who talks with the owner's voice. You cut a {"vertical Short" if short else "long video"} the way
the best channels in the niche do: fast, real proof on screen, and the picture ALWAYS shows what is being said
at that moment.

{"The narration is cut into BEATS of about 2 seconds: the Short is fast. Give every beat its own picture that shows exactly what that beat says. A scene covers ONE beat (first_line = last_line = the beat number); only a studio scene may cover 2." if short else "The narration is cut into BEATS of about 3 seconds: fast, like the best channels (owner 2026-11-18). Give every beat its own picture that shows exactly what that beat says. A scene covers 1 beat; only a page the camera walks through, a walkthrough or a typed prompt may cover 2."}
Scenes cover every beat exactly once, in order, no gaps: scene N+1's first_line = scene N's last_line + 1.

You also get CAPTURED PAGES: the real web pages behind the story, each cut into SHOTS (its headline, the exact
facts found on it, and every paragraph, list item and table cell with its text). A shot is a place on the page the
camera zooms to. Match beats to shots by meaning: when a beat states a fact, pick the shot whose text says it.
Never use the same shot twice in the whole video. {"On a Short, screenshots are the proof, not the whole show: at most one beat in three is a source scene, never two source scenes in a row; the rest are the drawn styles (recipes), 3D objects, metaphors, photos and logos." if short else "On a long video the pages carry the explanation: walk through a page across its shots, but put another kind of picture between pages."}

DRAW WHAT IS SAID (owner 2026-11-18, no two ways): every beat is a moving PICTURE of what its words say, made with
the graphics below: a recipe style first (X-Ray, Layer Stack, White Model, Circuit City, Glass and Light, Blueprint,
Puppets), a 3D object, a metaphor, a real photo, a real page, a real run, logos, Goli. Something that moves, never a
still card. NO TEXT CARDS: text appears only as a real quote (quote), a prompt the viewer copies (prompt) or the key
number (stat, at most 1 in a Short and 1 per minute of a long video). There are no compare, steps, checklist,
timeline, flow or words scenes any more: draw them (a comparison is scales or two objects side by side, steps are a
blueprint or a white model, a flow is a white model or a circuit city, a timeline is layers or a white model).

Scene types (fill only the fields the type uses; null or [] for the rest):
- source: a captured page, zoomed to one shot (source = page index, phrase = shot index). callout = the fact in at
  most 4 words (e.g. "$40") or null, callout_sub = what it is (3 to 6 words), edge glass or fade.
- photo: a real picture (source = page index; pages marked "photo: yes" or PICTURE): a person, a product, a place the
  words name. Owner 2026-11-17: when a line names a person or a product and a picture of it exists, show it.
- stat: one number that matters (value as a number, prefix like "$", suffix like "%" or "x", label 2 to 5 words).
- object3d: the words talk about a real thing or what is inside it. object3d = its name. Five are built in:
  laptop, phone, server (a data centre rack), chip (a GPU), battery; parts3d = [] for those. ANY other real thing
  (a robot, a car, a drone, a headset, a power plant, a house...): build it from 3 to 12 simple parts in parts3d
  (shape box/cyl/sphere, x y z = where its base sits, w d h = its size, about 0.1 to 3 units, z up; name = what the
  part is; gold = true on the ONE part the story is about; mover = true on a part that slides out). move3d = how it
  moves on punch, the spoken word: own (the built-in move: lid opens, a server slides out, the chip lid lifts, the
  phone's layers part, cells rise), explode (it comes apart into its parts: "inside", "made of"), assemble (the
  parts come together: "built", "combined"), lift (the gold part rises out: "the one that matters"), rise (it
  builds up part by part: "grows", "stacks up"), spin (it turns all the way round: "every side"). The part the
  story is about turns gold with a line to a label: label = what it is in this story, max 5 words ("Your rented
  GPU"); two other parts get their own name. Never two in a row; only on a beat whose words NAME the thing (laptop,
  computer, phone, server, rack, chip, GPU, battery, or a built thing's own name), and the same object at most twice
  in a video (owner 2026-11-25: a laptop for lines about names, Git and folders is a repeated block).
- recipe: a FILM-QUALITY 3D scene for this beat in a named style: the MAIN picture of the video, used for every
  beat whose words name a thing, a system, a place, a stack, a plan, an amount or what is inside something (owner
  2026-11-18: all of them are required, draw what is being said). They are the slowest pictures to draw, so a video
  has at most {"10" if short else "24"} recipe scenes: put them on the beats that need them most and draw the rest with
  photos, pages, real runs, 3D objects, metaphors, logos and puppets. DRAW THE SUBJECT (owner 2026-11-19, after a
  car video with no car in it): the real things the video is about must be seen, again and again: their photos (pages
  marked PICTURE) and recipes/3D objects BUILT AS THOSE THINGS from their real parts (a car: body, wheels, battery
  pack, motor, seats, screen; a factory: halls, lines, robots, trucks; a battery: cells, modules, case). Never an
  abstract stack of labelled cards for a real object. A flag only when the line is about the country itself.
  recipe = which style:
  xray = what is INSIDE a real thing and how it works (a chip, a battery, a phone, an engine, a data-centre rack):
  up to three inner parts, each lit and named in turn, with a simple flow (heat, air, current, data, force) acting
  on them. layers = anything BUILT IN LAYERS (a tech stack, what an AI product is made of, how a request travels
  through a system): 3-5 layers top to bottom, each with a simple diagram, a name and a short line, and a pulse
  showing the order things happen. white = how something FLOWS THROUGH A SYSTEM (energy, water, money, data,
  people): a white architect's model of the system, one accent travelling its path in order, a numbered label at each
  stop. A PLACE where things are made, stored or run (a factory, a chip fab, a data centre, a power plant, a port, a
  campus, a city: owner 2026-11-25, the Terafab beat) is a white model of that place with what flows in and out, never
  a blueprint. circuit = a JOURNEY or PIPELINE through stages (a prompt through a chip, a payment through a network): a
  circuit board at night, each stage a landmark with its printed name, a pulse carrying the order. glass = MIXTURES,
  RATIOS AND AMOUNTS (a split of money or time, a blend, a recipe, chemistry): real glassware, amounts as levels
  against the marks, one action per beat. blueprint = a PLAN, SET-UP or HOW ONE THING IS MADE (a machine, a
  device, a part, one building's structure): a flat drawing that rises into the real object, with dimensions and 2-3 numbered pointers. recipe_brief = what the scene must show, from the words and research only (max 60 words). xray: the
  object and its real look, the 1-3 inner parts to light in order and what each does in 2-5 words, the flow, and the
  brand if there is one (its colour becomes the accent). layers: each layer top to bottom with its name (1-2 words),
  a 2-4 word line and what its little diagram shows, and what the pulse carries (a request down, the answer up).
  white/circuit: the source, then each stop in order with its name (1-2 words) and a 2-4 word line, and what travels.
  glass: each ingredient with its colour and amount (in parts or %), and the action (pour, add, shake, settle).
  blueprint: the object, its 2-3 key measurements, and 2-3 pointers (where, 2-4 words each). ALSO fill object3d (+ parts3d, move3d) as the stand-in shown if
  the scene cannot be made. Two recipe scenes in a row are fine in different styles; never the same style twice in a row.
- metaphor: the beat explains an IDEA (a trade-off, a hidden cost, a bottleneck, layers, a loop, a level, a change):
  show it as a moving picture instead of text. metaphor = one of:
  scales (two things weighed: left, right, punch = the heavier one), unlock (something now possible: label),
  magnify (what is really underneath: label = the hidden truth), funnel (many things become one: items = 2-4 inputs,
  label = the result), stack (layers of a system: items bottom to top, 2-5), gauge (a level or amount: value 0-100,
  label), transform (one thing becomes another: left = before, right = after), iceberg (the visible part and the
  hidden mass: label = what people see, items = what is hidden), cycle (a loop: items = 3-5 steps).
  punch = the spoken word it lands on. Words max 4 each, as spoken. Name the real things (the app, the model, the
  site, the data's source: "Claude", "Gmail", "Reddit posts"): the video shows their real logos and icons. When a
  word is a prompt, put the prompt's real text in quote: the prompt itself is shown typed, never the word "prompt". Use one whenever a beat explains an idea
  with a shape (owner 2026-11-17: no fixed count); never two metaphor scenes in a row, never the same metaphor
  twice in a video.
- terminal: a REAL RUN (listed under REAL RUNS) proves what the beat says (the repo, the tool, the model actually
  working): source = the run's index, phrase = the words in its output to highlight. The viewer watches the real
  commands and the real output. Use each real run once, on the beat it proves best, over 2 beats.
- walkthrough: the beat tells the viewer how to do something IN a product (open, click, set, choose, install, type)
  and a captured page is that product's own page, docs or settings: source = page index, items = 2 to 4 steps (max
  4 words each, as spoken), shots = for each step the shot on that page where its button, menu, field, setting or
  command is (prefer [control] shots: the page's own buttons, menus, fields and commands). The viewer sees the real page; the camera goes to each place, the cursor clicks it and a numbered
  badge names the step. ALWAYS prefer this over steps when such a page exists: show the real thing, not text.
- prompt: the beat says what to type or ask an AI tool: quote = the exact prompt (max 20 words, as spoken or as the
  research gives it), label = the tool's name. It is typed into a chat box on screen and sent.
- quote: a short real quote from the pages or research (quote, quote_by).
- logos: 2 to 4 real product or company names (brands) named together in the beat.
- icon: one product or company named in the beat (brands = [that name], label = what about it, max 5 words).
- words: NEVER (owner 2026-11-17: no text blocks; a words scene is dropped and the picture before holds). Text
  appears only where it IS the content: a real quote (quote), a prompt the viewer copies (prompt), the key number
  (stat). Every other beat is a picture.
- studio: Goli at his desk, his screen shows screen_words (max 5 words) with a punch word. Use it for the opening hook,
  a reaction, a question to the viewer and the payoff; at most 1 beat in 5. poses: 1 to 2, each on a word spoken in
  that beat (talk, explain, point, point_up, point_left, shock, think, thumbs_up, shrug, wave).
- chapter: the first beat of a chapter (marked CHAPTER START): label = the chapter title.
- follow: the beat marked FOLLOW: label = the reason, max 6 words.
goli_corner: true on about half of the source and photo scenes, with 1 pose on a word in that beat (point_up when
the beat points at the proof, shock for a surprising number).

Rules: the picture matches the words of its beat; real proof whenever a page shows it; NO REPETITION: never two scenes
of the same type in a row{" (no exception on a Short)" if short else ", except source after source on different shots of one page"}, never the
same words, number, logo or shot twice in the video; numbers and names exactly as spoken
or on the page, never invented; only listed page and shot numbers."""


def _looks_text(allowed: list[str], paid: dict[str, int], puppets: bool) -> str:
    """What this video may use of the styles and puppets (its Studio switches), and how to fill them."""
    out = ["STYLES FOR THIS VIDEO (Studio switches): recipe may be "
           + (", ".join(f"{k}{f' (at most {paid[k]} in the video)' if k in paid else ''}" for k in allowed) or "none: do not use recipe")
           + ". " + ("puppets may be used." if puppets else "Do not use puppets.")]
    out.append("""How to fill them:
- layers, circuit, glass, white, xray, blueprint: fill = a JSON string with the scene's content (no recipe_brief needed):
  layers: {"title": [line 1, line 2] (max 3 words each, may be ["", ""]), "layers": [3 to 5 of {"name": 1-2 words,
    "note": 2-4 words, "diagram": one of chat, steps, network, files, chips}] top to bottom}
  circuit: {"stops": 2 to 6 of {"kind", "name" 1-2 words} in the order the signal travels; kinds: port (where it
    comes in or goes out), memory, processor, chip, battery, antenna, power, sensor (any other part is drawn as a chip
    with its name)}. Code lays them out.
  white: {"stops": 2 to 6 of {"kind", "name" 1-2 words, "note" 2-4 words} in the order the thing travels,
    "extras": up to 6 kinds that set the scene, "accent": "#rrggbb" (the one colour of what flows)}; kinds: house,
    tower, bank, factory, datacenter, shop, school, hospital, tree, pine, forest, mountain, hill, lake, cloud, sun,
    rain, bridge, car, truck, bus, plane, ship, pole, turbine, solar, tower_mast, person, crowd, battery, dam
    (extras may also be road, river, train). Code lays them out. A thing the pieces do not have is
    {"kind": "custom", "name", "note", "build": PARTS} (also allowed in extras), never left out.
  PARTS = ANY object written as named parts, one string each, in the 3D part format: "name: box|cyl|sphere|cone x y z
    w d h [rx90] [ry0] [rz45] [gold]" (z up, z = the part's base, any units; parts with the same name are one part).
    Build the REAL object the script names, its real proportions (from the research when it gives sizes) and its real
    parts. DETAIL: 15 to 40 parts for the object the scene is about (fewer only for a truly simple thing). Break every
    big plain shape into what it really is: a reservoir is a water surface, its shoreline steps and the dam face, not
    one block; a car has its body, cabin, windows, lights, wheel arches and 4 wheels; a building has its floors,
    windows, entrance and roof plant. Name each part as what it is, and mark the part the line is about gold.
  xray: {"object": its name, "build": PARTS lying flat as on a scanner bed (an outer part named shell, body, case or
    chassis, the inner parts inside it), "parts": 1 to 3 of {"part": a name in build, "name" 1-2 words, "note" 2-4
    words} in the order the flow reaches them, "flow": current, data, heat, air or force, "accent": "#rrggbb"}.
  blueprint: {"title": [1-2 short lines], "build": PARTS standing on the ground (any building, structure, machine or
    set-up), "notes": 1 to 3 of {"at": a name in build, "lines": [1-2 lines of 1-2 words]}, "dims": [width, depth,
    height] as printed with units, e.g. "60 M", only when the research gives them}.
- THE REAL THING ONLY (owner 2026-11-17): a style is used only when its own objects ARE what the line names:
  circuit only for chips, boards and electronics; glass only for liquids, mixing and amounts; layers only for things
  that really are layered; white for buildings, nature, cities, roads, vehicles and what flows between them; xray for
  the inside of a real object; blueprint for plans and how a thing is built. A mountain is never shown as a chip.
- puppets (owner 2026-11-25: "I liked that for bots, but only one puppet was there... maximise them"): EVERY beat
  where someone DOES something and is not one named real person is a puppet shot: a person, the viewer ("you"), a
  team, customers, a crowd, a founder in a story, AND an AI agent or bot at work (it reads, builds, gets stuck,
  hands over, finishes): an agent is a character with skin "#9AA4B2", hair "none", outfit "tshirt",
  glasses true and a laptop prop, its label the agent's job (1-3 words). In a long video use them about once every 30 s
  (never two in a row); in a Short 1-2. puppet = a JSON string {"cast": {...}, "shot": {...}}
  in the ReachMora story format below: ONE shot of kind wide, closeup, walk, crowd, table, versus, icon, map,
  counter or chart; cast = 1-3 original characters (distinct hair and outfit colours); "at" cues are words of this
  beat; at most 2 labels of 1-3 words; no talk, no title, no lower_third, no polaroid. A real person the words name
  is a photo scene, never a puppet. ALSO set metaphor (+ its fields) as the stand-in if the shot cannot be drawn.""")
    if puppets:
        from ..stickman.longform import KIT as RM
        out.append("PUPPET SHOT FORMAT (the ReachMora kit's own reference):\n"
                   + (RM / "references" / "story-format.md").read_text(encoding="utf-8"))
    return "\n".join(out) + "\n\n"


HOOK_MAX = 40.0


def hook_ends(lines: list[Any], fmt: str) -> float:
    """When a long video's hook (its opening paragraph, before the first chapter) ends; at most 40 s."""
    if fmt != "long" or not lines:
        return 0.0
    first = getattr(lines[0], "section", "")
    for line in lines[1:]:
        if getattr(line, "section", "") != first:
            return min(HOOK_MAX, float(line.start))
    return min(HOOK_MAX, float(lines[-1].end))


def beats(lines: list[Any], fmt: str) -> list[Any]:
    """The narration cut into beats of about 2 s (Short) or 3 s (long), at pauses and inside each line,
    so a picture can be chosen for every few words (owner 2026-11-11: what is on screen is what is said)."""
    from ..vector.align import TimedLine

    # owner 2026-11-12: the Short's pace is right. 2026-11-18 (owner: "no boring 2-5 second block, fast moves and
    # clips, that's how you engage"): long videos move fast too, a new picture about every 3 s
    target, low = (1.9, 1.1) if fmt == "short" else (3.0, 1.8)
    hook_end = hook_ends(lines, fmt)
    out: list[Any] = []
    for line in lines:
        words = list(getattr(line, "words", []) or [])
        # 2026-11-14 (owner): the hook is where people decide to stay, so a long video's opening paragraph gets more
        # pictures, but following what is said: a new picture where a sentence or a clause ends, one at a time,
        # never on a timer
        hook = fmt == "long" and line.start < hook_end
        if not words:
            out.append(TimedLine(len(out), line.text, line.emphasis, line.visual, line.label, line.section,
                                 line.start, line.end, []))
            continue
        chunk: list[Any] = []
        for k, w in enumerate(words):
            chunk.append(w)
            span = w.end - chunk[0].start
            nxt = words[k + 1] if k + 1 < len(words) else None
            pause = (nxt.start - w.end) if nxt else 9
            remaining = words[-1].end - w.end
            if hook:
                cut = nxt is None or (span >= 1.8 and remaining >= 1.8 and str(w.text)[-1:] in ",.;:?!")
            else:
                cut = nxt is None or (span >= low and remaining >= low and (span >= target or pause > 0.22 or
                                                                          str(w.text)[-1:] in ",.;:?!"))
            if cut:
                out.append(TimedLine(len(out), " ".join(x.text for x in chunk), line.emphasis, line.visual, line.label,
                                     line.section, chunk[0].start, chunk[-1].end, chunk))
                chunk = []
    return out


def shots(page: dict[str, Any]) -> list[dict[str, Any]]:
    """Every place on a captured page the camera can zoom to: the facts found, the headline, every block."""
    out = [{"kind": "fact", "text": h["phrase"], "rect": h["rects"][0]} for h in page.get("highlights") or []]
    if page.get("headline"):
        out.append({"kind": "headline", "text": str(page.get("title", ""))[:120], "rect": page["headline"]})
    out += [{"kind": "text", "text": b["text"], "rect": b["rect"]} for b in page.get("blocks") or []]
    out += [{"kind": "control", "text": c["text"], "rect": c["rect"]} for c in page.get("controls") or []]
    return out


def request(title: str, lines: list[Any], sources: list[dict[str, Any]], chapters: list[Any],
            follow: set[int], demos: list[dict[str, Any]] | None = None) -> str:
    starts = {line.index for line in lines for m in chapters if abs(float(line.start) - float(m.start)) < 0.05}
    rows = []
    for line in lines:
        mark = []
        if line.index in starts:
            mark.append("CHAPTER START")
        if line.index in follow:
            mark.append("FOLLOW")
        rows.append(f"{line.index}: [{line.start:.1f}-{line.end:.1f}s]{' (' + ', '.join(mark) + ')' if mark else ''} {line.text}")
    pages = []
    for i, page in enumerate(sources):
        if not page.get("ok"):
            continue
        if page.get("picture_only"):
            # 2026-11-17 (owner): the real picture of a person or product the story names
            pages.append(f"[{i}] PICTURE of {page.get('subject', '')} (photo only: use it as a photo scene when the "
                         f"words name {page.get('subject', '')})")
            continue
        listed = "\n".join(f"    {j} [{sh['kind']}] {sh['text']}" for j, sh in enumerate(shots(page)))
        n_photos = len(page.get("photos") or ([page["photo"]] if page.get("photo") else []))
        pages.append(f"[{i}] {page.get('title', '')[:90]} ({_domain(page.get('url', ''))})"
                     f"{f' photo: yes ({n_photos} pictures)' if n_photos else ''}\n{listed or '    (no shots)'}")
    chap = "\n".join(f"- {getattr(m, 'number', '')} {getattr(m, 'title', '')} at {getattr(m, 'start', 0):.1f}s" for m in chapters)
    from .demos import listing
    return (f"TITLE: {title}\n\nBEATS\n" + "\n".join(rows) + "\n\nCAPTURED PAGES\n" + ("\n".join(pages) or "none")
            + "\n\nREAL RUNS (terminal)\n" + (listing(demos or []) or "none")
            + "\n\nCHAPTERS\n" + (chap or "none"))


def _metaphor_data(s: dict, lines, t0: float, t1: float, dur: float) -> dict:
    """A metaphor scene's data from the editor's fields (the free stand-in for a puppet shot)."""
    land = _word_time(lines, s.get("punch") or "", t0, t1)
    items = [str(x) for x in (s.get("items") or [])][:5]
    right = str(s.get("right") or "")
    winner = "right" if s.get("punch") and right and str(s["punch"]).lower() in right.lower() else "left"
    return {"kind": s["metaphor"], "at": round(max(0.6, min(dur - 0.8, (land - t0) if land else dur * 0.45)), 3),
            "label": s.get("label") or s.get("screen_words") or "", "items": items,
            "times": _item_times(items, lines, t0, t1) if items else None,
            "left": s.get("left") or "", "right": right, "winner": winner, "value": s.get("value"),
            "prompt": " ".join(str(s.get("quote") or "").split()[:24])}


def _item_times(items: list[str], lines, t0: float, t1: float, first: float = 0.3) -> list[float]:
    """Each item lands on the word that says it; unspoken ones are spread evenly; always in order, apart."""
    n, dur = len(items), t1 - t0
    out: list[float] = []
    for i, item in enumerate(items):
        at = _phrase_time(lines, item, t0, t1)
        even = first + i * max(0.6, (dur - first - 0.6) / max(1, n))
        t = (at - t0) if at is not None else even
        if out and t < out[-1] + 0.6:
            t = out[-1] + 0.6
        out.append(round(min(t, dur - 0.3), 3))
    return out


def _words_of(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", str(text).lower()) if len(w) > 2 and w not in _SCREEN_STOP}


def _page_for(said: str, sources: list[dict], capture_dir) -> int | None:
    """Owner 2026-11-25 ("steps on screenshots"): the captured page of the product the beat names: its product name
    spoken first, else the page whose title shares the most spoken words (2 at least)."""
    if not capture_dir:
        return None
    words = _words_of(said)
    best, score = None, 0
    for i, page in enumerate(sources or []):
        if not page.get("ok") or page.get("picture_only") or not page.get("top"):
            continue
        name = _words_of(page.get("product") or "")
        sc = (10 if name and name <= words else 0) + len(_words_of(page.get("title") or "") & words)
        if sc > score:
            best, score = i, sc
    return best if score >= 2 else None


def _auto_shots(items: list[str], page: dict) -> list[int] | None:
    """Each step's own spot on the page, found by its words (a button or field first): None unless every step
    has its own spot."""
    spots = shots(page)
    picks: list[int] = []
    for item in items:
        want = _words_of(item)
        best, score = None, 0
        for j, sp in enumerate(spots):
            if j in picks or sp["rect"][2] < 20 or sp["rect"][3] < 12:
                continue
            sc = len(want & _words_of(sp["text"])) * (3 if sp["kind"] == "control" else 2 if sp["kind"] == "headline" else 1)
            if sc > score:
                best, score = j, sc
        if best is None:
            return None
        picks.append(best)
    return picks


def _walkthrough(s: dict, sources: list[dict], capture_dir, lines, t0: float, t1: float, notes: list[str],
                 k: int) -> dict | None:
    """The steps on the product's own captured page: one shot per step. None (shown as plain steps) when the
    page or a shot is missing or the shot is an empty patch. 2026-11-25: the page is found from the words when the
    editor gave none, and each step's spot from its words when the editor picked none."""
    src = s.get("source")
    items = (s.get("items") or [])[:4]
    if not (isinstance(src, int) and 0 <= src < len(sources) and sources[src].get("ok")):
        said = " ".join(str(w.text) for w in _spoken(lines, t0, t1)) + " " + " ".join(items)
        src = _page_for(said, sources, capture_dir)
        if src is not None:
            s["source"] = src
    page = sources[src] if isinstance(src, int) and 0 <= src < len(sources) else None
    picks = (s.get("shots") or [])[:4]
    if page and page.get("ok") and len(items) >= 2 and len(picks) < len(items):
        picks = _auto_shots(items, page) or picks
    if not page or not page.get("ok") or not capture_dir or len(items) < 2 or len(picks) < len(items):
        notes.append(f"scene {k}: walkthrough without a page or a shot per step, shown as steps")
        return None
    spots = shots(page)
    if any(not isinstance(p, int) or not 0 <= p < len(spots) for p in picks[:len(items)]):
        notes.append(f"scene {k}: walkthrough shot not on page {src}, shown as steps")
        return None
    rects = [spots[p]["rect"] for p in picks[:len(items)]]
    deep = bool(page.get("full")) and any(r[1] + r[3] > 860 for r in rects)
    image = capture_dir / (page["full"] if deep else page["top"])
    if not all(_shows_something(image, r) for r in rects):
        notes.append(f"scene {k}: a walkthrough shot looked empty, shown as steps")
        return None
    times = _item_times(items, lines, t0, t1, first=0.9)
    return {"image": image, "url": page.get("url", ""), "page_width": 1440, "heading": s.get("label") or "",
            "steps": [{"rect": r, "label": it, "at": at} for r, it, at in zip(rects, items, times)]}


def one_goli(scenes: list[dict]) -> list[dict]:
    """2026-11-12 (owner): one Goli per block. Goli scenes never overlap: a later one starts when the earlier ends
    (a sliver is dropped)."""
    hosts = sorted((s for s in scenes if s["type"] == "host"), key=lambda s: s["start"])
    end, drop = -1.0, []
    for h in hosts:
        if h["start"] < end - 0.02:
            cut = end - h["start"]
            if h["duration"] - cut < 0.4:
                drop.append(id(h))
                continue
            h["start"], h["duration"] = round(end, 3), round(h["duration"] - cut, 3)
            d = h["data"]
            d["poses"] = [dict(p, at=round(max(0.0, p["at"] - cut), 3)) for p in d.get("poses", [])]
            d["cues"] = [dict(c, start=round(c["start"] - cut, 3)) for c in d.get("cues", []) if c["start"] - cut >= 0]
        end = max(end, h["start"] + h["duration"])
    return [s for s in scenes if id(s) not in drop]


def _domain(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", str(url)).split("/")[0]


def _norm(word: str) -> str:
    return re.sub(r"[^a-z0-9$%.]", "", str(word).lower()).strip(".")


def _word_time(lines: list[Any], word: str, start: float, end: float) -> float | None:
    want = _norm(word)
    for line in lines:
        for w in getattr(line, "words", []) or []:
            if start - 0.01 <= w.start <= end and _norm(w.text) == want:
                return float(w.start)
    return None


def _phrase_time(lines, phrase: str, start: float, end: float) -> float | None:
    for token in str(phrase).split():
        if re.search(r"\d", token) or len(token) > 3:
            at = _word_time(lines, token, start, end)
            if at is not None:
                return at
    return None


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9$%.]+", str(text).lower().replace("'", ""))


def _readable_phrase(text: str, lines, start: float, end: float, punch: str | None = None) -> str:
    """2026-11-12 (owner: "finish line. proves selected"): words on screen are a phrase a person would
    read: the editor's words when they appear in this order in what is said, otherwise 3 to 6 spoken
    words around the key word, never across a sentence end."""
    said = " ".join(l.text for l in lines if l.start < end and l.end > start)
    want = _tokens(text)
    flat = " ".join(_tokens(said))
    if want and len(want) <= 8 and " ".join(want) in flat and not re.search(r"[.!?]\s+\S", str(text).strip()):
        return text
    for sentence in re.split(r"(?<=[.!?])\s+", said):
        words = sentence.split()
        if not words:
            continue
        key = next((i for i, w in enumerate(words) if punch and punch.lower() in w.lower()), None)
        if key is None and punch:
            continue
        key = key or 0
        a = max(0, key - 3)
        return " ".join(words[a:a + 6]).strip(" ,;:")
    words = said.split()
    return " ".join(words[:6]).strip(" ,;:") or text


def _screen_words(text: str, lines, start: float, end: float) -> list[dict[str, Any]]:
    words = str(text or "").split()[:8]
    out, last = [], 0.15
    for i, w in enumerate(words):
        at = _word_time(lines, w, start, end)
        rel = (at - start) if at is not None else last + 0.18
        rel = max(last, min(rel, end - start - 0.4))
        out.append({"text": w, "at": round(rel, 3)})
        last = rel + 0.08
    return out


def _cues_between(cues: list[dict], start: float, end: float) -> list[dict]:
    return [{"start": round(c["start"] - start, 3), "value": c["value"]} for c in cues if start <= c["start"] < end]


def build(raw: dict[str, Any], lines: list[Any], duration: float, fmt: str, sources: list[dict[str, Any]],
          capture_dir: Path | None, cues: list[dict], chapters: list[Any], logo_tiles=None,
          bookends: tuple[str, str] | None = None, demos: list[dict[str, Any]] | None = None,
          look: str = "glass", looks: dict[str, Any] | None = None) -> dict[str, Any]:
    """The editor's answer as a timed edit list for compose.Composer. Line ranges are repaired so every
    line is covered once; references to pages, phrases or words that do not exist are dropped (the scene
    keeps its words), and every such repair is reported in the edit list's `notes`."""
    n = len(lines)
    notes: list[str] = []
    used_pics: set[str] = set()
    scenes = sorted((dict(s) for s in raw.get("scenes") or []), key=lambda s: int(s.get("first_line", 0)))
    fixed: list[dict] = []
    nxt = 0
    for s in scenes:
        a, b = max(int(s.get("first_line", 0)), nxt), min(int(s.get("last_line", 0)), n - 1)
        if a > b:
            continue
        if a > nxt and fixed:                  # a gap: the previous scene carries on over it
            fixed[-1]["last_line"] = a - 1
        elif a > nxt:
            a = nxt
        s["first_line"], s["last_line"] = a, b
        fixed.append(s)
        nxt = b + 1
    if not fixed:
        fixed = [{"type": "studio", "first_line": 0, "last_line": n - 1, "screen_words": lines[0].text, "poses": []}]
        notes.append("editor returned no scenes: one studio scene")
    if nxt < n:
        fixed[-1]["last_line"] = n - 1

    looks = looks or looks_for(None)
    paid_left = dict(looks["paid"])
    out: list[dict] = []
    shown_runs: set[int] = set()
    used_metaphors: set[str] = set()
    shown_3d: list[str] = []
    for k, s in enumerate(fixed):
        t0 = 0.0 if k == 0 else float(lines[s["first_line"]].start) - 0.12
        t1 = duration if k == len(fixed) - 1 else float(lines[fixed[k + 1]["first_line"]].start) - 0.12
        t0, t1 = max(0.0, t0), max(t0 + 0.4, t1)
        dur = t1 - t0
        kind = s.get("type")
        # 2026-11-14 (owner): never the first 6 words of a sentence cut off ("The question is whether you spend");
        # without the editor's own headline, the whole line when it is short, else its key term
        line0 = lines[s["first_line"]]
        words = s.get("screen_words") or (line0.text if len(line0.text.split()) <= 6 else
                                          (getattr(line0, "label", "") or getattr(line0, "emphasis", "") or
                                           " ".join(line0.text.split()[:6])))
        poses = []
        for p in s.get("poses") or []:
            at = _word_time(lines, p.get("word", ""), t0, t1)
            if p.get("pose") in POSES and at is not None:
                poses.append({"pose": p["pose"], "at": round(at - t0, 3)})
        poses = sorted(poses, key=lambda p: p["at"])
        if not poses or poses[0]["at"] > 0.05:
            poses.insert(0, {"pose": "talk", "at": 0})

        def words_scene(text=words, punch=s.get("punch")):
            text = _readable_phrase(text, lines, t0, t1, punch)
            return {"type": "kinetic_title", "start": t0, "duration": dur, "in": "cut",
                    "data": {"words": _screen_words(text, lines, t0, t1), "punch": (punch or "").lower().strip(".,!?")}}

        # 2026-11-18 (owner: "if it fails we use the other scenes"): a scene that cannot be made never becomes a text
        # card. A how-to step with no screenshot shows its page; with no page, Goli says it in the studio.
        walk = _walkthrough(s, sources, capture_dir, lines, t0, t1, notes, k) if kind == "walkthrough" else None
        if kind == "walkthrough" and not walk:
            src = s.get("source")
            page = sources[src] if isinstance(src, int) and 0 <= src < len(sources) else None
            # owner 2026-11-25: the steps are never skipped: numbered steps beside the real page
            kind = "steps" if page and page.get("ok") and capture_dir and len(s.get("items") or []) >= 2 else \
                "source" if page and page.get("ok") and capture_dir else "studio"
            notes.append(f"scene {k}: walkthrough shown as {'its page' if kind == 'source' else 'Goli in the studio'}")
        elif kind == "source":
            src = s.get("source")
            page = sources[src] if isinstance(src, int) and 0 <= src < len(sources) else None
            if not (page and page.get("picture_only") and page.get("photo") and capture_dir) and \
                    (not page or not page.get("ok") or not capture_dir):
                notes.append(f"scene {k}: source {src} not captured, Goli says it in the studio")
                kind = "studio"

        if kind == "studio":
            out.append({"type": "host", "start": t0, "duration": dur, "data": {
                "place": "studio", "cues": _cues_between(cues, t0, t1), "poses": poses,
                "words": _screen_words(words, lines, t0, t1), "punch": (s.get("punch") or "").lower().strip(".,!?")}})
        elif kind == "source":
            src = s.get("source")
            page = sources[src] if isinstance(src, int) and 0 <= src < len(sources) else None
            if page and page.get("picture_only") and page.get("photo") and capture_dir:
                out.append({"type": "photo", "start": t0, "duration": dur, "data": {
                    "image": capture_dir / page["photo"], "url": page.get("url", "")}})
                continue
            if not page or not page.get("ok") or not capture_dir:
                notes.append(f"scene {k}: source {src} not captured, shown as words")
                out.append(words_scene())
                continue
            spots = shots(page)
            ph = s.get("phrase")
            spot = spots[ph] if isinstance(ph, int) and 0 <= ph < len(spots) else None
            highlights = []
            if spot:
                at = _phrase_time(lines, spot["text"], t0, t1) if spot["kind"] == "fact" else None
                highlights.append({"rect": spot["rect"], "ring": spot["kind"] == "fact" and len(spot["text"]) <= 8,
                                   "sweep": spot["kind"] != "fact",
                                   "at": round(max(0.6, (at - t0) if at is not None else 0.7), 3),
                                   "label": s.get("callout") or None, "sub": s.get("callout_sub") or ""})
            elif ph is not None:
                notes.append(f"scene {k}: shot {ph} not on page {src}")
            # a shot below the first screen is filmed on the whole-page capture
            # 2026-11-12 (owner: Outskill's screen recordings): long videos film the whole page and scroll it
            deep = bool(page.get("full")) and (fmt == "long" or (bool(spot) and spot["rect"][1] + spot["rect"][3] > 860))
            image = capture_dir / (page["full"] if deep else page["top"])
            if spot and not _shows_something(image, spot["rect"]):
                # 2026-11-11: a zoom landed on an empty dark patch of a page: use the headline instead
                notes.append(f"scene {k}: shot {ph} on page {src} looked empty, zoomed to the headline")
                head = page.get("headline")
                highlights = ([{"rect": head, "sweep": True, "at": 0.6, "label": s.get("callout") or None,
                                "sub": s.get("callout_sub") or ""}] if head and _shows_something(capture_dir / page["top"], head) else [])
                deep = False
                image = capture_dir / page["top"]
            out.append({"type": "browser_shot", "start": t0, "duration": dur, "data": {
                "image": image,
                "url": page.get("url", ""), "edge": "glass" if _dark(image) else (s.get("edge") or "glass"),
                "page_width": 1440, "highlights": [h for h in highlights if h], "headline": page.get("headline"),
                "photo": str(capture_dir / page["photo"]) if page.get("photo") else None,
                "record": bool(deep and fmt == "long")}})
            if s.get("goli_corner") and dur >= 1.8:
                out.append({"type": "host", "start": t0 + 0.35, "duration": dur - 0.35, "data": {
                    "place": "corner", "cues": _cues_between(cues, t0 + 0.35, t1),
                    "poses": [dict(p, at=max(0, p["at"] - 0.35)) for p in poses] or [{"pose": "point_left", "at": 0}]}})
        elif kind == "photo":
            src = s.get("source")
            page = sources[src] if isinstance(src, int) and 0 <= src < len(sources) else None
            if page and page.get("photo") and capture_dir and (capture_dir / page["photo"]).exists():
                # each use of a page's photos shows its next picture
                pics = [p for p in (page.get("photos") or [page["photo"]]) if (capture_dir / p).exists()
                        and p not in used_pics and _real_picture(capture_dir / p)]
                if not pics:               # owner 2026-11-25: never the same picture again: Goli and the TV say it
                    notes.append(f"scene {k}: every picture of page {src} already shown, Goli and the TV instead")
                    out.append({"type": "host", "start": t0, "duration": dur, "data": {
                        "place": "studio", "cues": _cues_between(cues, t0, t1), "poses": poses,
                        "words": _screen_words(words, lines, t0, t1), "punch": (s.get("punch") or "").lower().strip(".,!?")}})
                    continue
                pick = pics[0]
                used_pics.add(pick)
                out.append({"type": "photo", "start": t0, "duration": dur, "data": {
                    "image": capture_dir / pick, "url": page.get("url", "")}})
                if s.get("goli_corner") and dur >= 1.2:
                    out.append({"type": "host", "start": t0 + 0.2, "duration": dur - 0.2, "data": {
                        "place": "corner", "cues": _cues_between(cues, t0 + 0.2, t1),
                        "poses": [dict(p, at=max(0, p["at"] - 0.2)) for p in poses]}})
            else:
                notes.append(f"scene {k}: no photo on page {src}, shown as words")
                out.append(words_scene())
        elif kind == "flow" and len(s.get("items") or []) >= 2:
            out.append({"type": "flow", "start": t0, "duration": dur, "in": "wipe", "data": {
                "nodes": s["items"][:4], "brands": s.get("brands") or []}})
        elif kind == "icon" and s.get("brands") and logo_tiles and logo_tiles(s["brands"][0]):
            out.append({"type": "logo_tiles", "start": t0, "duration": dur, "data": {
                "tiles": [{"image": logo_tiles(s["brands"][0])}], "caption": s.get("label") or s["brands"][0], "big": True}})
        elif kind == "stat" and isinstance(s.get("value"), (int, float)):
            value, prefix, suffix = _stat_units(float(s["value"]), s.get("prefix") or "", s.get("suffix") or "",
                                                " ".join(w.text for w in _spoken(lines, t0 - 0.5, t1 + 0.5)))
            out.append({"type": "stat_counter", "start": t0, "duration": dur, "in": "whip", "data": {
                "value": value, "prefix": prefix, "suffix": suffix,
                "decimals": 0 if abs(value - round(value)) < 1e-9 else 1, "label": s.get("label") or ""}})
        elif kind == "compare" and s.get("rows"):
            rows = s["rows"][:4]
            out.append({"type": "comparison", "start": t0, "duration": dur, "in": "wipe", "data": {
                "left": s.get("left") or "", "right": s.get("right") or "",
                "rows": [[r["label"], r["a"], r["b"]] for r in rows],
                "winners": [r["winner"] if r["winner"] != "none" else None for r in rows],
                "gap": min(0.55, max(0.25, (dur - 0.8) / max(1, len(rows))))}})
        elif kind == "object3d" and (s.get("object3d") in OBJECTS3D or len(s.get("parts3d") or []) >= 2) \
                and not (out and out[-1]["type"] == "object3d") and not _object_unsaid(s, lines, t0, t1, shown_3d, notes, k):
            shown_3d.append(s["object3d"])
            land = _word_time(lines, s.get("punch") or "", t0, t1)
            out.append({"type": "object3d", "start": t0, "duration": dur, "in": "rise", "data": {
                "object": s["object3d"] if s["object3d"] in OBJECTS3D else "custom",
                "move": s.get("move3d") if s.get("move3d") in MOVES3D else "own",
                "parts": [] if s["object3d"] in OBJECTS3D else [dict(p) for p in (s.get("parts3d") or [])[:12]],
                "at": round(max(0.5, min(dur - 1.6, (land - t0) if land else 0.8)), 3),
                "said": " ".join(str(w.text) for w in _spoken(lines, t0, t1)),
                "lead": " ".join(str(s.get("label") or s.get("screen_words") or "").split()[:5])}})
        elif kind == "puppets" and "puppets" in looks["free"] and s.get("puppet") \
                and not (out and out[-1]["type"] == "puppet_clip"):
            try:
                doc = json.loads(s["puppet"])
            except (TypeError, ValueError):
                doc = None
            fallback = _metaphor_data(s, lines, t0, t1, dur) if s.get("metaphor") in METAPHORS else None
            if isinstance(doc, dict):
                spoken = [w for l in lines for w in (getattr(l, "words", None) or []) if t0 - 0.01 <= float(w.start) < t1]
                out.append({"type": "puppet_clip", "start": t0, "duration": dur, "in": "rise", "data": {
                    "doc": doc, "text": " ".join(w.text for w in spoken) or " ".join(l.text for l in lines[s["first_line"]:s["last_line"] + 1]),
                    "words": [{"text": w.text, "t": round(float(w.start) - t0, 2)} for w in spoken], "fallback": fallback}})
            elif fallback:
                out.append({"type": "metaphor", "start": t0, "duration": dur, "in": "rise", "data": fallback})
                notes.append(f"scene {k}: puppet shot unreadable, metaphor instead")
            else:
                out.append(words_scene())
        elif kind == "recipe" and s.get("recipe") in RECIPE_KEYS \
                and (s["recipe"] in looks["free"] and s.get("fill") or paid_left.get(s["recipe"], 0) > 0 and s.get("recipe_brief")) \
                and not (out and out[-1]["type"] == "recipe_clip"):
            if s["recipe"] in paid_left:
                paid_left[s["recipe"]] -= 1
            fallback = None
            if s.get("object3d") in OBJECTS3D or len(s.get("parts3d") or []) >= 2:
                land = _word_time(lines, s.get("punch") or "", t0, t1)
                fallback = {"object": s["object3d"] if s.get("object3d") in OBJECTS3D else "custom",
                            "move": s.get("move3d") if s.get("move3d") in MOVES3D else "own",
                            "parts": [] if s.get("object3d") in OBJECTS3D else [dict(p) for p in (s.get("parts3d") or [])[:12]],
                            "at": round(max(0.5, min(dur - 1.6, (land - t0) if land else 0.8)), 3),
                            "lead": " ".join(str(s.get("label") or "").split()[:5])}
            words = [{"text": w.text, "t": round(float(w.start) - t0, 2)} for l in lines for w in (getattr(l, "words", None) or [])
                     if t0 - 0.01 <= float(w.start) < t1]
            fill = None
            if s["recipe"] in looks["free"]:
                try:
                    fill = json.loads(s.get("fill") or "")
                except ValueError:
                    fill = None
            out.append({"type": "recipe_clip", "start": t0, "duration": dur, "in": "rise", "data": {
                "recipe": s["recipe"], "brief": str(s.get("recipe_brief") or "")[:600], "words": words,
                "fill": fill if isinstance(fill, dict) else None, "fallback": fallback}})
        elif kind == "metaphor" and s.get("metaphor") in METAPHORS and s["metaphor"] not in used_metaphors \
                and not (out and out[-1]["type"] == "metaphor"):
            used_metaphors.add(s["metaphor"])
            land = _word_time(lines, s.get("punch") or "", t0, t1)
            items = [str(x) for x in (s.get("items") or [])][:5]
            right = str(s.get("right") or "")
            winner = "right" if s.get("punch") and right and str(s["punch"]).lower() in right.lower() else "left"
            out.append({"type": "metaphor", "start": t0, "duration": dur, "in": "rise", "data": {
                "kind": s["metaphor"], "at": round(max(0.6, min(dur - 0.8, (land - t0) if land else dur * 0.45)), 3),
                "label": s.get("label") or s.get("screen_words") or "", "items": items,
                "times": _item_times(items, lines, t0, t1) if items else None,
                "left": s.get("left") or "", "right": right, "winner": winner, "value": s.get("value"),
                # owner 2026-11-26: a prompt is shown as the prompt itself (the beat's quote), never as the word
                "prompt": " ".join(str(s.get("quote") or "").split()[:24])}})
        elif kind == "terminal" and isinstance(s.get("source"), int) and 0 <= s["source"] < len(demos or []) \
                and s["source"] not in shown_runs:
            from .demos import scene_data
            shown_runs.add(s["source"])
            out.append({"type": "terminal", "start": t0, "duration": dur, "data": scene_data(demos[s["source"]],
                                                                                             s.get("phrase"))})
        elif kind == "walkthrough" and walk:
            out.append({"type": "walkthrough", "start": t0, "duration": dur, "data": walk})
        elif kind == "prompt" and s.get("quote"):
            out.append({"type": "prompt_card", "start": t0, "duration": dur, "in": "rise", "data": {
                "text": " ".join(str(s["quote"]).split()[:24]), "tool": s.get("label") or ""}})
        elif kind == "checklist" and s.get("items"):
            items = s["items"][:5]
            out.append({"type": "checklist", "start": t0, "duration": dur, "in": "wipe", "data": {
                "heading": s.get("screen_words") or "", "items": items, "at": _item_times(items, lines, t0, t1)}})
        elif kind in ("steps", "walkthrough") and s.get("items"):
            items = s["items"][:4]
            times = []
            for i, item in enumerate(items):
                at = _phrase_time(lines, item, t0, t1)
                times.append(round((at - t0) if at is not None else 0.3 + i * min(0.7, (dur - 0.6) / len(items)), 3))
            data = {"heading": s.get("label") or "", "items": items, "at": times}
            # owner 2026-11-25 ("steps to be shown without skipping, on screenshots"): numbered steps stand beside
            # the product's real page whenever one was captured
            said = " ".join(str(w.text) for w in _spoken(lines, t0, t1)) + " " + " ".join(items)
            src = s.get("source") if isinstance(s.get("source"), int) and 0 <= s["source"] < len(sources) \
                and sources[s["source"]].get("ok") else _page_for(said, sources, capture_dir)
            if src is not None and capture_dir and (Path(capture_dir) / sources[src]["top"]).exists() \
                    and _real_picture(Path(capture_dir) / sources[src]["top"]):
                data.update(image=Path(capture_dir) / sources[src]["top"], url=sources[src].get("url", ""))
            out.append({"type": "steps", "start": t0, "duration": dur, "in": "wipe", "data": data})
        elif kind == "timeline" and len(s.get("points") or []) >= 2:
            out.append({"type": "timeline", "start": t0, "duration": dur, "in": "whip", "data": {"points": s["points"][:4]}})
        elif kind == "quote" and s.get("quote"):
            out.append({"type": "quote_card", "start": t0, "duration": dur, "in": "rise", "data": {
                "text": s["quote"], "who": s.get("quote_by") or "", "mark": [s.get("punch") or ""]}})
        elif kind == "logos" and s.get("brands") and logo_tiles:
            pairs = [(b, t) for b, t in ((b, logo_tiles(b)) for b in s["brands"][:5]) if t]
            if len(pairs) >= 1:
                # owner 2026-11-25 (Outskill's logo dock): each logo lands in its slot as its name is said
                ats, last = [], -0.6
                for i, (b, _) in enumerate(pairs):
                    at = _phrase_time(lines, b, t0, t1)
                    at = (at - t0) if at is not None else 0.3 + i * min(0.6, (dur - 0.6) / len(pairs))
                    at = max(at, last + 0.35)
                    ats.append(round(min(at, dur - 0.4), 3))
                    last = at
                out.append({"type": "logo_tiles", "start": t0, "duration": dur, "data": {
                    "tiles": [{"image": t, "name": b, "at": a} for (b, t), a in zip(pairs, ats)], "dock": True,
                    "caption": s.get("screen_words") or ""}})
            else:
                notes.append(f"scene {k}: no logos found for {s['brands']}, shown as words")
                out.append(words_scene(" ".join(s["brands"][:4])))
        elif kind == "chapter" and str(s.get("label") or words).strip().lower() in ("intro", "introduction", "close",
                                                                                    "outro", "conclusion"):
            # 2026-11-13 (review): no "Intro" / "Close" title cards: the opening and ending say that already
            out.append(words_scene(words))
        elif kind == "chapter":
            out.append({"type": "chapter_card", "start": t0, "duration": dur, "in": "whip", "data": {
                "number": "", "title": s.get("label") or words}})
        elif kind == "follow":
            # 2026-11-12 (owner): no "follow" text card: Goli points at a Subscribe button that gets pressed,
            # then the bell rings
            out.append({"type": "host", "start": t0, "duration": dur, "data": {
                "place": "full" if fmt == "long" else "lower", "subscribe": True, "cues": _cues_between(cues, t0, t1),
                "poses": [{"pose": "point" if fmt == "long" else "point_up", "at": 0},
                          {"pose": "thumbs_up", "at": round(min(dur - 0.4, 2.2), 2)}]}})
        else:
            # 2026-11-18 (owner): no text cards; a scene without its data is Goli saying the line
            notes.append(f"scene {k}: {kind} without its data, Goli says it in the studio")
            out.append({"type": "host", "start": t0, "duration": dur, "data": {
                "place": "studio", "cues": _cues_between(cues, t0, t1), "poses": poses,
                "words": _screen_words(words, lines, t0, t1), "punch": (s.get("punch") or "").lower().strip(".,!?")}})
    out = _no_repeats(out, lines, fmt, notes)
    out = _pace(out, lines, fmt)
    out = _words_cap(out, notes, fmt, cues)
    out = _short_cards(out, notes, cues)
    out = _screen_pictures(out, sources, capture_dir, lines, cues, notes, look if look in LOOKS3D else "glass")
    out = _min_length(out, fmt)
    out = _recipe_time(out, fmt, notes)
    out = _lower_host(out, cues, fmt)
    if bookends and lines:
        out = _bookends(out, lines, cues, duration, *bookends)
    out = one_goli(out)
    out = one_goli(_cap_cards(out, lines, cues, notes))
    _transitions(out, lines)
    misses = plan_coverage(raw.get("plan") or [], out, lines, sources, notes)
    return {"format": fmt, "duration": duration, "scenes": out, "notes": notes, "captions": captions(lines, fmt),
            "plan": raw.get("plan") or [], "plan_misses": misses,
            "look": look if look in LOOKS3D else "glass",
            "chapters": [{"title": f"{getattr(m, 'number', '')} · {getattr(m, 'title', '')}".strip(" ·"),
                          "at": float(getattr(m, "start", 0))} for m in chapters]}


def _scene_words(sc: dict, sources: list[dict]) -> set[str]:
    """Everything a scene shows, as words: its data (labels, names, words, fills) and the page its picture is from."""
    text = json.dumps(sc.get("data") or {}, default=str)
    pic = Path(str(sc["data"].get("screen") or sc["data"].get("image") or "")).name
    for page in sources or []:
        if pic and pic in {Path(str(page.get(k) or "")).name for k in ("top", "full", "photo")} | \
                {Path(str(x)).name for x in page.get("photos") or []}:
            text += " " + str(page.get("title") or "") + " " + str(page.get("subject") or page.get("product") or "")
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2}


def plan_coverage(plan: list[dict], scenes: list[dict], lines, sources: list[dict], notes: list[str]) -> list[dict]:
    """Owner 2026-11-25 (storyboard per statement): every sentence's named thing must be on screen while it is said.
    A sentence whose scenes show nothing of it is a miss: its studio TV takes the named words (free), and the doctor
    counts it as a lesson."""
    misses = []
    for row in plan:
        try:
            a, b = int(row.get("first_line", -1)), int(row.get("last_line", -1))
            t0, t1 = float(lines[a].start), float(lines[b].end)
        except (IndexError, TypeError, ValueError):
            continue
        named = {w for w in re.findall(r"[a-z0-9]+", str(row.get("named") or "").lower())
                 if len(w) > 2 and w not in _SCREEN_STOP}
        if not named:
            continue
        inside = [sc for sc in scenes if sc["start"] < t1 - 0.2 and sc["start"] + sc["duration"] > t0 + 0.2
                  and not (sc["type"] == "host" and sc["data"].get("place") in ("side", "corner", "lower"))]
        if any(named & _scene_words(sc, sources) for sc in inside):
            continue
        misses.append({"first_line": a, "last_line": b, "named": row.get("named"), "at": round(t0, 2)})
        for sc in inside:
            if sc["type"] == "host" and sc["data"].get("place") == "studio" and not sc["data"].get("screen"):
                sc["data"]["words"] = _screen_words(str(row.get("named")), lines, sc["start"], sc["start"] + sc["duration"])
                sc["data"]["punch"] = next(iter(named))
                break
        notes.append(f"plan: '{row.get('named')}' at {t0:.1f}s is not on screen")
    return misses


# 2026-11-12 (owner): long videos never open or close the same way, and Goli is "interactive".
INTROS = ("walk_in", "pop_up", "chair_spin", "close_pull", "screen_on", "coffee", "stage_slam")
OUTROS = ("wave_walk", "lights_off", "lean_back", "chair_spin_away", "end_card")
INTRO_POSES = {"walk_in": [("talk", 0)], "pop_up": [("shock", 0), ("talk", 1.3)], "chair_spin": [("talk", 0)],
               "close_pull": [("talk", 0)], "screen_on": [("point", 0), ("talk", 1.6)],
               "coffee": [("think", 0), ("talk", 1.0)], "stage_slam": [("point", 0.3), ("talk", 1.8)]}
OUTRO_POSES = {"wave_walk": [("talk", 0), ("wave", -2.2)], "lights_off": [("talk", 0), ("wave", -2.4)],
               "lean_back": [("talk", 0), ("thumbs_up", -2.2)], "chair_spin_away": [("talk", 0), ("wave", -2.0)],
               "end_card": [("point", 0)]}
CALM = {"coffee", "lean_back"}


def pick_bookends(title: str, recent_intros: list[str], recent_outros: list[str], seed: int) -> tuple[str, str]:
    """One opening and one ending: never one of the last 3 used; a shock story never opens with coffee."""
    import random
    from ..vector.thumb_styles import is_alert
    rnd = random.Random(seed)
    alarm = is_alert(title)
    intros = [i for i in INTROS if i not in recent_intros[:3] and not (alarm and i in CALM)] or list(INTROS)
    if alarm and "pop_up" in intros:
        intros = ["pop_up"] + [i for i in intros if i != "pop_up"][:1]
    outros = [o for o in OUTROS if o not in recent_outros[:3]] or list(OUTROS)
    return rnd.choice(intros), rnd.choice(outros)


def _bookends(scenes: list[dict], lines: list[Any], cues: list[dict], duration: float, intro: str, outro: str,
              length: float = 3.6) -> list[dict]:
    """The opening covers the first ~3.6 s and the ending the last ~3.6 s: scenes under them are trimmed."""
    a = min(length, duration / 4)
    b = max(a + 1.0, duration - length)

    def text_between(t0, t1):
        return " ".join(l.text for l in lines if l.start < t1 and l.end > t0) or (lines[0].text if lines else "")

    def host(t0, t1, which, poses, place):
        words = text_between(t0, t1).split()[:5]
        at = [round(i * min(1.4, t1 - t0) / max(1, len(words)), 2) for i in range(len(words))]
        ps = [{"pose": p, "at": round(max(0.0, (t1 - t0) + o if o < 0 else o), 3)} for p, o in poses]
        return {"type": "host", "start": t0, "duration": t1 - t0, "data": {
            "place": place, "cues": _cues_between(cues, t0, t1), "poses": sorted(ps, key=lambda p: p["at"]),
            "words": [{"text": w_, "at": t} for w_, t in zip(words, at)], "punch": (words[-1] if words else "").lower().strip(".,!?"),
            "intro" if which in INTROS else "outro": which}}

    out = []
    for sc in scenes:
        s0, s1 = sc["start"], sc["start"] + sc["duration"]
        s0, s1 = max(s0, a), min(s1, b)
        if s1 - s0 < 0.4:
            continue
        out.append(dict(sc, start=round(s0, 3), duration=round(s1 - s0, 3)))
    out.insert(0, host(0.0, a, intro, INTRO_POSES[intro], "full" if intro == "stage_slam" else "studio"))
    out.append(host(b, duration, outro, OUTRO_POSES[outro], "full" if outro == "end_card" else "studio"))
    return sorted(out, key=lambda s: (s["start"], s["type"] == "host"))


def save(edit: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(edit, indent=2, default=str) + "\n", encoding="utf-8")


# A Short shows the proof on top and keeps Goli at his desk below it for the whole run of cards
# (owner 2026-11-11: no empty space above and below the cards). His pose follows each card.
REACT = {"browser_shot": "point_up", "stat_counter": "shock", "comparison": "explain", "steps": "point_up",
         "walkthrough": "point_up", "terminal": "point", "metaphor": "point", "object3d": "point", "recipe_clip": "point", "puppet_clip": "point", "prompt_card": "point_up", "checklist": "thumbs_up", "timeline": "explain", "quote_card": "think", "logo_tiles": "thumbs_up", "kinetic_title": "talk",
         "chapter_card": "talk", "follow_cta": "wave"}


# 2026-11-12 (owner): in long videos Goli stands right of the proof in (nearly) every scene and reacts to it:
# points at the page, is shocked by the number, counts through the steps, shrugs at a doubt; never the same
# gesture twice in a row for the same kind of card.
REACT_LONG = {"browser_shot": ["point_left", "point_up", "explain"], "photo": ["point_left", "think"],
              "stat_counter": ["shock", "point_left"], "comparison": ["shrug", "think", "explain"],
              "steps": ["explain", "point_up", "thumbs_up"], "walkthrough": ["point_left", "point_up", "explain"], "terminal": ["point", "think", "thumbs_up"], "metaphor": ["point", "shock", "think"], "object3d": ["point", "shock", "explain"], "recipe_clip": ["point_left", "explain", "shock"], "puppet_clip": ["point_left", "think", "explain"],
              "prompt_card": ["point_left", "think"], "checklist": ["thumbs_up", "explain"], "timeline": ["point_left", "explain"],
              "flow": ["explain", "point_left"], "quote_card": ["think", "shrug"], "logo_tiles": ["thumbs_up", "point_left"],
              "kinetic_title": ["explain", "talk", "point_left"], "chapter_card": ["wave", "talk"]}


def _lower_host(scenes: list[dict], cues: list[dict], fmt: str = "short") -> list[dict]:
    corner = [s for s in scenes if s["type"] == "host" and s["data"].get("place") == "corner"]
    main = [s for s in scenes if s not in corner]
    out: list[dict] = []
    run: list[dict] = []
    runs = [0]
    used: dict[str, int] = {}

    def close():
        if not run:
            return
        t0 = run[0]["start"]
        t1 = run[-1]["start"] + run[-1]["duration"]
        poses = []
        for scene in run:
            if fmt == "long":
                options = REACT_LONG.get(scene["type"], ["talk", "explain"])
                used[scene["type"]] = used.get(scene["type"], -1) + 1
                poses.append({"pose": options[used[scene["type"]] % len(options)], "at": round(scene["start"] - t0, 3)})
                if scene["duration"] > 3.0:          # then back to talking, so he never freezes in one gesture
                    poses.append({"pose": "talk", "at": round(scene["start"] - t0 + scene["duration"] * .6, 3)})
                scene["data"]["goli_zone"] = True
                continue
            poses.append({"pose": REACT.get(scene["type"], "talk"), "at": round(scene["start"] - t0, 3)})
            scene["data"]["goli_zone"] = True       # owner 2026-11-25: a Short is the long video in 9:16: proof on top, Goli under it
            for c in corner:            # the editor's own reaction words for this card win
                if abs(c["start"] - scene["start"]) < 0.6:
                    for p in c["data"].get("poses", []):
                        if p["at"] > 0.3:
                            poses.append({"pose": p["pose"], "at": round(c["start"] - t0 + p["at"], 3)})
        poses = sorted(poses, key=lambda p: p["at"])
        # 2026-11-11 (owner): not always at the desk: every other run of cards he stands beside them
        # owner 2026-11-25: "the same way we treat long videos... the only difference is framing": in a Short too he
        # stands with the proof (under it), never back at the desk with the proof on a TV
        place = "side"
        runs[0] += 1
        out.append({"type": "host", "start": t0, "duration": t1 - t0, "data": {
            "place": place, "cues": [{"start": round(c["start"] - t0, 3), "value": c["value"]}
                                       for c in cues if t0 <= c["start"] < t1], "poses": poses}})
        run.clear()

    for scene in main:
        if scene["type"] == "host" or (run and scene["type"] == "follow_cta"):
            close()
        else:
            run.append(scene)
        out.append(scene)
    close()
    return sorted(out, key=lambda s: (s["start"], s["type"] == "host"))


def _no_dots(text: str) -> str:
    """2026-11-13 (owner): "..." is how the voice is told to pause; on screen it reads as a stop. Captions drop it."""
    t = str(text).replace("…", "...")
    return t[:-3] if t.endswith("...") and len(t) > 3 else t.replace("...", "")


def captions(lines: list[Any], fmt: str) -> list[dict[str, Any]]:
    """Spoken-word captions, chunked as the illustration engine does (short: up to 4 words, long: 7)."""
    from ..vector.align import caption_chunks

    out = []
    for c in caption_chunks(lines, max_words=4 if fmt == "short" else 7):
        if not c.words:
            continue
        out.append({"start": round(float(c.words[0].start) - 0.05, 3), "end": round(float(c.end), 3),
                    "words": [{"text": _no_dots(w.text), "at": round(float(w.start), 3)} for w in c.words],
                    "keys": sorted(int(k) for k in c.keys)})
    return out


# 2026-11-11 (owner): "too slow": in the niche the picture changes every second or two. A stretch longer
# than a beat is cut at word boundaries into beats that each show something new.
BEAT = {"short": 2.2, "long": 6.5}
STUDIO_BEAT = {"short": 3.0, "long": 10.0}
HOLD = {"recipe_clip", "puppet_clip", "stat_counter", "comparison", "steps", "walkthrough", "terminal", "metaphor", "object3d", "prompt_card", "checklist", "timeline", "quote_card", "logo_tiles", "chapter_card", "follow_cta"}


# owner 2026-11-25: a 3D object is shown only when it is the real thing being said. A device with a screen (laptop,
# phone) is right whenever its screen shows the real page or picture of what is said (owner: "11 times is not wrong;
# what is wrong is the same way, same colour, and the screen empty"); any other object only when the words name it.
# Each showing gets its own look and view, never the previous one's.
SCREEN_DEVICES = ("laptop", "phone")
OBJECT_WORDS = {"laptop": ("laptop", "computer", "pc", "macbook", "notebook", "desktop"),
                "phone": ("phone", "iphone", "android", "mobile", "smartphone"),
                "server": ("server", "servers", "datacenter", "data", "rack", "cloud"),
                "chip": ("chip", "chips", "gpu", "gpus", "processor", "cpu", "silicon", "nvidia"),
                "battery": ("battery", "batteries", "cell", "cells", "charge", "charging")}


def _stat_units(value: float, prefix: str, suffix: str, said: str) -> tuple[float, str, str]:
    """A counter reads like money or a count, never "90.92" or "229.0" (owner 2026-11-25): a big number gets its
    K/M/B, and the unit the voice says ("dollars", "billion", "percent") is put on when the editor left it off."""
    low = said.lower()
    if abs(value) >= 1e9:
        value, suffix = value / 1e9, suffix or "B"
    elif abs(value) >= 1e6:
        value, suffix = value / 1e6, suffix or "M"
    elif abs(value) >= 1e4:
        value, suffix = value / 1e3, suffix or "K"
    if not suffix:
        suffix = ("B" if re.search(r"\bbillions?\b", low) else "M" if re.search(r"\bmillions?\b", low)
                  else "%" if re.search(r"\bper ?cent\b|%", low) else "")
    if not prefix and re.search(r"\bdollars?\b|\$", low):
        prefix = "$"
    return round(value, 1), prefix, suffix


def _object_unsaid(s: dict, lines, t0: float, t1: float, shown: list[str], notes: list[str], k: int) -> bool:
    name = str(s.get("object3d") or "").lower()
    said = {_norm(w.text) for w in _spoken(lines, t0 - 0.3, t1 + 0.3)}
    names = OBJECT_WORDS.get(name) or tuple(_norm(x) for x in re.findall(r"[A-Za-z]+", name + " " + str(s.get("label") or "")) if len(x) > 3)
    if name in SCREEN_DEVICES:
        return False              # its screen decides (_screen_pictures): the real thing on it, else another block
    if not any(n in said for n in names):
        notes.append(f"scene {k}: 3D {name} but the words do not name it, Goli and the TV instead")
        return True
    return False


def _spoken(lines, a: float, b: float) -> list[Any]:
    return [w for line in lines for w in (getattr(line, "words", []) or []) if a <= w.start < b]


def _cuts(lines, t0: float, t1: float, beat: float) -> list[float]:
    n = min(6, max(1, math.ceil((t1 - t0) / beat - 0.25)))
    if n == 1:
        return [t0, t1]
    starts = [w.start for w in _spoken(lines, t0 + 0.6, t1 - 0.6)]
    cuts = [t0]
    for k in range(1, n):
        want = t0 + (t1 - t0) * k / n
        near = min(starts, key=lambda x: abs(x - want)) if starts else want
        near = near - 0.05 if abs(near - want) <= 1.0 else want     # a silent stretch is cut on time
        if near - cuts[-1] > 0.8 and t1 - near > 0.8:
            cuts.append(near)
    return cuts + [t1]


FILLER = set("a an the and or but so to of in on at for with is are was were be been it its it's this that these those "
             "you your we our i my me he she they them their there here just really actually what who how why when "
             "do does did can could would should will have has had not no yes than then as by from up out about".split())


def _words_beat(lines, a: float, b: float) -> dict:
    """The meaning of what is said in this beat, not the running text (the captions carry that)."""
    spoken = _spoken(lines, a, b) or _spoken(lines, a - 1, b)
    ws = [w for w in spoken if _norm(w.text) not in FILLER][:4] or spoken[:4]
    punch = max((w.text for w in ws), key=lambda t: (bool(re.search(r"\d", t)), len(t)), default="")
    return {"type": "kinetic_title", "start": a, "duration": b - a, "in": "cut", "data": {
        "words": [{"text": w.text, "at": round(max(0.05, w.start - a), 3)} for w in ws],
        "punch": punch.lower().strip(".,!?")}}


def _slice_host(s: dict, a: float, b: float, lines, first: bool) -> dict:
    t0 = s["start"]
    d = s["data"]
    poses = [p for p in d.get("poses", []) if a - t0 <= p["at"] < b - t0]
    before = [p for p in d.get("poses", []) if p["at"] < a - t0]
    if not poses or poses[0]["at"] > a - t0 + 0.05:
        poses.insert(0, {"pose": (before[-1]["pose"] if before else "talk"), "at": a - t0})
    return dict(s, start=a, duration=b - a, data=dict(
        d, cues=[dict(c, start=round(c["start"] - (a - t0), 3)) for c in d.get("cues", []) if a - t0 <= c["start"] < b - t0],
        poses=[dict(p, at=round(p["at"] - (a - t0), 3)) for p in poses],
        words=[dict(w, at=round(max(0.05, w["at"] - (a - t0)), 3)) for w in d.get("words", [])] if first
        else _words_beat(lines, a, b)["data"]["words"]))


def _pace(scenes: list[dict], lines, fmt: str) -> list[dict]:
    out = []
    for s in scenes:
        t0, t1 = s["start"], s["start"] + s["duration"]
        kind = s["type"]
        beat = BEAT.get(fmt, 4.0)
        if kind == "host" and s["data"].get("place") != "studio":
            out.append(s)
            continue
        limit = (STUDIO_BEAT[fmt] if kind == "host" else beat * 2.4 if kind in ("walkthrough", "terminal")
                 else beat * 1.6 if kind in HOLD else beat)
        if t1 - t0 <= limit:
            out.append(s)
            continue
        if kind in HOLD:                       # the card keeps time for its build, then the words carry on
            starts = [w.start for w in _spoken(lines, t0 + limit - 0.6, t1 - 0.8)]
            first = (starts[0] - 0.05) if starts else t0 + limit
            kept = dict(s, duration=first - t0)
            for key in ("steps", "items"):     # a step or item the shortened card no longer reaches is left out
                if kind in ("walkthrough", "checklist") and key in s["data"]:
                    times = s["data"]["steps"] if key == "steps" else s["data"].get("at") or []
                    keep = [i for i, x in enumerate(times) if (x["at"] if key == "steps" else x) < first - t0 - 0.6] or [0]
                    data = dict(s["data"], **{key: [s["data"][key][i] for i in keep]})
                    if key == "items":
                        data["at"] = [s["data"]["at"][i] for i in keep]
                    kept["data"] = data
            if fmt == "long":
                # 2026-11-14 (owner): a long video keeps the picture instead of cutting to word fragments
                # ("OLED efficient much image"); viewers found the words confusing
                out.append(s)
                continue
            out.append(kept)
            cuts = _cuts(lines, first, t1, beat)
            out.extend(_words_beat(lines, a, b) for a, b in zip(cuts, cuts[1:]))
            continue
        cuts = _cuts(lines, t0, t1, beat if kind != "host" else STUDIO_BEAT[fmt] * 0.7)
        for k, (a, b) in enumerate(zip(cuts, cuts[1:])):
            if kind == "browser_shot":
                photo = s["data"].get("photo")
                if k == 0:
                    out.append(dict(s, start=a, duration=b - a))
                elif k == 1:
                    out.append(dict(s, start=a, duration=b - a, data=dict(s["data"], zoomed=True)))
                elif k == 2 and photo:
                    out.append({"type": "photo", "start": a, "duration": b - a,
                                "data": {"image": photo, "url": s["data"].get("url", "")}})
                else:
                    out.append(_words_beat(lines, a, b))
            elif kind == "host":               # studio, then Goli steps aside for the words, then back
                out.append(_slice_host(s, a, b, lines, k == 0) if k % 2 == 0 else _words_beat(lines, a, b))
            else:
                out.append(_words_beat(lines, a, b))
    return sorted(out, key=lambda x: (x["start"], x["type"] == "host"))


def _crop_stats(image: Path, rect, scale: float = 1.5):
    from PIL import Image, ImageStat

    with Image.open(image) as im:
        x, y, w, h = rect
        box = (int(x * scale), int(y * scale), int((x + w) * scale), int((y + h) * scale))
        box = (max(0, box[0]), max(0, box[1]), min(im.width, box[2]), min(im.height, box[3]))
        if box[2] - box[0] < 8 or box[3] - box[1] < 8:
            return None
        return ImageStat.Stat(im.crop(box).convert("L"))


def _shows_something(image: Path, rect) -> bool:
    """A shot is worth zooming to only when it holds visible text or picture (contrast inside it)."""
    try:
        st = _crop_stats(image, rect)
    except Exception:  # noqa: BLE001
        return True
    return bool(st) and st.stddev[0] > 14


def _dark(image: Path) -> bool:
    try:
        from PIL import Image, ImageStat
        with Image.open(image) as im:
            return ImageStat.Stat(im.convert("L").resize((64, 64))).mean[0] < 90
    except Exception:  # noqa: BLE001
        return False


def _no_repeats(scenes: list[dict], lines, fmt: str, notes: list[str]) -> list[dict]:
    """Owner 2026-11-12: no repetition. A shot already shown is swapped for an unused place on the same
    page that best matches the beat's words; a Short never shows screenshots three times in a row; the same
    words never come back as a card."""
    used_rects: set[tuple] = set()
    used_words: set[str] = set()
    out, streak = [], 0
    page_run: list[str] = []     # 2026-11-13 (review): one page 3 or 4 times in a row looked stuck: at most 2
    for sc in scenes:
        kind = sc["type"]
        if kind == "browser_shot":
            url = str(sc["data"].get("url"))
            if page_run[-2:] == [url, url]:
                notes.append(f"page at {sc['start']:.1f}s shown twice in a row already, shown as words")
                sc = _words_beat(lines, sc["start"], sc["start"] + sc["duration"])
                kind, page_run = sc["type"], []
        if kind == "browser_shot":
            page_run.append(str(sc["data"].get("url")))
        elif kind != "host":
            page_run = []
        if kind == "browser_shot":
            hl = (sc["data"].get("highlights") or [{}])[0]
            key = (str(sc["data"].get("url")), tuple(hl.get("rect") or sc["data"].get("headline") or []))
            if key in used_rects:
                notes.append(f"shot at {sc['start']:.1f}s already used, shown as words")
                sc = _words_beat(lines, sc["start"], sc["start"] + sc["duration"])
                kind = sc["type"]
            else:
                used_rects.add(key)
        if kind == "browser_shot":
            streak += 1
            if fmt == "short" and streak > 2:
                sc = _words_beat(lines, sc["start"], sc["start"] + sc["duration"])
                kind, streak = sc["type"], 0
        elif kind != "host":
            streak = 0
        if kind == "kinetic_title":
            text = " ".join(w["text"].lower() for w in sc["data"]["words"])
            if text in used_words and out:
                notes.append(f"words at {sc['start']:.1f}s repeated, joined to the scene before")
                prev = next((o for o in reversed(out) if o["type"] != "host"), None)
                if prev is not None:
                    prev["duration"] = sc["start"] + sc["duration"] - prev["start"]
                    continue
            used_words.add(text)
        out.append(sc)
    return out


QUIET_TAGS = ("serious", "quietly", "whispers", "softly", "slowly", "sad", "sighs", "exhales")


def quiet_windows(voice_script: str, lines: list[Any], most: int = 2, longest: float = 12.0,
                  apart: float = 45.0) -> list[list[float]]:
    """2026-11-13 (owner, point 8): where the music drops out: the paragraphs the script marks as serious or quiet
    ([serious], [quietly], [whispers], [sighs]...), timed by the spoken lines they match. At most 3 a video, each
    at most 12 s, so the drop stays an effect."""
    import re as _re
    words = lambda t: _re.findall(r"[a-z0-9']+", str(t).lower())
    timed = [(words(getattr(l, "text", "")), float(getattr(l, "start", 0)), float(getattr(l, "end", 0))) for l in lines]
    out: list[list[float]] = []
    for para in _re.split(r"\n\s*\n", voice_script or ""):
        tags = " ".join(_re.findall(r"\[([^\]]+)\]", para[:120])).lower()
        if not any(t in tags for t in QUIET_TAGS):
            continue
        body = words(_re.sub(r"\[[^\]]*\]", " ", para))
        if len(body) < 4:
            continue
        head, tail = body[:4], body[-4:]
        start = next((a for w, a, b in timed if w[:4] == head or " ".join(head) in " ".join(w)), None)
        end = next((b for w, a, b in reversed(timed) if " ".join(tail) in " ".join(w)), None)
        if start is None or end is None or end <= start:
            continue
        if out and start - out[-1][1] < apart:      # 2026-11-13: never back to back (they chained over 15 s)
            continue
        out.append([round(start, 2), round(min(end, start + longest), 2)])
        if len(out) >= most:
            break
    return out


DEEPER = {"walkthrough", "terminal", "object3d", "recipe_clip", "puppet_clip"}
# 2026-11-17 (owner): no fixed counts for picture blocks: each one matches its words, never the same block twice in
# a row (and never the same metaphor twice in a video). Words blocks are the exception: at most 2 in a video.
# 2026-11-17 (owner): no text blocks. Text only where it IS the content: a real quote (quote_card), a prompt to
# copy (prompt_card), the key number (stat_counter); anything else is a picture
WORDS_MAX = 0


def _real_picture(path: Path) -> bool:
    """A picture worth a screen: not black, blank, a flat texture or a tiny icon (2026-11-25: the TV showed 4 black
    pictures from a news page and a grey texture)."""
    try:
        from PIL import Image, ImageFilter, ImageStat
        with Image.open(path) as im:
            if im.width < 320 or im.height < 180:
                return False
            g = im.convert("L").resize((160, 90))
        st = ImageStat.Stat(g)
        edges = ImageStat.Stat(g.filter(ImageFilter.FIND_EDGES)).mean[0]
        # a dark-mode app or terminal is dark but full of edges (2026-11-25: OpenCode's own screenshot); black is not
        light = 22 < st.mean[0] < 245 and st.stddev[0] > 20
        dark = st.mean[0] <= 22 and st.stddev[0] > 12 and edges > 12
        return (light or dark) and edges > 6
    except Exception:  # noqa: BLE001 - unreadable is not a picture
        return False


_SCREEN_STOP = set("this that with from have about your they their there what when which would could should into "
                   "just like then than them been were will also only more most some very much over even back".split())


def _screen_pictures(scenes: list[dict], sources: list[dict], capture_dir: Path | None, lines=None,
                     cues: list[dict] | None = None, notes: list[str] | None = None, look: str = "glass") -> list[dict]:
    """The studio TV (owner 2026-11-20, 2026-11-25): it shows the real thing being said. A picture goes on it only when
    its page names what the line names (the spoken words, 2026-11-25: the old match read the mouth cues, found no words
    and cycled 10 pictures in order), never a black, blank or texture picture, and never twice in a video unless it is
    the product itself (its page's subject is named in the line), at most 3 times. Otherwise the TV shows the line's
    own words with the key word lit (owner 2026-11-25: "add these to the TV"), never a meaningless chart.
    A laptop or phone shows the same kind of real picture on its own screen; with none it gives way to Goli and the TV
    (owner 2026-11-25: an empty screen is not real). Each 3D showing gets its own look and view."""
    notes = notes if notes is not None else []
    scenes = _object_variety(scenes, look)
    if not capture_dir:
        return _no_empty_screens(scenes, lines, cues, notes)
    pics: list[tuple[Path, set[str], set[str]]] = []
    seen: set[str] = set()
    for page in sources or []:
        title = str(page.get("title") or page.get("name") or "")
        who = str(page.get("subject") or page.get("product") or "")
        subject = {w for w in re.findall(r"[a-z0-9]+", who.lower()) if len(w) > 2}
        keys = {w for w in re.findall(r"[a-z0-9]+", (title + " " + who).lower())
                if len(w) > 3 and w not in _SCREEN_STOP}
        names = list(page.get("photos") or ([page["photo"]] if page.get("photo") else []))
        if page.get("product") and page.get("ok") and page.get("top"):
            names.insert(0, page["top"])      # 2026-11-25: the product's own page is the real thing on the TV
        for name in names:
            f = capture_dir / name
            if f.exists() and f.name not in seen and _real_picture(f):
                seen.add(f.name)
                pics.append((f, keys, subject))
    used: Counter = Counter()
    last = None
    for sc in scenes:
        d = sc["data"]
        if sc["type"] == "object3d" and d.get("object") in SCREEN_DEVICES:
            said = {w for w in re.findall(r"[a-z0-9]+", str(d.get("said") or "").lower()) if len(w) > 3 and w not in _SCREEN_STOP}
            best, score = None, 0
            for f, keys, subject in pics:
                product = bool(subject) and subject <= said
                if f == last or used[f] >= (3 if product else 1):
                    continue
                sc_ = len(keys & said) + (2 if product else 0)
                if sc_ > score:
                    best, score = f, sc_
            if best is not None:
                d["screen"], last = best, best
                used[best] += 1
    scenes = _no_empty_screens(scenes, lines, cues, notes)
    last = None
    for sc in scenes:
        d = sc["data"]
        if sc["type"] != "host" or d.get("place") != "studio" or d.get("intro") or d.get("outro"):
            continue
        said = {w for w in re.findall(r"[a-z0-9]+", " ".join(str(w.get("text") or "") for w in d.get("words") or []).lower())
                if len(w) > 3 and w not in _SCREEN_STOP}
        best, score = None, 0
        for f, keys, subject in pics:
            product = bool(subject) and subject <= said
            if f == last or used[f] >= (3 if product else 1):
                continue
            sc_ = len(keys & said) + (2 if product else 0)
            if sc_ > score:
                best, score = f, sc_
        if best is not None and score >= 1:
            d["screen"] = best
            d["words"], d["punch"] = [], ""     # the picture replaces the headline
            used[best] += 1
            last = best
        else:
            last = None                          # the line's own words stay on the TV
    return scenes


def _no_empty_screens(scenes: list[dict], lines, cues, notes: list[str]) -> list[dict]:
    """A laptop or phone with nothing real on its screen is not shown: Goli says the line with its words on the TV."""
    out = []
    for sc in scenes:
        d = sc["data"]
        if sc["type"] == "object3d" and d.get("object") in SCREEN_DEVICES and not d.get("screen"):
            notes.append(f"3D {d['object']} at {sc['start']:.1f}s: no real picture for its screen, Goli and the TV instead")
            host = _studio(sc["start"], sc["start"] + sc["duration"], cues)
            if lines is not None and d.get("said"):
                host["data"]["words"] = _screen_words(d["said"], lines, sc["start"], sc["start"] + sc["duration"])
            out.append(host)
        else:
            out.append(sc)
    return out


def _object_variety(scenes: list[dict], look: str) -> list[dict]:
    """Owner 2026-11-25 ("same way, same colour, same visual"): every 3D showing gets a look and a view that the one
    before did not have; the video's own look comes first."""
    order = [look] + [k for k in LOOKS3D if k != look]
    prev_look, n = None, 0
    for sc in sorted((s for s in scenes if s["type"] == "object3d"), key=lambda s: s["start"]):
        pick = order[n % len(order)]
        if pick == prev_look:
            pick = order[(n + 1) % len(order)]
        sc["data"]["look"], sc["data"]["view"] = pick, n % 4
        if sc["data"].get("object") == "laptop":     # owner 2026-11-25: smooth, real keys or neon keys, in turn
            sc["data"]["keys"] = ("neon", "none", "keys")[n % 3]
        prev_look, n = pick, n + 1
    return scenes


def _card_words(sc: dict | None) -> list[dict]:
    """The words a card carried (its number and label, title or text), for the studio screen when no picture fits."""
    if not sc:
        return []
    d = sc.get("data") or {}
    if d.get("words") and isinstance(d["words"], list) and all(isinstance(w, dict) for w in d["words"]):
        return [dict(w, at=0) for w in d["words"]][:6]
    text = " ".join(str(d.get(k) or "") for k in ("value", "label", "title", "text")).strip()
    return [{"text": w, "at": 0} for w in text.split()[:6]]


def _studio(start: float, end: float, cues: list[dict] | None, card: dict | None = None) -> dict:
    """Goli talking in the studio over [start, end): the picture a beat falls back to (never a held card). The card's
    words go on the studio screen unless a real picture takes it (never an empty wall)."""
    return {"type": "host", "start": round(start, 3), "duration": round(end - start, 3), "data": {
        "place": "studio", "cues": _cues_between(cues or [], start, end), "poses": [{"pose": "talk", "at": 0}],
        "words": _card_words(card), "punch": ""}}


# 2026-11-19 (owner review of the China EV video: "The factory advantage" and "40%" held ~9 s): a card shows for
# its read and Goli takes the rest of the beat
CARD_MAX = {"chapter_card": 2.0, "stat_counter": 3.0}


def _cap_cards(scenes: list[dict], lines, cues: list[dict] | None, notes: list[str]) -> list[dict]:
    """The last word on card length (owner 2026-11-25: a chapter card held 7.4 s while Goli stood beside it): after all
    the other passes a card that grew past its CARD_MAX is cut back; the rest of its time is Goli in the studio with the
    line on his TV, and a Goli standing beside the card stops with it."""
    out = list(scenes)
    limit = {id(x): _chapter_end(x, lines) if x["type"] == "chapter_card" else CARD_MAX.get(x["type"], 0) for x in scenes}
    for sc in [x for x in scenes if CARD_MAX.get(x["type"]) and x["duration"] > limit[id(x)] + (0.1 if x["type"] == "chapter_card" else 0.3)]:
        cut, end = sc["start"] + limit[id(sc)], sc["start"] + sc["duration"]
        sc["duration"] = round(limit[id(sc)], 3)
        for h in [x for x in out if x["type"] == "host" and x["data"].get("place") in ("side", "lower")
                  and x["start"] < end and x["start"] + x["duration"] > cut]:
            if h["start"] >= cut - 0.05:
                out.remove(h)
            else:
                h["duration"] = round(cut - h["start"], 3)
        text = " ".join(w.text for w in _spoken(lines, cut, end))
        out.append({"type": "host", "start": round(cut, 3), "duration": round(end - cut, 3), "data": {
            "place": "studio", "cues": _cues_between(cues or [], cut, end), "poses": [{"pose": "talk", "at": 0}],
            "words": _screen_words(text, lines, cut, end) if text else [], "punch": ""}})
        notes.append(f"{sc['type']} at {sc['start']:.1f}s held {end - sc['start']:.1f} s: cut to {limit[id(sc)]:.1f} s, then the studio")
    return sorted(out, key=lambda s: (s["start"], s["type"] == "host"))


def _chapter_end(sc: dict, lines) -> float:
    """Owner 2026-11-25 ("once you say 'let's go to step 5', the moment you start explaining that stage it has to
    leave"): a chapter card stays while its stage is being named and leaves on the last word that names it; 1-2 s."""
    t0 = sc["start"]
    want = {_norm(w) for w in re.findall(r"[A-Za-z0-9]+", str(sc["data"].get("title") or "")) if len(w) > 1}
    words = list(_spoken(lines, t0 - 0.2, t0 + 2.6))
    hit = [w for w in words if _norm(w.text) in want]
    if hit:
        last = hit[-1]
        end = float(getattr(last, "end", None) or float(last.start) + 0.35)
        return max(1.0, min(CARD_MAX["chapter_card"], end - t0 + 0.2))
    first = next((w for w in words if re.search(r"[.!?]$", w.text)), None)   # no title words said: its first sentence
    if first is not None:
        return max(1.0, min(CARD_MAX["chapter_card"], float(getattr(first, "end", None) or first.start + 0.3) - t0 + 0.2))
    return 1.6


def _short_cards(scenes: list[dict], notes: list[str], cues: list[dict] | None) -> list[dict]:
    out = []
    for sc in scenes:
        most = CARD_MAX.get(sc["type"])
        if most and sc["duration"] > most + 0.6:
            end = sc["start"] + sc["duration"]
            out.append(dict(sc, duration=most))
            out.append(_studio(sc["start"] + most, end, cues, sc))
            notes.append(f"{sc['type']} at {sc['start']:.1f}s: {most:.0f} s, then Goli")
        else:
            out.append(sc)
    return sorted(out, key=lambda s: (s["start"], s["type"] == "host"))


def _words_cap(scenes: list[dict], notes: list[str], fmt: str = "long", cues: list[dict] | None = None) -> list[dict]:
    """At most WORDS_MAX words blocks: any later one gives its time to the picture before it (the picture holds,
    owner 2026-11-14), or to the one after when it opens the video."""
    content = sorted((s for s in scenes if s["type"] != "host" or s["data"].get("place") == "studio"),
                     key=lambda s: s["start"])
    hosts = [s for s in scenes if s not in content]
    keep: list[dict] = []
    shown, pending = 0, None
    total = max((s["start"] + s["duration"] for s in scenes), default=0.0)
    stats_max, stats = (1 if fmt == "short" else max(1, int(total // 60))), 0
    last_stat = -999.0
    for sc in content:
        # the key number: 1 in a Short, 1 per minute of a long video and never two within a minute (2026-11-19: the
        # China EV video had 8 in its first minute); any more is Goli saying it
        if sc["type"] == "stat_counter":
            if stats + 1 > stats_max or (fmt != "short" and sc["start"] - last_stat < 60):
                notes.append(f"number at {sc['start']:.1f}s: one a minute, Goli says it")
                keep.append(_studio(sc["start"], sc["start"] + sc["duration"], cues, sc))
                continue
            stats, last_stat = stats + 1, sc["start"]
        if sc["type"] in TEXT_CARDS and not sc["data"].get("image"):    # steps on a real page are a picture
            if shown < WORDS_MAX:
                shown += 1
            elif keep and sc["start"] + sc["duration"] - keep[-1]["start"] > 4.0:
                # holding the picture before would sit still too long: Goli takes the beat
                notes.append(f"words at {sc['start']:.1f}s: Goli says it")
                keep.append(_studio(sc["start"], sc["start"] + sc["duration"], cues, sc))
                continue
            elif keep:
                notes.append(f"words at {sc['start']:.1f}s: the picture before holds instead")
                keep[-1]["duration"] = round(sc["start"] + sc["duration"] - keep[-1]["start"], 3)
                continue
            else:
                pending = sc
                continue
        if pending is not None:
            sc = dict(sc, start=pending["start"], duration=round(sc["start"] + sc["duration"] - pending["start"], 3))
            pending = None
        keep.append(sc)
    if pending is not None:
        keep.append(pending)
    return sorted(keep + hosts, key=lambda s: (s["start"], s["type"] == "host"))
# the shortest a picture may stay (a fast cut is still a picture the eye can read); the beat's words go on
MIN_SCENE = {"short": 1.0, "long": 1.5}
STRONG = {"zoom", "flash", "iris", "whip"}


# 2026-11-19 (owner review: "recipe scenes were not even lasting a second while the text blocks spent 2-3 s"): a
# recipe is the big picture of the video, so it plays long enough to watch; it takes the time from the scenes after it
RECIPE_MIN = {"short": 2.5, "long": 4.5}


def _recipe_time(scenes: list[dict], fmt: str, notes: list[str]) -> list[dict]:
    content = sorted((s for s in scenes if s["type"] != "host" or s["data"].get("place") == "studio"),
                     key=lambda s: s["start"])
    layers = [s for s in scenes if s not in content]
    total = max((s["start"] + s["duration"] for s in content), default=0.0)
    out: list[dict] = []
    i = 0
    while i < len(content):
        sc = dict(content[i])
        i += 1
        if sc["type"] == "recipe_clip" and sc["duration"] < RECIPE_MIN[fmt]:
            want = sc["start"] + RECIPE_MIN[fmt]
            while i < len(content) and content[i]["start"] < want - 0.05 and content[i]["type"] != "recipe_clip":
                nxt = content[i]
                end = nxt["start"] + nxt["duration"]
                if end - want < MIN_SCENE[fmt]:          # what is left of it is too short to read: the recipe takes it
                    want = max(want, end)
                    i += 1
                else:
                    content[i] = dict(nxt, start=round(want, 3), duration=round(end - want, 3))
                    break
            want = min(want, content[i]["start"] if i < len(content) else total)   # never past the next or the end
            if want > sc["start"] + sc["duration"] + 0.05:
                notes.append(f"recipe at {sc['start']:.1f}s: plays {want - sc['start']:.1f} s")
                sc["duration"] = round(want - sc["start"], 3)
        out.append(sc)
    return sorted(out + layers, key=lambda s: (s["start"], s["type"] == "host"))


def _min_length(scenes: list[dict], fmt: str) -> list[dict]:
    """A picture shorter than MIN_SCENE gives its time to the one before it (or after, at the start)."""
    content = sorted((s for s in scenes if s["type"] != "host"), key=lambda s: s["start"])
    keep: list[dict] = []
    for sc in content:
        if sc["duration"] >= MIN_SCENE[fmt] or not keep and sc is content[-1]:
            keep.append(sc)
            continue
        if keep and abs(keep[-1]["start"] + keep[-1]["duration"] - sc["start"]) < 0.08:
            keep[-1]["duration"] = round(sc["start"] + sc["duration"] - keep[-1]["start"], 3)
        else:
            keep.append(sc)          # nothing joined before it: it holds and the next short one joins it
    # a run of short ones at the very start became one too-short scene: it takes the next one's time
    out, i = [], 0
    while i < len(keep):
        sc = keep[i]
        if sc["duration"] < MIN_SCENE[fmt] and i + 1 < len(keep) and \
                abs(sc["start"] + sc["duration"] - keep[i + 1]["start"]) < 0.08:
            keep[i + 1] = dict(keep[i + 1], start=sc["start"],
                               duration=round(keep[i + 1]["start"] + keep[i + 1]["duration"] - sc["start"], 3))
            i += 1
            continue
        out.append(sc)
        i += 1
    return sorted(out + [s for s in scenes if s["type"] == "host"], key=lambda s: (s["start"], s["type"] == "host"))


def _transitions(scenes: list[dict], lines) -> None:
    """2026-11-13 (owner, point 6): how a scene comes in says how it relates to the one before:
    the same page going on -> match (cut, no movement); going deeper into the same thing (a page, then its steps, a
    real run or the device itself) -> zoom through; a big number -> gold flash; the answer to a question, or a
    lock/magnifier reveal -> iris; a turn in the argument ("But...", "However...") or a comparison -> whip; a new
    chapter -> wipe; otherwise the thought goes on -> push. Never the same one three times in a row."""
    content = [s for s in sorted(scenes, key=lambda s: s["start"]) if s["type"] != "host"]
    said = lambda t: " ".join(str(getattr(l, "text", "")) for l in lines
                              if getattr(l, "start", 0) <= t + 0.3 and getattr(l, "end", 0) >= t - 0.3).strip().lower()
    prev_said = lambda t: " ".join(str(getattr(l, "text", "")) for l in lines if getattr(l, "end", 0) <= t + 0.05)[-160:]
    used: list[str] = []
    for i, sc in enumerate(content):
        if i == 0 or sc.get("in") == "none":
            continue
        before, kind, t = content[i - 1], sc["type"], sc["start"]
        url = lambda x: str((x.get("data") or {}).get("url") or "")
        if kind == "chapter_card":
            how = "wipe"
        elif kind == before["type"] == "browser_shot" and url(sc) and url(sc) == url(before):
            how = "match"
        elif kind in DEEPER and before["type"] in ("browser_shot", "kinetic_title", "metaphor", "stat_counter"):
            how = "zoom"
        elif kind == "stat_counter":
            how = "flash"
        elif (kind == "metaphor" and (sc.get("data") or {}).get("kind") in ("unlock", "magnify")) or \
                prev_said(t).rstrip().endswith("?"):
            how = "iris"
        elif kind in ("comparison",) or ((sc.get("data") or {}).get("kind") == "scales") or \
                said(t).startswith(("but ", "however", "yet ", "instead")):
            how = "whip"
        else:
            how = "push"
        if used[-2:] == [how, how] and how not in ("match",):
            how = {"push": "wipe", "wipe": "push", "whip": "push", "zoom": "push", "iris": "push", "flash": "push"}[how]
        # 2026-11-13 (owner: "transitions should be smooth and meaningful"): a strong one (zoom, flash, iris, whip)
        # is a punctuation mark: at most one in three cuts; the rest flow (push, or a clean cut for a quick beat)
        if how in STRONG and any(u in STRONG for u in used[-2:]):
            how = "push"
        if how == "push" and sc["duration"] < 1.3:
            how = "match"
        if used and used[-1] == "match" and how == "match" and kind != before["type"] and len(used) > 1 and used[-2] == "match":
            how = "push"
        sc["in"] = how
        used.append(how)
