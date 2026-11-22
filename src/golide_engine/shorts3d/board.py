"""The 3D Short storyboard (owner plan 2026-11-22, step 4).

Sol writes ONE storyboard per Short, as data (never code): the set, 2-4 people and where they stand, what each does on
which word, what the wall TV shows, and the shots (who, angle, lens, move) on the real word timings. It is saved at once
and never paid for twice (owner 2026-11-22: "I ain't paying for retries"); everything Sol gets wrong is repaired here for
free (unknown names, shot lengths, two people on one spot) and the director (assets/shorts3d/director.js) frames and
checks every shot. Cost cap: one call, at most COST_CAP_USD (owner 2026-11-22: "should always cost 0.86"), enforced by
the output limit, with the provider's automatic re-ask switched off.
"""
from __future__ import annotations

import json
import re
from typing import Any

COST_CAP_USD = 0.86
PRICE_IN, PRICE_OUT = 4.0 / 1e6, 20.0 / 1e6        # gpt-5.6-sol (config/provider-pricing.json)
SETS = ("office", "home")
OFFICE_PLACES = [f"desk-{k}{s}" for k in range(1, 5) for s in ("", "-left", "-right")] + [f"open-{i}" for i in range(1, 7)]
HOME_PLACES = ["sofa", "table-left", "table-right", "kitchen"] + [f"open-{i}" for i in range(1, 7)]
ACTS = ["stand", "type", "cheer", "hands-on-head", "scratch-head", "point", "wave", "laugh", "shrug", "nod", "lean-in", "arms-crossed"]
FACES = ["calm", "smug", "grin", "wide", "pale", "squint", "laugh", "serious", "shout", "listen", "flat"]
OUTFITS = ["suit", "vest", "hoodie", "polo", "shirt", "bowtie"]
PATTERNS = ["none", "stripes", "hstripes", "pinstripe", "plaid", "dots", "zigzag"]
HATS = ["none", "cap", "beret", "boonie", "pith"]
ANGLES = ["front", "low", "high", "left", "right"]          # back views are left out: faces carry these stories
LENSES = ["wide", "medium", "close"]
MOVES = ["push", "pull", "crane-down", "crane-up", "orbit-left", "orbit-right", "dolly-zoom", "hold"]
BUBBLES = ["none", "?", "!", "$"]
MIN_SHOT, MAX_SHOT = 1.0, 3.5                               # CLAUDE.md pace: no picture under 1.0 s; skill: 2-3.5 s


def _enum(values: list[str]) -> dict:
    return {"type": "string", "enum": values}


def schema() -> dict:
    """Strict JSON schema for the one Sol call."""
    obj = lambda props: {"type": "object", "additionalProperties": False, "properties": props, "required": list(props)}
    look = obj({"outfit": _enum(OUTFITS), "color": {"type": "string"}, "accent": {"type": "string"}, "pattern": _enum(PATTERNS),
                "hat": _enum(HATS), "glasses": {"type": "boolean"}})
    member = obj({"id": {"type": "string"}, "label": {"type": "string"}, "place": {"type": "string"}, "look": look})
    state = obj({"from": {"type": "integer"}, "kicker": {"type": "string"}, "title": {"type": "string"},
                 "chart": _enum(["up", "down", "none"]), "icon": _enum(["chip", "none"]), "tone": _enum(["good", "bad", "neutral"])})
    beat = obj({"from": {"type": "integer"}, "who": {"type": "string"}, "act": _enum(ACTS), "face": _enum(FACES),
                "bubble": _enum(BUBBLES), "look": {"type": "string"}})
    glow = obj({"from": {"type": "integer"}, "place": {"type": "string"}, "tone": _enum(["good", "bad", "neutral"])})
    shot = obj({"from": {"type": "integer"}, "who": {"type": "array", "items": {"type": "string"}}, "angle": _enum(ANGLES),
                "lens": _enum(LENSES), "move": _enum(MOVES)})
    return obj({"set": _enum(list(SETS)), "cast": {"type": "array", "items": member},
                "tv": obj({"place": {"type": "string"}, "states": {"type": "array", "items": state}}),
                "beats": {"type": "array", "items": beat}, "glow": {"type": "array", "items": glow},
                "shots": {"type": "array", "items": shot}})


