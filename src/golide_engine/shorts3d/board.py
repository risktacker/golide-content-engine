"""The 3D Short storyboard: an open film plan for ANY script (owner 2026-11-23).

Owner 2026-11-23: "You don't know what's coming with another script, but you are prepared to make whatever will come."
Nothing here is a set, a prop list or a topic. Sol directs the script like a film: the place it happens in (built from
ground, sky and walls), every thing the words name (found by name in free CC0 model libraries, or built from 3D parts
when no library has it), the people and what each one DOES on which word (walk to it, pick it up, throw it, ride it,
fall), what the things do (move, spin, break, bend, appear) and the shots. Only the body moves are a fixed vocabulary
(the puppet's controls, like an animator's); every noun and every place is free text.

One call per Short, at most COST_CAP_USD (owner 2026-11-22), the provider's re-ask off; everything Sol gets wrong is
repaired here for free and the director (assets/shorts3d/director.js) frames and checks every shot.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

COST_CAP_USD = 0.86
PRICE_IN, PRICE_OUT = 4.0 / 1e6, 20.0 / 1e6        # gpt-5.6-sol (config/provider-pricing.json)

# the puppet's controls (verbs). Targets and props are free: any thing id, any person id or a spot [x, z].
DOES = ["stand", "walk", "run", "turn", "hold", "pick-up", "put-down", "give", "throw", "kick", "push", "pull",
        "sit", "lie", "fall", "jump", "ride", "use", "point", "wave", "cheer", "hands-on-head", "scratch-head",
        "shrug", "nod", "shake-head", "lean-in", "arms-crossed", "look", "sneak", "hide", "hands-on-hips", "kneel",
        "cry", "facepalm", "lean-back", "work", "carry"]
# what a thing can do on a word
THING_DOES = ["move", "spin", "shake", "bend", "break", "tilt", "fall", "grow", "shrink", "appear", "vanish", "glow",
              "smoke", "fire", "text"]
FACES = ["calm", "smug", "grin", "wide", "pale", "squint", "laugh", "serious", "shout", "listen", "flat"]
OUTFITS = ["suit", "vest", "hoodie", "polo", "shirt", "bowtie", "uniform", "overalls", "coat", "dress", "jersey", "apron"]
PATTERNS = ["none", "stripes", "hstripes", "pinstripe", "plaid", "dots", "zigzag"]
HATS = ["none", "cap", "beret", "boonie", "pith", "helmet", "police", "hardhat", "chef", "cowboy", "beanie"]
SKIES = ["day", "dusk", "night", "overcast", "indoor"]
ANGLES = ["front", "low", "high", "left", "right", "over-shoulder", "top"]
LENSES = ["wide", "medium", "close", "extreme-close", "face"]
# the story job of every stretch (measured on Rick's films: the camera move follows the job, not the noun)
JOBS = ["hook", "setup", "talk", "act", "explain", "analogy", "turn", "place", "climax", "end"]
LIFE = ["none", "sway", "spin", "bob", "flutter", "smoke", "steam", "flicker", "drip", "roll"]
ROLES = ["story", "dressing", "detail", "gag"]
ARRANGE = ["scatter", "heap", "stack", "row"]
MOVES = ["push", "pull", "crane-down", "crane-up", "orbit-left", "orbit-right", "pan", "track", "whip", "dolly-zoom",
         "snap-zoom", "hold"]
BUBBLES = ["none", "?", "!", "$", "..."]
MIN_SHOT, MAX_SHOT = 1.0, 2.8                               # CLAUDE.md: no picture under 1.0 s; owner 2026-11-23: fast, like the references (a new picture every 1-2 s)
MAX_THINGS, MAX_CAST, MAX_CALLOUTS, MAX_COUNT, STAGE = 70, 14, 30, 60, 60.0                   # metres from the centre a spot may be


def _enum(values: list[str]) -> dict:
    return {"type": "string", "enum": values}


def schema() -> dict:
    """Strict JSON schema for the one Sol call. Nouns are free strings; only the controls are lists."""
    obj = lambda props: {"type": "object", "additionalProperties": False, "properties": props, "required": list(props)}
    s, num, i = {"type": "string"}, {"type": "number"}, {"type": "integer"}
    spot = {"type": "array", "items": num}
    strs = {"type": "array", "items": s}
    world = obj({"place": s, "indoor": {"type": "boolean"}, "ground": s, "ground_color": s, "walls_color": s,
                 "sky": _enum(SKIES), "size": spot, "light": _enum(["warm", "cool", "neutral"])})
    thing = obj({"id": s, "name": s, "role": _enum(ROLES), "search": s, "height_m": num, "at": spot, "on": s, "turn_deg": num,
                 "color": s, "parts": strs, "text": s, "hero": {"type": "boolean"}, "count": i, "spread": num,
                 "life": _enum(LIFE), "arrange": _enum(ARRANGE)})
    look = obj({"outfit": _enum(OUTFITS), "color": s, "accent": s, "pattern": _enum(PATTERNS), "hat": _enum(HATS),
                "glasses": {"type": "boolean"}})
    member = obj({"id": s, "label": s, "at": spot, "turn_deg": num, "look": look})
    beat = obj({"from": i, "until": i, "who": s, "do": _enum(DOES), "target": s, "to": spot, "with": s,
                "face": _enum(FACES), "bubble": _enum(BUBBLES), "says": {"type": "boolean"}})
    event = obj({"from": i, "until": i, "thing": s, "do": _enum(THING_DOES), "to": spot, "path": {"type": "array", "items": spot},
                 "amount": num, "text": s})
    landing = obj({"see": s, "from": i, "frame": strs, "near": s, "eye": s, "angle": _enum(ANGLES), "lens": _enum(LENSES),
                   "cam": spot, "aim": spot, "mm": num})
    # the picture plan, written first (the Ricks Clips kits' PICTURE_PLAN.md, column for column)
    row = obj({"job": _enum(JOBS), "mark": _enum(["none", "hook", "twist", "signature", "last-frame", "stillness"]),
               "words": s, "landing_word": i, "what_we_see": s, "shown": _enum(["close", "in-scene", "not-shown"]), "why": s,
               "light": s, "near_lens": s, "far_world": s, "feeling": s, "acted_gag": s, "effect": s})
    film = obj({"one_sentence": s, "cast_notes": s, "places_and_light": s, "colour_meaning": s, "speaking_lines": s,
                "extreme_gags": s, "power_moments": s, "impossible_view": s})
    move = obj({"from": i, "job": _enum(JOBS), "follow": s, "landings": {"type": "array", "items": landing}})
    callout = obj({"from": i, "until": i, "on": s, "text": s, "tone": _enum(["good", "bad", "neutral"])})
    return obj({"film": film, "plan": {"type": "array", "items": row}, "world": world, "things": {"type": "array", "items": thing}, "cast": {"type": "array", "items": member},
                "beats": {"type": "array", "items": beat}, "events": {"type": "array", "items": event},
                "callouts": {"type": "array", "items": callout}, "moves": {"type": "array", "items": move}})


def instructions() -> str:
    """What Sol is told. Method only (measured on Ricks Clips' films and the storyboard craft), never a topic."""
    return (
        "You are the director and storyboard artist of a 3D animated YouTube Short in the Ricks Clips style: white "
        "deadpan heads, pear bodies, noodle limbs, acting inside a detailed, lit 3D world. You do not know the topic in "
        "advance and nothing is pre-made: whatever the script says, you build and stage it. Your board is the only "
        "thing the engine draws: if it is not in the board, it is not on screen.\n\n"
        "HOW TO WORK. First read the whole script and decide, for every phrase: who is in it, what they are doing, "
        "what just changed, and what the viewer must feel. Then build the world, then the cast, then the acting, then "
        "the camera. A viewer watching once on a phone with the sound off must understand every moment from the "
        "picture alone: the thing the line names is visible when it is said.\n\n"
        "STEP 1, THE FILM (film): write it out in full sentences, as a storyboard artist's brief: the film in one "
        "sentence; every person in it (cast_notes: build, clothes in colour, the one trait that drives their acting, "
        "how they move and where they look, the mocker and the hero); every place and its light (places_and_light: "
        "what stands in it near and far, the visible light source and its colour, the time of day, how the light "
        "changes as the story goes on); the one colour that means one thing in this film (colour_meaning); every "
        "quoted line (speaking_lines: who says it and, word by word, where their eyes go, what the head does and "
        "what each hand does); the extreme gags (extreme_gags: every word of amount, size, speed or feeling taken "
        "literally, 10 to 100 times past real, built from this story's own objects, the best 2 to 4); the power "
        "moments (power_moments: the 2 to 4 words where something big happens on screen, with the effect that fits "
        "this scene); the impossible view (impossible_view: one picture from where no real camera could be, inside "
        "the object or the hidden place that matters most, and how the camera flies in and out).\n"
        "STEP 2, THE PICTURE PLAN (plan): one row for every thing or action the voice NAMES, in order. Each row: its "
        "story job; a mark (hook for the first picture, twist, the ONE signature picture of the film on the turn or "
        "climax, last-frame, or none); words: the exact words with the landing word in CAPITALS; landing_word: that "
        "word's number; what_we_see: the doer + the thing + the result, one action on the landing word, written so a "
        "builder could draw it (sizes, positions, what is nearest the lens, what each hand does, what changes); shown: "
        "close (the camera pushes in, the thing does something for about a second, then back to a face), in-scene "
        "(clearly in the frame on its word) or not-shown (only when showing it would break the scene); why: what "
        "this thing does in THIS story (the proof, the joke, the twist, the thing the hero touches, the number the "
        "viewer must believe), never \"the voice says it\"; light: the visible light source and how it has changed "
        "since the last row; near_lens: the real prop from this place nearest the lens; far_world: what stands behind; "
        "feeling: what the person in frame feels on that word, in plain words from this story (\"smug: he has heard "
        "this joke before\"), never a list word; acted_gag: who, the gag, its mechanism, readable with the sound off, "
        "no mechanism twice in the film, or none; effect: Rick's rule, measured: an effect marks a STORY FUNCTION and "
        "nothing else, one per row at most, on the word: a reveal gets a light sweep or a spotlight; a reward or prize "
        "carries its own light (glow from within, string bulbs); a count the voice speaks gets a number device ticking "
        "per word; a temptation lights the person's face; an impact gets a flash, a ring burst and a camera kick; speed "
        "gets speed lines; something special or valuable gets 4 to 6 small four-point stars at its edge; a change of "
        "mood or time changes the whole light (noon to sunset to night blue); a far catastrophe gets a dust plume, "
        "debris and scattering birds; everything else gets NO effect (80 percent of Rick's frames are clean). The effect "
        "grows out of this story's own objects, or none. Write every column in full: vague words "
        "(\"a mountain\", \"people react\", \"he works\") are a failure; say which, how big, where, doing what. A key "
        "number or term also goes on a sign or label in the world.\n"
        "STEP 3, BUILD IT: every row of the plan must be built by the data below: its things exist with their parts, "
        "its people do its action on its word, its effect is an event, its picture is a landing whose near is the "
        "row's near_lens prop. Nothing in the plan is left out of the data.\n"
        "WORLD: where the story happens (place: the script's own words), indoor or outdoor, the ground (what it is made "
        "of) and its colour (hex), walls colour for indoors, sky (day, dusk, night, overcast, indoor), size [width, "
        "depth] in metres (10 to 120), light warm/cool/neutral. Coordinates are metres: x left to right, z towards the "
        "viewer, the centre is [0, 0], ground at height 0. A story that moves between places builds each place in its "
        "own area of the world (tens of metres apart) so the camera can travel or cut between them.\n"
        "THINGS: every object, vehicle, building, animal, plant, piece of land, sign or screen. Each has an id, its plain "
        "name, a role (story: the script names it; dressing: it belongs in the place; detail: something only THIS place "
        "and time would have; gag: a small visual joke), search words a free 3D model library would file it under, its "
        "real height in metres, where it stands [x, z], on (another thing's id it sits on, or empty), turn in degrees, "
        "a colour (hex or empty) and parts: the thing built from simple 3D parts, one per line, \"name: "
        "box|cyl|sphere|cone x y z w d h [rx90] [#hex]\" (x, y on the ground, z up from its base, sizes w d h), 8 to 30 "
        "parts with real proportions, its own colours and FIVE details specific to this story and period (wear, lettering, marks, period "
        "parts, what is on it), used when no library has the thing; nothing generic: a plain box is a failure. Long things (a road, a rail line, a river, a fence, a bridge, a "
        "pipe, a wire) are one thing with their real length. text: words printed on it or empty. hero: true for the "
        "one or two things the story is about; give them the most parts. count and spread: one entry can stand for a "
        "cluster of the same thing (count 1 to 60 copies within spread metres, each turned and sized a little "
        "differently), and arrange says how: scatter (lying around), heap (piled into a mound, highest in the middle), "
        "stack (one on top of another), row (side by side in a line). life: the thing's own constant "
        "motion (sway, spin, bob, flutter, smoke, steam, flicker, drip, roll, or none).\n"
        "DENSITY, measured on Ricks Clips' frames: every place carries 30 or more kinds of things and hundreds of "
        "objects (use clusters), grouped big, medium and small around the action, never in lines or grids; at least 2 "
        "moving things in every view (life or events: smoke, flags, steam, flicker, dust, water, birds); 3 details only "
        "this place and time would have and 1 or 2 visual jokes; something big and close behind the subjects in every "
        "view (a wall, a machine, a vehicle, a tree), never open empty ground behind them.\n"
        "CAST: the people, 1 to 14. Each has an id, a role (label; a real person is never drawn as themselves: give a "
        "role), where they start [x, z], which way they face (turn_deg, 0 = towards the viewer) and a look that fits the "
        "role and makes them easy to tell apart (outfit, main colour and accent hex, pattern, hat, glasses). Besides the "
        "story's people, add background people who belong there, each busy with their own work all the time, so the "
        "place is alive.\n"
        f"BEATS (the acting): what each person does from word `from` until word `until`: do is one of {', '.join(DOES)}. "
        "target is the thing or person it is done to or towards (any id) or empty; to is a spot [x, z] to walk or run to, "
        "or []; with is a thing in their hands (held, carried, thrown, kicked, used, given, worked on) or empty. "
        f"A face ({', '.join(FACES)}) and a bubble (?, !, $, ... or none). says: true while this person speaks a line "
        "the script quotes (their mouth moves on those words). Act like an animator: every person in view is doing "
        "something on every phrase; a pose shows the attitude (hands on hips, leaning back, arms crossed) and changes "
        "only when the thought changes; the face is big and specific to the moment (smug, shocked, crying, laughing) "
        "and comes from what that person just saw or knows; two people never react the same way. Every action beat is "
        "an attention chain: the face, then the hands, then the object, then what happens, then someone's reaction. "
        "Hands end on the object; nothing floats; people stand beside furniture, not inside it.\n"
        f"EVENTS: what things do from word `from` until `until`: do is one of {', '.join(THING_DOES)}. move goes to `to` "
        "or along `path` (a list of spots); spin/shake/bend/tilt/grow/shrink use amount (degrees or times); break "
        "splits it; fall tips it over; appear/vanish; glow lights it; smoke/fire on it; text changes its printed words. "
        "People riding a thing move with it. Every change of state is caused by an action you show.\n"
        "CALLOUTS: small labels that pop up over a thing or a person on a word: a number, an amount, a price, a name or "
        "a status the script gives (at most 3 short words), tone good/bad/neutral, from word `from` until `until`.\n"
        "THE CAMERA, measured on Ricks Clips' films: ONE travelling camera that almost never cuts (a hard cut only "
        "when the story changes place or time), is moving about two thirds of the time, keeps catching moving things "
        "and lands on a new picture about every second. Write the camera as MOVES. A move starts on a word, has a "
        "story job and lasts as long as that job (often 3 to 12 seconds); inside it the camera flies from landing to "
        "landing without a cut. follow: the id of the thing or person the camera rides with during the move (a moving "
        "vehicle, a runner, a thrown thing), or empty. The job decides how it moves:\n"
        "- hook: land close on the strange act, then pull back and rise to reveal the big thing; two or three landings "
        "in the first 4 seconds.\n"
        "- setup (who, where, the stakes): one long travel along a line in the place (a road, a rail, a wall, a row) "
        "joining the places and people.\n"
        "- talk (someone speaks, mocks, argues): rest on the speaker and creep in; on the angry or smug word, a push in "
        "or a turn round them; then their listener's face.\n"
        "- act (the hero does or builds the thing): push to the hands, then travel over the object part by part: "
        "hands, part, part, result, the faces watching.\n"
        "- explain (\"you see\", how it works): travel along the mechanism like reading it, landing where the picture "
        "itself changes.\n"
        "- analogy (\"it's like\"): a new small place for the comparison, one long straight push to the point.\n"
        "- turn (\"but\", the twist): a slow pull back and rise that shows the whole thing.\n"
        "- place (a change of place or time): the new place, landing on its strongest detail.\n"
        "- climax (it happens): ride with the moving thing, then one fast push on the hit.\n"
        "- end: pull back from the result with the hero calm and big in front of it, then creep in on the face, "
        "matching the first picture so the Short loops.\n"
        "LANDINGS ARE CAMERA STATIONS (Rick's camera, measured): the camera rests on a station, then travels to the next "
        "and lands on its word; travel takes 1.5 s + 0.25 s per metre of camera path (at most 6 s), so write stations "
        "about 2.5 s or more apart inside a move (a new picture every 1 to 1.5 s comes from the travel itself and from "
        "the people acting, not from more stations). Write EVERY station exactly, the way a camera operator would: cam "
        "= where the camera stands [x, z, height in metres], aim = the point it looks at [x, z, height] (a face is at "
        "about 1.3 m, hands at about 0.9 m, a thing at its middle), mm = the lens (24 wide, 35 medium, 50 close, 85 a "
        "face). You placed every person and thing, so you know where they are: put the camera where the picture of "
        "the plan row is (low at rail height for a low view, 2 m in front of a face for a face, high above for the "
        "place). Keep the camera out of things and people, in front of the near-lens prop's far side so the prop is "
        "between lens and subject, and never with a wall between camera and subject. Each landing first says in one plain sentence what the "
        "picture shows (see: the subject, its action, what is close in front and what stands behind), then frame (the "
        "ids it is about: what that moment is about, sized so it reads), near (the id of the prop nearest the lens, "
        "from the plan row; the camera looks past it), eye (for the plan's impossible view or a point of view: the "
        "id of the thing the camera sits INSIDE, looking out at the frame, or empty), angle and lens. Vary the size from landing "
        "to landing (wide, medium, close, extreme-close on the thing in action, face for every reaction); never the "
        "same size and angle on the same person three times in a row; a face in view within the first 1.5 seconds. "
        "Keep the camera on one side of the action within a place (the 180-degree rule). "
        "Angles: " + ", ".join(ANGLES) + ". Lenses: " + ", ".join(LENSES) + ".\n"
        "All `from` and `until` values are word numbers from the list you are given; beats, events, moves and their "
        "landings in time order. Only facts from the script. Return JSON."
    )


def request(title: str, words: list[dict], phrases: list[dict]) -> str:
    numbered = " ".join(f"{i}:{w['word']}" for i, w in enumerate(words))
    starts = "; ".join(f"{p['from']} ({p['start']:.1f}s) {p['text']}" for p in phrases)
    return (f"TITLE: {title}\nLENGTH: {words[-1]['end']:.1f} seconds\n\nWORDS (number:word):\n{numbered}\n\n"
            f"PHRASE STARTS (word number, time, phrase):\n{starts}\n")


def phrases(words: list[dict], gap: float = 0.25) -> list[dict]:
    """The voice in phrases (a new phrase after punctuation or a pause), each with its first word number."""
    out, cur = [], []
    for i, w in enumerate(words):
        if cur and (re.search(r"[,.;:!?]$", words[i - 1]["word"]) or w["start"] - words[i - 1]["end"] > gap):
            out.append(cur); cur = []
        cur.append(i)
    if cur:
        out.append(cur)
    return [{"from": p[0], "start": words[p[0]]["start"], "text": " ".join(words[i]["word"] for i in p)} for p in out]


def max_output_tokens(input_tokens: int) -> int:
    """The output limit that keeps one call under the cap whatever happens."""
    return max(4000, int((COST_CAP_USD - input_tokens * PRICE_IN) / PRICE_OUT) - 500)


def estimate_input_tokens(text: str) -> int:
    return int(len(text) / 3.2) + 200


def write(text_provider, title: str, words: list[dict]) -> tuple[dict, Any]:
    """The one paid call. Returns (storyboard, provider output with token counts)."""
    ins, req = instructions(), request(title, words, phrases(words))
    limit = max_output_tokens(estimate_input_tokens(ins + req))
    out = text_provider.generate_json(ins, req, schema(), max_output_tokens=limit, grow=False)
    return out.value, out


# ---------------- free repairs ----------------
def _hex(v: Any, default: str) -> str:
    return v if isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v) else default


