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
        "shrug", "nod", "shake-head", "lean-in", "arms-crossed", "look", "sneak", "hide"]
# what a thing can do on a word
THING_DOES = ["move", "spin", "shake", "bend", "break", "tilt", "fall", "grow", "shrink", "appear", "vanish", "glow",
              "smoke", "fire", "text"]
FACES = ["calm", "smug", "grin", "wide", "pale", "squint", "laugh", "serious", "shout", "listen", "flat"]
OUTFITS = ["suit", "vest", "hoodie", "polo", "shirt", "bowtie", "uniform", "overalls", "coat", "dress", "jersey", "apron"]
PATTERNS = ["none", "stripes", "hstripes", "pinstripe", "plaid", "dots", "zigzag"]
HATS = ["none", "cap", "beret", "boonie", "pith", "helmet", "police", "hardhat", "chef", "cowboy", "beanie"]
SKIES = ["day", "dusk", "night", "overcast", "indoor"]
ANGLES = ["front", "low", "high", "left", "right", "over-shoulder", "top"]
LENSES = ["wide", "medium", "close", "extreme-close"]
MOVES = ["push", "pull", "crane-down", "crane-up", "orbit-left", "orbit-right", "pan", "track", "whip", "dolly-zoom",
         "snap-zoom", "hold"]
BUBBLES = ["none", "?", "!", "$", "..."]
MIN_SHOT, MAX_SHOT = 1.0, 3.5                               # CLAUDE.md pace: no picture under 1.0 s; engine: 2-3.5 s
MAX_THINGS, MAX_CAST, STAGE = 30, 6, 60.0                   # metres from the centre a spot may be


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
    thing = obj({"id": s, "name": s, "search": s, "height_m": num, "at": spot, "on": s, "turn_deg": num,
                 "color": s, "parts": strs, "text": s, "hero": {"type": "boolean"}})
    look = obj({"outfit": _enum(OUTFITS), "color": s, "accent": s, "pattern": _enum(PATTERNS), "hat": _enum(HATS),
                "glasses": {"type": "boolean"}})
    member = obj({"id": s, "label": s, "at": spot, "turn_deg": num, "look": look})
    beat = obj({"from": i, "until": i, "who": s, "do": _enum(DOES), "target": s, "to": spot, "with": s,
                "face": _enum(FACES), "bubble": _enum(BUBBLES)})
    event = obj({"from": i, "until": i, "thing": s, "do": _enum(THING_DOES), "to": spot, "path": {"type": "array", "items": spot},
                 "amount": num, "text": s})
    shot = obj({"from": i, "frame": strs, "angle": _enum(ANGLES), "lens": _enum(LENSES), "move": _enum(MOVES)})
    return obj({"world": world, "things": {"type": "array", "items": thing}, "cast": {"type": "array", "items": member},
                "beats": {"type": "array", "items": beat}, "events": {"type": "array", "items": event},
                "shots": {"type": "array", "items": shot}})