def instructions() -> str:
    return (
        "You are the director of a 3D animated YouTube Short in the Ricks Clips style: white deadpan heads, pear bodies, "
        "noodle limbs, a lit 3D set, one place, 2 to 4 people around one thing. The narrator speaks; nobody's mouth "
        "talks; the people ACT what the words say. You write ONE storyboard as JSON; the engine builds it and a camera "
        "director frames every shot (people always whole in the frame, nothing colliding), so you choose WHAT is shown, "
        "not camera numbers.\n\n"
        "SET: \"office\" (4 standing desks in a row, each with a laptop; a wall TV can hang on the back wall) or \"home\" "
        "(sofa, kitchen, a round table).\n"
        f"PLACES office: desk-1..desk-4 (behind that desk, facing the camera), desk-N-left / desk-N-right (standing at "
        f"that desk's end, facing it), open-1..open-6 (open floor in front of the desks, left to right). Home: "
        f"{', '.join(HOME_PLACES)}. Never two people on one place. People who talk to each other stand at one desk "
        "(behind it and at its ends) or on neighbouring open places.\n"
        "CAST: 2 to 4 people; real people are never drawn as themselves: give roles (\"the chipmaker's boss\", "
        "\"an investor\"). Look: outfit, a main colour and an accent (hex), a pattern, a hat or none, glasses. Make "
        "each person easy to tell apart.\n"
        "TV (office): place \"above:<id>\" (on the wall behind that person), \"wall-left\", \"wall-right\" or \"none\". "
        "States change on the key words: a short kicker (BREAKING, LIVE, or empty), a title of at most 3 words in "
        "capitals that SHOWS the story's object or number (\"AI IPO\", \"$3.8 TRILLION\", \"NASDAQ -2%\"), a chart "
        "up/down/none, a chip icon when it is about chips, tone good/bad/neutral. Only facts from the script.\n"
        f"BEATS: from word number N, a person does an act ({', '.join(ACTS)}), wears a face ({', '.join(FACES)}), may "
        "show a bubble (?, !, $ or none) and looks at someone (a cast id, \"tv\" or \"front\"). point uses look as its "
        "target. Every line of the voice has a matching action: when the script says investors doubt, they scratch "
        "their heads with a \"?\"; when money lands, someone cheers; when it goes wrong, faces go pale.\n"
        "GLOW: a laptop lights the faces at a desk place, good (green) or bad (red), from a word on.\n"
        "SHOTS: a new shot starts on the FIRST word of a phrase (use the phrase starts given). Each shot lasts 1.5 to "
        "3.5 seconds; every shot moves; never the same angle twice in a row. who = the 1 to 3 people (and \"tv\") the "
        "shot is about; anyone else should be away from them. Plan like a director: open on the hero with the place "
        "(crane-down, wide), push in low on the hero for confidence, show the news landing on the TV, cut to the "
        "reactions, a dolly-zoom on the \"oh no\" moment. Angles: front, low, high, left, right. Lenses: wide, medium, "
        "close (close still shows the whole person). Moves: " + ", ".join(MOVES) + ".\n"
        "All `from` values are word numbers from the list you are given; shots and beats in time order. Return JSON."
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


def repair(board: dict, words: list[dict]) -> tuple[dict, list[str]]:
    """Make any storyboard buildable without asking again. Returns the board and what was changed."""
    notes: list[str] = []
    n = len(words)
    b = json.loads(json.dumps(board))
    b["set"] = b.get("set") if b.get("set") in SETS else "office"
    places = OFFICE_PLACES if b["set"] == "office" else HOME_PLACES
    cast, used = [], set()
    for i, m in enumerate((b.get("cast") or [])[:4]):
        cid = re.sub(r"[^a-z0-9_-]", "", str(m.get("id") or f"p{i + 1}").lower()) or f"p{i + 1}"
        if cid in {c["id"] for c in cast} or cid == "tv":
            cid = f"{cid}{i + 1}"
        place = m.get("place") if m.get("place") in places and m.get("place") not in used else None
        if place is None:
            place = next((p for p in places if p not in used and p.startswith("open-")), None) or next(p for p in places if p not in used)
            notes.append(f"{cid} moved to {place} (its place was unknown or taken)")
        used.add(place)
        L = m.get("look") or {}
        cast.append({"id": cid, "label": str(m.get("label") or cid)[:60], "place": place,
                     "look": {"outfit": L.get("outfit") if L.get("outfit") in OUTFITS else "suit",
                              "color": _hex(L.get("color"), "#2f3542"), "accent": _hex(L.get("accent"), "#c8352f"),
                              "pattern": L.get("pattern") if L.get("pattern") in PATTERNS else "none",
                              "hat": L.get("hat") if L.get("hat") in HATS else "none", "glasses": bool(L.get("glasses"))}})
    if len(cast) < 1:
        raise ValueError("storyboard: no cast")
    b["cast"] = cast
    ids = {c["id"] for c in cast}
    clampw = lambda v: max(0, min(n - 1, int(v or 0)))
    tv = b.get("tv") or {}
    tvp = str(tv.get("place") or "none")
    if b["set"] != "office" or not (tvp in ("wall-left", "wall-right") or (tvp.startswith("above:") and tvp[6:] in ids)):
        if tvp != "none":
            notes.append(f"TV place {tvp} not usable, TV off")
        tvp = "none"
    states = []
    for s in tv.get("states") or []:
        title = re.sub(r"\s+", " ", str(s.get("title") or "")).strip()[:24]
        if not title:
            continue
        states.append({"from": clampw(s.get("from")), "kicker": str(s.get("kicker") or "")[:22], "title": title,
                       "chart": s.get("chart") if s.get("chart") in ("up", "down", "none") else "none",
                       "icon": s.get("icon") if s.get("icon") in ("chip", "none") else "none",
                       "tone": s.get("tone") if s.get("tone") in ("good", "bad", "neutral") else "neutral"})
    b["tv"] = {"place": tvp, "states": sorted(states, key=lambda s: s["from"]) if tvp != "none" else []}
    beats = []
    for x in b.get("beats") or []:
        if x.get("who") not in ids:
            continue
        look = x.get("look") if x.get("look") in ids | {"tv", "front"} else "front"
        if look == "tv" and tvp == "none":
            look = "front"
        beats.append({"from": clampw(x.get("from")), "who": x["who"], "act": x.get("act") if x.get("act") in ACTS else "stand",
                      "face": x.get("face") if x.get("face") in FACES else "calm",
                      "bubble": x.get("bubble") if x.get("bubble") in BUBBLES else "none", "look": look})
    b["beats"] = sorted(beats, key=lambda x: x["from"])
    b["glow"] = [{"from": clampw(g.get("from")), "place": g["place"], "tone": g.get("tone") if g.get("tone") in ("good", "bad", "neutral") else "neutral"}
                 for g in b.get("glow") or [] if g.get("place") in places]
    # shots: on word starts, 1.0-3.5 s, never the same angle twice in a row, everyone named known
    end = words[-1]["end"]
    shots = []
    for s in sorted(b.get("shots") or [], key=lambda s: int(s.get("from") or 0)):
        who = [w for w in (s.get("who") or []) if w in ids or (w == "tv" and tvp != "none")]
        if not who:
            notes.append(f"shot at word {s.get('from')} named nobody known, dropped")
            continue
        shots.append({"from": clampw(s.get("from")), "who": who, "angle": s.get("angle") if s.get("angle") in ANGLES else "front",
                      "lens": s.get("lens") if s.get("lens") in LENSES else "medium", "move": s.get("move") if s.get("move") in MOVES else "push"})
    if not shots:
        shots = [{"from": 0, "who": [cast[0]["id"]], "angle": "front", "lens": "medium", "move": "push"}]
        notes.append("no usable shots: one shot on the first person")
    shots[0]["from"] = 0
    t = lambda i: words[i]["start"]
    merged = []
    for s in shots:                                   # too short: folded into the shot before
        if merged and t(s["from"]) - t(merged[-1]["from"]) < MIN_SHOT:
            notes.append(f"shot at word {s['from']} under {MIN_SHOT}s, merged")
            continue
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
            cur = {**cur, "from": nxt, "angle": ANGLES[(ANGLES.index(cur["angle"]) + 2) % len(ANGLES)],
                   "move": "orbit-left" if cur["move"] != "orbit-left" else "orbit-right"}
            out.append(cur); notes.append(f"long shot split at word {nxt}")
    for a, c in zip(out, out[1:]):
        if a["angle"] == c["angle"]:
            c["angle"] = ANGLES[(ANGLES.index(c["angle"]) + 1) % len(ANGLES)]
    b["shots"] = out
    return b, notes