def _id(v: Any, fallback: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "", str(v or "").lower())[:24] or fallback


def _num(v: Any, default: float, lo: float, hi: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(x) else max(lo, min(hi, x))


def _spot(v: Any, half: tuple[float, float] | None = None) -> list[float] | None:
    if not isinstance(v, (list, tuple)) or len(v) < 2:
        return None
    try:
        x, z = float(v[0]), float(v[1])
    except (TypeError, ValueError):
        return None
    hx, hz = half or (STAGE, STAGE)
    return [round(max(-hx, min(hx, x)), 3), round(max(-hz, min(hz, z)), 3)]


def _pick(v: Any, allowed: list[str], default: str) -> str:
    return v if v in allowed else default


def _station(s: dict) -> dict:
    """A camera station the storyboard wrote: [x, z, height] for the camera and for its aim, and the lens in mm."""
    def p3(v):
        try:
            x, z, h = (float(q) for q in v[:3])
        except (TypeError, ValueError):
            return None
        return [round(max(-300, min(300, x)), 3), round(max(-300, min(300, z)), 3), round(max(0.05, min(150, h)), 3)]
    cam, aim = p3(s.get("cam") or []), p3(s.get("aim") or [])
    if not cam or not aim or cam == aim:
        return {"cam": [], "aim": [], "mm": 0}
    return {"cam": cam, "aim": aim, "mm": _num(s.get("mm"), 35, 12, 135)}


def _job_move(job: str, k: int, n: int) -> str:
    """The camera move of the k-th of n landings in a move with this story job (Rick's camera by situation)."""
    last = k == n - 1
    return {"hook": "push" if k == 0 else "crane-up" if k == 1 else "push",
            "setup": "track" if k % 2 == 0 else "pan",
            "talk": "push" if k % 2 == 0 else "orbit-left",
            "act": "push" if k == 0 else "track",
            "explain": "track",
            "analogy": "push",
            "turn": "pull" if k == 0 else "crane-up",
            "place": "crane-down" if k == 0 else "push",
            "climax": "track" if not last else "snap-zoom",
            "end": "pull" if not last else "push"}.get(job, "push")


def _landings(b: dict) -> list[dict]:
    """Flatten the camera moves into landings (take = which move, so landings of one move fly, takes cut)."""
    out = []
    for mi, m in enumerate(b.get("moves") or []):
        ls = [x for x in (m.get("landings") or []) if isinstance(x, dict)]
        if not ls:
            continue
        ls[0] = {**ls[0], "from": m.get("from", ls[0].get("from"))}
        for k, x in enumerate(ls):
            out.append({**x, "take": mi, "job": m.get("job"), "follow": m.get("follow", ""),
                        "move": _job_move(m.get("job"), k, len(ls))})
    if not out:                                   # an older board: every shot is its own take
        out = [{**x, "take": i} for i, x in enumerate(b.get("shots") or [])]
    return out


def repair(board: dict, words: list[dict]) -> tuple[dict, list[str]]:
    """Make any storyboard buildable without asking again. Returns the board and what was changed."""
    notes: list[str] = []
    n = len(words)
    b = json.loads(json.dumps(board or {}))
    clampw = lambda v: max(0, min(n - 1, int(_num(v, 0, 0, n - 1))))

    w = b.get("world") or {}
    size = w.get("size") if isinstance(w.get("size"), (list, tuple)) and len(w.get("size")) >= 2 else [30, 30]
    size = [_num(size[0], 30, 10, 120), _num(size[1], 30, 10, 120)]
    half = (size[0] / 2, size[1] / 2)
    indoor = bool(w.get("indoor"))
    b["world"] = {"place": str(w.get("place") or "")[:120], "indoor": indoor, "ground": str(w.get("ground") or "")[:80],
                  "ground_color": _hex(w.get("ground_color"), "#b9b2a4" if indoor else "#8fae6b"),
                  "walls_color": _hex(w.get("walls_color"), "#d9d2c3"),
                  "sky": "indoor" if indoor else _pick(w.get("sky"), SKIES[:-1], "day"),
                  "size": size, "light": _pick(w.get("light"), ["warm", "cool", "neutral"], "warm")}

    things, tids = [], set()
    for k, t in enumerate((b.get("things") or [])[:MAX_THINGS]):
        tid = _id(t.get("id"), f"t{k + 1}")
        while tid in tids:
            tid += "x"
        name = re.sub(r"\s+", " ", str(t.get("name") or tid)).strip()[:60]
        parts = [str(p)[:120] for p in (t.get("parts") or []) if isinstance(p, str) and ":" in p][:40]
        at = _spot(t.get("at"), half)
        if at is None:
            at = [0.0, 0.0]; notes.append(f"{tid} had no spot, put at the centre")
        things.append({"id": tid, "name": name, "role": _pick(t.get("role"), ROLES, "dressing"), "count": int(_num(t.get("count"), 1, 1, MAX_COUNT)),
                       "spread": _num(t.get("spread"), 0, 0, 30), "life": _pick(t.get("life"), LIFE, "none"), "arrange": _pick(t.get("arrange"), ARRANGE, "scatter"), "search": str(t.get("search") or name)[:80],
                       "height_m": _num(t.get("height_m"), 1.0, 0.02, 200), "at": at, "on": _id(t.get("on"), ""),
                       "turn_deg": _num(t.get("turn_deg"), 0, -360, 360), "color": _hex(t.get("color"), ""),
                       "parts": parts, "text": str(t.get("text") or "")[:40], "hero": bool(t.get("hero"))})
        tids.add(tid)
    for t in things:
        if t["on"] and (t["on"] not in tids or t["on"] == t["id"]):
            t["on"] = ""
    b["things"] = things

    cast, cids = [], set()
    for k, m in enumerate((b.get("cast") or [])[:MAX_CAST]):
        cid = _id(m.get("id"), f"p{k + 1}")
        while cid in cids or cid in tids:
            cid += "p"
        at = _spot(m.get("at"), half) or [round(-1.5 + 1.5 * k, 3), 1.0]
        L = m.get("look") or {}
        cast.append({"id": cid, "label": str(m.get("label") or cid)[:60], "at": at,
                     "turn_deg": _num(m.get("turn_deg"), 0, -360, 360),
                     "look": {"outfit": _pick(L.get("outfit"), OUTFITS, "shirt"), "color": _hex(L.get("color"), "#2f3542"),
                              "accent": _hex(L.get("accent"), "#c8352f"), "pattern": _pick(L.get("pattern"), PATTERNS, "none"),
                              "hat": _pick(L.get("hat"), HATS, "none"), "glasses": bool(L.get("glasses"))}})
        cids.add(cid)
    if not cast and not things:
        raise ValueError("storyboard: nobody and nothing to show")
    b["cast"] = cast
    ids = cids | tids

    beats = []
    for x in b.get("beats") or []:
        if x.get("who") not in cids:
            continue
        do = _pick(x.get("do"), DOES, "stand")
        target = x.get("target") if x.get("target") in ids and x.get("target") != x.get("who") else ""
        to = _spot(x.get("to"), half)
        held = x.get("with") if x.get("with") in tids else ""
        if do in ("walk", "run", "sneak") and not to and not target:
            notes.append(f"{x['who']} {do} at word {x.get('from')} had nowhere to go: stands"); do = "stand"
        if do in ("throw", "kick", "give", "hold", "use", "put-down") and not held:
            held = target if target in tids else ""
            if not held:
                notes.append(f"{x['who']} {do} at word {x.get('from')} had nothing to {do}: points"); do = "point"
        if do == "give" and target not in cids:
            do = "put-down" if held else "point"
        if do == "ride" and target not in tids:
            notes.append(f"{x['who']} ride at word {x.get('from')} had nothing to ride: stands"); do = "stand"
        f = clampw(x.get("from"))
        beats.append({"from": f, "until": max(f, clampw(x.get("until") if x.get("until") is not None else f)), "who": x["who"],
                      "do": do, "target": target, "to": to or [], "with": held,
                      "face": _pick(x.get("face"), FACES, "calm"), "bubble": _pick(x.get("bubble"), BUBBLES, "none"), "says": bool(x.get("says"))})
    b["beats"] = sorted(beats, key=lambda x: x["from"])

    events = []
    for e in b.get("events") or []:
        if e.get("thing") not in tids:
            continue
        do = _pick(e.get("do"), THING_DOES, "")
        if not do:
            continue
        path = [p for p in (_spot(q, half) for q in (e.get("path") or [])) if p]
        to = _spot(e.get("to"), half)
        if do == "move" and not to and not path:
            notes.append(f"{e['thing']} move at word {e.get('from')} had nowhere to go, dropped"); continue
        f = clampw(e.get("from"))
        events.append({"from": f, "until": max(f, clampw(e.get("until") if e.get("until") is not None else f)), "thing": e["thing"],
                       "do": do, "to": to or [], "path": path[:24], "amount": _num(e.get("amount"), 1, -3600, 3600),
                       "text": str(e.get("text") or "")[:40]})
    b["events"] = sorted(events, key=lambda e: e["from"])

    b["film"] = {k: str(v)[:4000] for k, v in (b.get("film") or {}).items() if isinstance(v, str)}
    b["plan"] = [r for r in (b.get("plan") or []) if isinstance(r, dict)][:120]
    b["callouts"] = sorted([{"from": clampw(c.get("from")), "until": max(clampw(c.get("from")), clampw(c.get("until") if c.get("until") is not None else c.get("from"))),
                             "on": c["on"], "text": re.sub(r"\s+", " ", str(c.get("text") or "")).strip()[:24],
                             "tone": _pick(c.get("tone"), ["good", "bad", "neutral"], "neutral")}
                            for c in (b.get("callouts") or [])[:MAX_CALLOUTS] if c.get("on") in ids and str(c.get("text") or "").strip()],
                           key=lambda c: c["from"])

    # shots: on word starts, 1.0-2.0 s, never the same angle twice in a row, framing known ids
    end = words[-1]["end"]
    first = (cast[0]["id"] if cast else things[0]["id"])
    shots = []
    for s in sorted(_landings(b), key=lambda s: int(_num(s.get("from"), 0, 0, n))):
        frame = [x for x in (s.get("frame") or []) if x in ids][:4]
        if not frame:
            notes.append(f"landing at word {s.get('from')} framed nothing known, dropped"); continue
        shots.append({"from": clampw(s.get("from")), "frame": frame, "angle": _pick(s.get("angle"), ANGLES, "front"),
                      "lens": _pick(s.get("lens"), LENSES, "medium"), "move": _pick(s.get("move"), MOVES, "push"),
                      "take": int(s.get("take", len(shots))), "job": _pick(s.get("job"), JOBS, "act"),
                      "follow": s.get("follow") if s.get("follow") in ids else "", "see": str(s.get("see") or "")[:300],
                      "near": s.get("near") if s.get("near") in tids and s.get("near") not in frame else "",
                      "eye": s.get("eye") if s.get("eye") in tids and s.get("eye") not in frame else "",
                      **_station(s)})
    if not shots:
        shots = [{"from": 0, "frame": [first], "angle": "front", "lens": "wide", "move": "push"}]
        notes.append("no usable shots: one shot on the first person or thing")
    shots[0]["from"] = 0
    t = lambda i: words[i]["start"]
    merged = []
    for s in shots:                                   # too short: folded into the shot before
        if merged and t(s["from"]) - t(merged[-1]["from"]) < MIN_SHOT:
            notes.append(f"shot at word {s['from']} under {MIN_SHOT}s, merged"); continue
        merged.append(s)
    if len(merged) > 1 and end - t(merged[-1]["from"]) < MIN_SHOT:
        merged.pop(); notes.append("last shot under the minimum, merged")
    out = []
    for i, s in enumerate(merged):                    # too long: split at word starts, a new angle each part
        stop = t(merged[i + 1]["from"]) if i + 1 < len(merged) else end
        out.append(s)
        cur = s
        while stop - t(cur["from"]) > (7.0 if cur.get("cam") else MAX_SHOT):   # a written station rests and drifts (Rick: 2.5 s and up)
            nxt = next((j for j in range(cur["from"] + 1, n) if t(j) - t(cur["from"]) >= 1.2), None)
            if nxt is None or stop - t(nxt) < MIN_SHOT:
                break
            cur = {**cur, "from": nxt, "angle": ANGLES[(ANGLES.index(cur["angle"]) + 2) % 5],
                   "move": "orbit-left" if cur["move"] != "orbit-left" else "orbit-right", "see": ""}
            out.append(cur); notes.append(f"long shot split at word {nxt}")
    for a, c in zip(out, out[1:]):
        if a["angle"] == c["angle"] and a["lens"] == c["lens"]:
            c["angle"] = ANGLES[(ANGLES.index(c["angle"]) + 1) % len(ANGLES)]
    b["shots"] = out
    return b, notes