def instructions() -> str:
    return (
        "You are the film director of a 3D animated YouTube Short in the Ricks Clips style: white deadpan heads, pear "
        "bodies, noodle limbs, real lit 3D places. The narrator speaks; nobody's mouth talks; the people and the things "
        "ACT exactly what the words say. Whatever the script is about, you build it: you do not know the topic in "
        "advance and nothing is pre-made. If a line says someone plays with a ball, a ball is there and they kick it; "
        "if it says a vehicle crosses a place, that vehicle crosses that place. Never put the story somewhere it is "
        "not, never show a thing the script does not need, never stand in a symbol for a thing you can show.\n\n"
        "WORLD: where the story happens, in the script's own words (place: free text), indoor or outdoor, the ground "
        "(free words: what it is made of) and its colour (hex), walls colour for indoors, sky (day, dusk, night, "
        "overcast, indoor), size [width, depth] in metres (10 to 120), light warm/cool/neutral. Coordinates are metres: "
        "x left to right, z towards the viewer, the centre of the place is [0, 0], ground at height 0.\n"
        "THINGS: every object, vehicle, building, animal, plant, piece of land or screen the script needs, each with an "
        "id, its plain name, search words a free 3D model library would file it under (\"steam locomotive train\", "
        "\"soccer ball\"), its real height in metres, where it is [x, z], on (another thing's id it sits on, or empty), "
        "turn in degrees, a colour (hex or empty), and parts: the thing built from simple 3D parts, one per line, "
        "\"name: box|cyl|sphere|cone x y z w d h [rx90] [#hex]\" (x, y on the ground, z up from its base, sizes w d h), "
        "6 to 30 parts that make it recognisable, used when no library has the thing. Long things (a road, a rail "
        "line, a river, a fence, a bridge) are one thing with their real length. text: words printed on it (a sign, a "
        "screen, a newspaper) or empty. hero: true for the one or two things the story is about.\n"
        "CAST: the people, 1 to 6, each with an id, a role (label; real people are never drawn as themselves: give a "
        "role), where they start [x, z], which way they face (turn_deg, 0 = towards the viewer) and a look that fits "
        "the role (outfit, main colour and accent hex, pattern, hat, glasses). Make each person easy to tell apart.\n"
        f"BEATS: what each person does, from word number `from` until word `until`: do is one of {', '.join(DOES)}. "
        "target is the thing or person it is done to or towards (any id) or empty; to is a spot [x, z] to walk or run "
        "to, or []; with is a thing in their hands (held, thrown, kicked, used, given) or empty. walk/run need to or a "
        "target; ride puts them on or in a thing that moves; give passes `with` to `target`; throw and kick send `with` "
        f"to `to` or `target`. A face ({', '.join(FACES)}) and a bubble (?, !, $, ... or none). Every line of the voice "
        "has a matching action on screen; gestures (cheer, shrug, point) are reactions, never the whole story.\n"
        f"EVENTS: what things do, from word `from` until `until`: do is one of {', '.join(THING_DOES)}. move goes to "
        "`to` or along `path` (a list of spots); spin/shake/bend/tilt/grow/shrink use amount (degrees or times); break "
        "splits it; fall tips it over; appear/vanish; glow lights it; smoke/fire on it; text changes the words printed "
        "on it to `text`. People riding a thing move with it.\n"
        "SHOTS: a new shot starts on the FIRST word of a phrase (use the phrase starts given). Each lasts 1.5 to 3.5 "
        "seconds; every shot moves; never the same angle twice in a row. frame = the ids (people and things) the shot "
        "is about. Plan like a director: establish the place with a crane-down, a low push-in on the hero, an "
        "over-the-shoulder insert on what they look at, an extreme close-up with a snap-zoom on the key action, a whip "
        "between reactions, a dolly-zoom on the \"oh no\". Angles: " + ", ".join(ANGLES) + ". Lenses: "
        + ", ".join(LENSES) + ". Moves: " + ", ".join(MOVES) + ".\n"
        "All `from` and `until` values are word numbers from the list you are given; beats, events and shots in time "
        "order. Only facts from the script. Return JSON."
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
        things.append({"id": tid, "name": name, "search": str(t.get("search") or name)[:80],
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
                      "face": _pick(x.get("face"), FACES, "calm"), "bubble": _pick(x.get("bubble"), BUBBLES, "none")})
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

    # shots: on word starts, 1.0-3.5 s, never the same angle twice in a row, framing known ids
    end = words[-1]["end"]
    first = (cast[0]["id"] if cast else things[0]["id"])
    shots = []
    for s in sorted(b.get("shots") or [], key=lambda s: int(_num(s.get("from"), 0, 0, n))):
        frame = [x for x in (s.get("frame") or []) if x in ids][:4]
        if not frame:
            notes.append(f"shot at word {s.get('from')} framed nothing known, dropped"); continue
        shots.append({"from": clampw(s.get("from")), "frame": frame, "angle": _pick(s.get("angle"), ANGLES, "front"),
                      "lens": _pick(s.get("lens"), LENSES, "medium"), "move": _pick(s.get("move"), MOVES, "push")})
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
        while stop - t(cur["from"]) > MAX_SHOT:
            nxt = next((j for j in range(cur["from"] + 1, n) if t(j) - t(cur["from"]) >= 2.2), None)
            if nxt is None or stop - t(nxt) < MIN_SHOT:
                break
            cur = {**cur, "from": nxt, "angle": ANGLES[(ANGLES.index(cur["angle"]) + 2) % 5],
                   "move": "orbit-left" if cur["move"] != "orbit-left" else "orbit-right"}
            out.append(cur); notes.append(f"long shot split at word {nxt}")
    for a, c in zip(out, out[1:]):
        if a["angle"] == c["angle"]:
            c["angle"] = ANGLES[(ANGLES.index(c["angle"]) + 1) % len(ANGLES)]
    b["shots"] = out
    return b, notes
