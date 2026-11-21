"""Stickman long videos: the ReachMora 2D long-form engine (vendor/reachmora), used exactly as its skill says:
script.txt -> sentences -> timing.json -> story.json (written from references/story-format.md) -> plan (fix every
warning) -> stills -> render -> audio -> final.

What we add: timing.json is built from the word timings our engine already has (the same words the captions use),
so the engine needs no speech model; the storyboard is written by the model with the kit's story format and pacing
rules as its instructions, facts only from our research; the plan's warnings go back to the writer once.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
KIT = ROOT / "vendor" / "reachmora"

sys.path.insert(0, str(KIT))
from engine.timing import norm, sentences  # noqa: E402  (the kit's own sentence splitter and word normaliser)

sys.path.remove(str(KIT))


def script_text(display: str) -> str:
    """The script as the kit wants it: one paragraph per line (our display script already is)."""
    lines = [" ".join(p.split()) for p in re.split(r"\n\s*\n|\n", display) if p.strip()]
    return "\n".join(lines) + "\n"


def timing(script: str, words: list[dict[str, Any]], duration: float) -> dict[str, Any]:
    """timing.json in the kit's format (engine/timing.py align()), from our timed words instead of its ASR.
    Script words are matched to spoken words in order (difflib, as the kit does); unmatched ones are interpolated."""
    import difflib

    ss = sentences(script)
    sw = [(i, w) for i, s in enumerate(ss) for w in s.split() if norm(w)]
    spoken = [(norm(str(w.get("word", ""))), float(w["start"]), float(w.get("end", w["start"]))) for w in words]
    spoken = [s for s in spoken if s[0]]
    times: list[float | None] = [None] * len(sw)
    ends: list[float | None] = [None] * len(sw)
    sm = difflib.SequenceMatcher(a=[norm(w) for _, w in sw], b=[w for w, _, _ in spoken], autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            times[blk.a + k], ends[blk.a + k] = spoken[blk.b + k][1], spoken[blk.b + k][2]
    matched = sum(t is not None for t in times) / max(1, len(times))
    known = [k for k, t in enumerate(times) if t is not None]
    if not known:
        raise RuntimeError("stickman timing: none of the script's words were found in the voice timing")
    for k in range(len(times)):
        if times[k] is None:
            prev = max((j for j in known if j < k), default=None)
            nxt = min((j for j in known if j > k), default=None)
            if prev is None:
                times[k] = max(0.0, times[nxt] - 0.3 * (nxt - k))
            elif nxt is None:
                times[k] = times[prev] + 0.3 * (k - prev)
            else:
                times[k] = times[prev] + (times[nxt] - times[prev]) * (k - prev) / (nxt - prev)
    for k in range(1, len(times)):
        times[k] = max(times[k], times[k - 1])
    out = []
    for i, s in enumerate(ss):
        ks = [k for k, (si, _) in enumerate(sw) if si == i]
        if not ks:
            continue
        t0, tl = times[ks[0]], times[ks[-1]]
        last_end = ends[ks[-1]] if ends[ks[-1]] is not None else tl + 0.3
        nxt = times[ks[-1] + 1] if ks[-1] + 1 < len(times) else duration
        t1 = max(tl + 0.15, min(last_end + 0.05, nxt - 0.02, duration))
        out.append({"i": i, "text": s, "start": round(max(0.0, t0 - 0.06), 3), "end": round(t1, 3),
                    "words": [{"w": sw[k][1], "n": norm(sw[k][1]), "t": round(times[k], 3)} for k in ks]})
    return {"duration": round(duration, 3), "method": "asr", "matched": round(matched, 3), "sentences": out}


def numbered(script: str) -> str:
    return "\n".join(f"{i:3d}  {s}" for i, s in enumerate(sentences(script)))


# ---------------------------------------------------------------- the storyboard writer
STORY_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"story_json": {"type": "string"}},
    "required": ["story_json"],
}


def instructions() -> str:
    fmt = (KIT / "references" / "story-format.md").read_text(encoding="utf-8")
    return f"""You storyboard a long animated YouTube video in the ReachMora 2D style: you write its story.json, exactly
in the format below. The engine draws everything from it; you never write drawing code.

The voiceover is already recorded and timed. You get its sentences, numbered (use these numbers in "s"), the
video's title and the verified research. Follow the format and its pacing rules exactly:
- cover every sentence number once, in order. FAST (owner 2026-11-18, after his fast-cut test): one shot per
  sentence, aim 1.5-4 s a shot (the sentence times are given); join two sentences only when both are under 1.5 s;
  a sentence longer than 4 s gets beats, labels, props or a stamp landing on its own words about every 1.5 s, so
  the picture changes on the voice and never sits still. Plan each shot's picture to be surprising and literal;
- never more than two of the same kind in a row; rotate world shots (wide, closeup, walk) with graphics (icon,
  counter, chart, table, versus, list);
- every number in the script on screen (counter, chart or label), with an everyday comparison where it helps;
  numbers ONLY from the script and research, never invented (charts without real numbers use show_values false);
- a reaction closeup after every big claim or twist; re-hook moments (spoken title, stamp, versus) every 60-90 s;
- tag the first shot in each new place or era; a lower_third the first time each person appears;
- chapter cards: 1-2 silent title cards for 5 min, 3-6 for 10-15 min, 0-1 for 3 min (as the format says);
- cue mid-shot events with words from that shot's own sentences ("at": "word");
- end on a polaroid shot whose caption is the payoff line, cued 1-2 s before the end.
- cast: 2-4 ORIGINAL characters with distinct silhouettes and colours. Dress them for who they are with "role":
  {", ".join(sorted(ROLES))} (the role sets outfit, colours and gear: helmet, hard hat and hi-vis vest, lab coat,
  stethoscope, badge, cap, crown...); "headscarf": true (with "scarf_col") for a woman who wears one; "headwear":
  one of {", ".join(HEADWEAR)} on anyone. Women: "outfit": "dress" or a suit with "hair": "long" or "bun".
  Extras for one shot (soldiers, workers, crowd members) are cast members too. Real people (a CEO, a founder) are generic
  puppets with a lower_third name card, never a likeness; no brand mascots. Company logos are real (owner
  2026-11-21): use "logo" / logo_pop / names, never draw a logo yourself.
- labels: 1-4 words each, at most 3 per shot; characters' x between 250 and 1670.
- icons (owner 2026-11-21: show the real things the story names): use the kit's icons, which include ours:
  {", ".join(sorted(kit_icons()))}. Draw what is said (chip, datacenter, rocket, factory, court...). A thing
  with no icon gets icon "label" with "text": its name (1-3 words); never skip it.
- THE CAST CARRIES THE STORY (owner 2026-11-21): at least 2 of every 3 shots are wide/walk/dialogue/closeup shots
  with characters ACTING (chars with acts) in a place; icon/title/table/chart shots are at most 1 in 3 and never two in
  a row. The FIRST shot is the hook: a character in a real place doing something on the first words (never an empty
  card or a title alone). Every character in a shot has at least one act on a word of its sentence. (The engine
  puts the cast into any shot you leave without it, so give them the place, the things and the acts yourself.)
- PLACES (owner 2026-11-21: "it's the whole world"): a wide, walk or closeup shot stands in a real place that
  fits its sentence. Sets: {", ".join(sorted(kit_sets()))}. Options: "time" (day/dusk/night), and where the place
  carries a name, "sign" (hq, cutaway, press, newsroom, exchange, highway, launchpad, stage, classroom "board_text")
  or "flag" (moon, mars). "logo": the company's name (hq, cutaway, press, campus) puts its REAL logo on the sign or roof. A new place at least every 2-3 shots; never the same place twice in a row.
- MOVING PICTURES: any shot may carry "moves": [{{"do": name, "at": "word", ...}}], a picture that plays on its word:
  {", ".join(sorted(kit_moves()))}. Options: x, y, s, "text" (a label), "names" (kart_race, podium, dominoes:
  2-5 short names from the script; company names get their real logos), logo_pop ("logo": a company the
  sentence names, its real mark pops in). "at" is a word in the FIRST HALF of the shot's sentence (a move on the last
  word is cut off). Use one move in about every second shot, matched literally to what is said (money -> money_rain
  or cash_pile, launch -> rocket_launch, crash -> chart_down + alarm, race/competition -> kart_race, winner -> podium,
  chain reaction -> dominoes, change of direction -> signpost, ban/shut down -> door_slam); never the same move in
  two shots in a row.
- BEHAVIOUR (owner 2026-11-21, "the all ingredient"): every character in a shot DOES something on the story's words:
  "acts": [{{"do": name, "at": "word", "for": seconds (optional), "item": icon, "to": x}}] on the char. Acts:
  {", ".join(ACTS)}. Several at once on one char when the story says so (a man tired of waiting: scratch + tap_foot;
  he lost: head_down + shake_head). Match the words literally: agree/deal -> handshake (the two chars about 430 apart,
  facing each other), fight/disagree -> argue (both, facing), joke/funny -> laugh, lost/failed -> head_down, no/never
  -> shake_head, yes/right -> nod, waiting/queue -> scratch + tap_foot, typing/posting -> type, scrolling/online ->
  scroll, calling -> call, money/won -> grab or hold with "item", gave/sold -> give, secret -> shh, shocked -> jump,
  won/success -> cheer, exhausted -> sigh, collapse -> faint, sad/lost money -> cry, in love/likes -> love, arrives ->
  walk_to or run_to with "to". "item" is any icon name (phone, laptop, moneybag, chip, gift...).
- LOTS AT ONCE: like the channels that work, 2-3 things move together in a shot: a char's act + a moving picture +
  a prop. Social media and attention: hearts_rise, like_counter ("from", "to"), comment_pop ("lines"), emoji_pop
  ("face"), notif_pop, big_phone ("lines"); crowds and bots: bot_rows ("mode": idle|cheer), desk_row (typing at
  computers). Equipment and signs are icons in props: industrial, home, school, office, smart devices, and glowing
  neon ("text", "color") / led_board ("text") / exit_sign / neon_heart / neon_arrow / tombstone ("text").
- CAMERA: "cam" may be one of {", ".join(CAM_PRESETS)}; vary it from shot to shot (shake only on a shock).
- mood: pick from the format's list to fit the story.
- checked on our renders (2026-11-17): a title shot ALWAYS has "text" (spoken or not; without it the card is
  black); a walk shot has ONE character (two walk on the same line and hide each other); in icon, list, counter,
  table and chart shots the FIRST item has no "at" (it is there from the shot's first frame), later items land on
  their words, so a graphic never opens on an empty page; a counter's number with its prefix and suffix is at most
  6 characters ("$5T", "208B", "90%"); words like TRILLION or PEOPLE go in its caption.

Return JSON with one field, story_json: the complete story.json as a string.

========================= story.json FORMAT (the kit's reference) =========================
{fmt}"""


def request(title: str, script: str, timing_doc: dict[str, Any], research: dict[str, Any], problems: str = "") -> str:
    rows = "\n".join(f"{s['i']:3d}  [{s['start']:7.2f}-{s['end']:7.2f}]  {s['text']}" for s in timing_doc["sentences"])
    facts = json.dumps(research, ensure_ascii=False)[:24000] if research else "(none)"
    out = (f"TITLE: {title}\nLENGTH: {timing_doc['duration'] / 60:.1f} min\n\nSENTENCES (number [start-end s] text):\n"
           f"{rows}\n\nVERIFIED RESEARCH (the only source for facts and numbers):\n{facts}\n")
    if problems:
        out += f"\nTHE ENGINE'S PLAN CHECK FOUND THESE PROBLEMS IN YOUR LAST story.json. Fix every one and send the whole file again:\n{problems}\n"
    return out


# ---------------------------------------------------------------- running the kit
def kit(command: str, project: Path, *args: str, timeout: int = 6 * 3600) -> str:
    """python3 -m engine <command> <P> ..., run from the kit folder as its skill says."""
    # 2026-11-21: our extra icons load into the kit (stickman/rm_hook) in its process and every render worker
    hook = str(Path(__file__).resolve().parent / "rm_hook")
    src = str(Path(__file__).resolve().parents[2])
    path = os.pathsep.join([hook, src] + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else []))
    result = subprocess.run([sys.executable, "-m", "engine", command, str(project), *args], cwd=KIT, text=True,
                            capture_output=True, timeout=timeout,
                            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=path))
    if result.returncode != 0:
        raise RuntimeError(f"stickman {command} failed: {(result.stderr or result.stdout)[-1500:]}")
    return result.stdout


def warnings(plan_output: str) -> list[str]:
    return [line[len("WARNING:"):].strip() for line in plan_output.splitlines() if line.startswith("WARNING:")]


def prepare(project: Path, display: str, words: list[dict[str, Any]], duration: float, voice: Path) -> dict[str, Any]:
    project.mkdir(parents=True, exist_ok=True)
    script = script_text(display)
    (project / "script.txt").write_text(script, encoding="utf-8")
    doc = timing(script, words, duration)
    (project / "timing.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    target = project / f"voice{voice.suffix.lower()}"
    if not target.exists():
        target.write_bytes(voice.read_bytes())
    return doc


def collisions(project: Path) -> dict[str, Any]:
    """Text touching text, leaving the frame or covering a head, on real frames of every shot (stickman/collide.py,
    run in its own process because it wraps the engine's label drawing)."""
    # 2026-11-21: with our hook, exactly as the kit renders (icons, places, moves, acts); without it the check called
    # every new icon "cannot be drawn" and took 84 things out of the Nvidia SC26 video
    hook = str(Path(__file__).resolve().parent / "rm_hook")
    result = subprocess.run([sys.executable, "-m", "golide_engine.stickman.collide", str(project)], capture_output=True,
                            text=True, timeout=1800,
                            env=dict(os.environ, PYTHONPATH=os.pathsep.join([hook, str(ROOT / "src"), os.environ.get("PYTHONPATH", "")])))
    if result.returncode != 0:
        raise RuntimeError(f"stickman collision check failed: {result.stderr[-800:]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


CHAR_SHARE = 2 / 3     # owner 2026-11-21: "I don't see much of puppets": at least 2 of every 3 shots show characters


def puppet_problems(story: dict[str, Any]) -> list[str]:
    """The puppets carry the story: at least 2 of every 3 shots have characters in them (acting), and never two shots
    in a row without any. Returned as problems for the writer; a storyboard that still breaks it is not drawn."""
    shots = [s for s in story.get("shots") or [] if isinstance(s, dict)]
    if not shots:
        return ["the story has no shots"]
    has = [bool(s.get("chars")) for s in shots]
    out = []
    if sum(has) < CHAR_SHARE * len(shots):
        out.append(f"only {sum(has)} of {len(shots)} shots have characters; at least {int(-(-CHAR_SHARE * len(shots) // 1))} "
                   "must show the cast acting (wide/walk/dialogue/closeup with chars and acts): the puppets carry the story")
    for i in range(1, len(has)):
        if not has[i] and not has[i - 1]:
            out.append(f"shots {i - 1} and {i} both have no characters; never two in a row without the cast")
    acting = sum(1 for s in shots for ch in s.get("chars") or [] if isinstance(ch, dict) and ch.get("acts"))
    if sum(has) and acting < sum(has) * .8:
        out.append(f"only {acting} characters act; every shot with characters gives them acts on the words")
    return out


ACT_WORDS = [   # the act a sentence's words call for (first match wins); "point" at the shot's things otherwise
    (("lost", "lose", "failed", "fail", "behind", "dropped", "fell"), ["head_down", "shake_head"]),
    (("waiting", "wait", "queue", "line", "delay", "slow"), ["scratch", "tap_foot"]),
    (("money", "billion", "million", "cash", "paid", "profit", "revenue", "price"), ["grab"]),
    (("laugh", "joke", "funny"), ["laugh"]), (("argue", "fight", "versus", "rival", "against"), ["argue"]),
    (("deal", "agree", "partner", "together"), ["handshake"]), (("no", "not", "never", "won't"), ["shake_head"]),
    (("yes", "right", "exactly", "true"), ["nod"]), (("shock", "suddenly", "boom", "crash", "huge"), ["jump"]),
    (("won", "win", "record", "first", "success", "launch"), ["cheer"]), (("type", "code", "write", "posting"), ["type"]),
    (("phone", "app", "online", "scroll", "post"), ["scroll"]), (("call",), ["call"]), (("think", "why", "how", "what"), ["think"]),
    (("tired", "hard", "struggle"), ["sigh"]), (("secret", "quiet", "hidden"), ["shh"]),
]
CHART_KINDS = ("chart",)


def sentence_texts(project: Path) -> list[str]:
    try:
        return [str(s.get("text", "")) for s in json.loads((project / "timing.json").read_text(encoding="utf-8"))["sentences"]]
    except Exception:  # noqa: BLE001 - no timing yet: acts default to pointing
        return []


def _acts_for(text: str, has_things: bool, item: str | None) -> list[dict[str, Any]]:
    words = re.findall(r"[a-z']+", text.lower())
    first = words[min(1, len(words) - 1)] if words else None
    for keys, acts in ACT_WORDS:
        hit = next((w for w in words if w in keys), None)
        if hit:
            out = [{"do": a, "at": hit} for a in acts]
            if acts == ["grab"] and item:
                out[0]["item"] = item
            return out
    return [{"do": "point" if has_things else "nod", "at": first}] if first else [{"do": "point" if has_things else "nod"}]


def cast_in(story: dict[str, Any], sentences: list[str]) -> int:
    """The cast carries the story (owner 2026-11-21): the engine turns shots without characters into scenes where the
    cast stands in the place with that shot's things and acts on its words, so at least 2 of every 3 shots and the
    first shot have the cast, never two in a row without; and every character on screen acts. Returns shots changed."""
    shots = [s for s in story.get("shots") or [] if isinstance(s, dict)]
    cast = story.setdefault("cast", {})
    if not cast:
        cast["host"] = {"role": "corporate"}
    ids = list(cast)
    place, changed, bare = "openoffice", 0, 0
    def text_of(shot):
        return " ".join(sentences[i] for i in shot.get("s", []) if isinstance(i, int) and 0 <= i < len(sentences))
    for i, shot in enumerate(shots):
        if shot.get("chars"):
            place = shot.get("set") or place
            for ch in shot["chars"]:
                if isinstance(ch, dict) and not ch.get("acts"):
                    ch["acts"] = _acts_for(text_of(shot), bool(shot.get("props")), None)
            continue
        keep = i > 0 and bool(shots[i - 1].get("chars")) and (bare + 1) <= len(shots) / 3
        if keep:
            bare += 1
            continue
        things = [x.get("name") for x in shot.get("icons") or [] if isinstance(x, dict) and x.get("name")]
        things += [x.get("icon") for x in shot.get("props") or [] if isinstance(x, dict) and x.get("icon")]
        moves = list(shot.get("moves") or [])
        chart = shot.get("kind") in CHART_KINDS
        if chart:                                   # the chart stands on the right, the cast on the left
            moves.append({"do": "chart_up", "box": [760, 200, 1740, 800]})
        who = ids[changed % len(ids)]
        new = {"kind": "wide", "s": shot.get("s", []), "set": shot.get("set") or place, "cam": shot.get("cam", "push"),
               "chars": [{"id": who, "x": 360 if chart else 560, "face": .7,
                          "acts": _acts_for(text_of(shot), bool(things), things[0] if things else None)}],
               "props": [] if chart else [{"icon": n, "x": 1180 + k * 300, "y": 700, "s": .75} for k, n in enumerate(things[:2])]}
        for key in ("time", "labels", "lower_third", "logo", "sign", "beats"):
            if key in shot:
                new[key] = shot[key]
        if moves:
            new["moves"] = [m for m in moves if isinstance(m, dict)]
        shot.clear(); shot.update(new)
        changed += 1
    print(json.dumps({"status": "stickman_cast_in", "shots_given_the_cast": changed, "shots": len(shots)}), flush=True)
    return changed


def storyboard(text, project: Path, title: str, doc: dict[str, Any], research: dict[str, Any], record=None) -> list[str]:
    """Write story.json, then check it: the kit's plan check and our collision check (owner 2026-11-17: no collision
    in anything). Problems go back to the writer once. Any collision still there after that is removed (the text
    that collides is taken out), so the video is clean. Returns the plan warnings left."""
    problems = ""
    left: list[str] = []
    asked: list[dict[str, str]] = []
    for attempt in (1, 2):
        out = text.generate_json(instructions(), request(title, (project / "script.txt").read_text(encoding="utf-8"),
                                                         doc, research, problems), STORY_SCHEMA, max_output_tokens=60000)
        if record:
            record(f"stickman-story-{attempt}", out)
        story = json.loads(out.value["story_json"])
        story["title"] = title
        asked += [w for w in wishes(story) if w not in asked]
        cast_in(story, sentence_texts(project))        # owner 2026-11-21: the engine puts the cast in, never a stop
        (project / "story.json").write_text(json.dumps(story, indent=1, ensure_ascii=False), encoding="utf-8")
        unknown = fix_icons(json.loads(json.dumps(story)))
        places = fix_places(json.loads(json.dumps(story)))
        if attempt == 2 and places:
            fix_places(story, final=True)
            (project / "story.json").write_text(json.dumps(story, indent=1, ensure_ascii=False), encoding="utf-8")
        if attempt == 2 or not unknown:
            fix_story_icons(project)
        try:
            left = warnings(kit("plan", project, timeout=900))
        except RuntimeError as error:
            left = [str(error)]
        if attempt == 1 and unknown:
            known = ", ".join(sorted(kit_icons()))
            left = left + [f"icon {c.split(' -> ')[0]!r} is not one the kit draws; use one of: {known}; for anything else "
                           f"use icon \"label\" with \"text\": its name" for c in unknown if " -> " in c and not c.startswith("lower_third")]
        if attempt == 1:
            left = left + places
        if any(k in w for w in left for k in ("ImportError", "ModuleNotFoundError", "cannot open shared object")):
            # 2026-11-17: the machine is broken, not the story; never pay the writer again for that
            raise RuntimeError("stickman: the kit cannot run on this machine: " + left[0][-400:])
        hit = collisions(project)["problems"] if not any("failed" in w for w in left) else []
        print(json.dumps({"status": "stickman_plan", "attempt": attempt, "warnings": len(left), "collisions": len(hit)}),
              flush=True)
        if not left and not hit:
            report_wishes(project, title, asked)
            return []
        problems = "\n".join(f"- {w}" for w in left + hit)
    report_wishes(project, title, asked)
    clean_up(project)
    return left


def kit_icons() -> set[str]:
    """The icon names the kit can draw (vendor/reachmora/engine/props.py ICONS), read from its source."""
    import re
    src = (KIT / "engine" / "props.py").read_text(encoding="utf-8")
    block = src[src.find("ICONS = dict("):src.find("\n\n", src.find("ICONS = dict("))]
    ours = (Path(__file__).resolve().parent / "rm_extra.py").read_text(encoding="utf-8")
    ours = ours[ours.find("ICONS = {"):ours.find("}", ours.find("ICONS = {"))]
    gear = (Path(__file__).resolve().parent / "rm_gear.py").read_text(encoding="utf-8")
    gear = gear[gear.find("ICONS = {"):]
    return (set(re.findall(r"(\w+)=(?:ic_|lambda)", block)) | set(re.findall(r'"(\w+)": ic_', ours))
            | set(re.findall(r'"(\w+)": ic_', gear)))


from .rm_roles import HEADWEAR, ROLES  # noqa: E402
from .rm_acts import ACTS  # noqa: E402

CAM_PRESETS = ("push", "pull", "pan_left", "pan_right", "tilt_up", "tilt_down", "crane", "orbit", "shake")
HERE = Path(__file__).resolve().parent


def kit_sets() -> set[str]:
    """The places the kit draws: its own sets (engine/sets.py SETS) and ours (rm_sets.py NEW_SETS), read from source."""
    import re
    src = (KIT / "engine" / "sets.py").read_text(encoding="utf-8")
    block = src[src.find("SETS = dict("):]
    ours = (HERE / "rm_sets.py").read_text(encoding="utf-8")       # NEW_SETS = dict(...) and NEW_SETS.update(...)
    return set(re.findall(r"(\w+)=set_", block)) | set(re.findall(r"(\w+)=set_", ours))


def kit_moves() -> set[str]:
    """The moving pictures a shot can carry (rm_moves.py, one m_<name> function each)."""
    import re
    return set(re.findall(r"^def m_(\w+)\(", (HERE / "rm_moves.py").read_text(encoding="utf-8"), re.M))


def fix_places(story: dict[str, Any], final: bool = False) -> list[str]:
    """Problems with places, moves and camera names (for the writer's retry). With final=True they are repaired so
    the render never stops: an unknown place becomes the kit's own place for that shot kind, an unknown move or camera
    name is left out (nothing drawn rather than a wrong picture). No model call."""
    sets, moves = kit_sets(), kit_moves()
    found: list[str] = []
    for i, shot in enumerate(story.get("shots") or []):
        if not isinstance(shot, dict):
            continue
        name = shot.get("set")
        if name is not None and name not in sets:
            found.append(f"shot {i}: set {name!r} is not a place the kit draws; use one of: {', '.join(sorted(sets))}")
            if final:
                shot.pop("set")
        if isinstance(shot.get("moves"), list):
            keep = []
            for m in shot["moves"]:
                if isinstance(m, dict) and m.get("do") in moves:
                    keep.append(m)
                else:
                    found.append(f"shot {i}: move {(m or {}).get('do') if isinstance(m, dict) else m!r} is not one of: {', '.join(sorted(moves))}")
            if final:
                shot["moves"] = keep
        cam = shot.get("cam")
        if isinstance(cam, str) and cam not in CAM_PRESETS:
            found.append(f"shot {i}: cam {cam!r} is not one of: {', '.join(CAM_PRESETS)} (or the format's zoom/focus object)")
            if final:
                shot.pop("cam")
    return found


def wishes(story: dict[str, Any]) -> list[dict[str, str]]:
    """What the writer asked for that the library cannot draw (owner 2026-11-21): places, icons, moves, cameras,
    roles and brand logos. Listed in Studio so each new batch is drawn from what real videos needed. No model call."""
    from ..vector import logos
    from .rm_roles import ROLES

    sets, moves, icons = kit_sets(), kit_moves(), kit_icons()
    out: list[tuple[str, str]] = []
    for d in (story.get("cast") or {}).values():
        if isinstance(d, dict) and d.get("role") and str(d["role"]).lower() not in ROLES:
            out.append(("role", str(d["role"])))
    for shot in story.get("shots") or []:
        if not isinstance(shot, dict):
            continue
        if shot.get("set") is not None and shot["set"] not in sets:
            out.append(("place", str(shot["set"])))
        cam = shot.get("cam")
        if isinstance(cam, str) and cam not in CAM_PRESETS:
            out.append(("camera", cam))
        names = [p.get("icon") for p in shot.get("props") or [] if isinstance(p, dict)]
        names += [i.get("name") for i in shot.get("icons") or [] if isinstance(i, dict)]
        names += [(shot.get(k) or {}).get("icon") for k in ("bubble", "compare") if isinstance(shot.get(k), dict)]
        for n in names:
            if isinstance(n, str) and n and n not in icons:
                out.append(("icon", n.replace("_", " ")))
        from .rm_acts import LENGTH as ACT_NAMES
        for ch in shot.get("chars") or []:
            for a in (ch.get("acts") or []) if isinstance(ch, dict) else []:
                if isinstance(a, dict) and a.get("do") not in ACT_NAMES:
                    out.append(("act", str(a.get("do"))))
        brands = [shot.get("logo")]
        for m in shot.get("moves") or []:
            if not isinstance(m, dict):
                continue
            if m.get("do") not in moves:
                out.append(("move", str(m.get("do"))))
            if m.get("do") == "logo_pop":
                brands.append(m.get("logo") or m.get("text"))
            elif m.get("do") in LOGO_MOVES:
                brands += list(m.get("names") or [])
        for b in brands:
            if isinstance(b, str) and b.strip() and not logos.find(b.strip()):
                out.append(("logo", b.strip()))
    seen, items = set(), []
    for kind, name in out:
        if (kind, name.lower()) not in seen:
            seen.add((kind, name.lower()))
            items.append({"kind": kind, "name": name})
    return items


def report_wishes(project: Path, title: str, items: list[dict[str, str]]) -> None:
    """Keep the wishes beside the story and send them to Studio's list. A failed send never stops the video."""
    (project / "wishes.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": "stickman_wishes", "count": len(items), "items": items[:30]}), flush=True)
    url = os.getenv("GOLIDE_STUDIO_BASE_URL", "").strip()
    if not items or not url:
        return
    try:
        from ..studio_bridge import StudioBridge
        StudioBridge(url).stickman_wishes(title, items)
    except Exception as exc:  # noqa: BLE001 - the list is a help for the next batch, not part of the video
        print(json.dumps({"status": "stickman_wishes_not_sent", "error": str(exc)[:200]}), flush=True)


def fix_icons(story: dict[str, Any], known: set[str] | None = None) -> list[str]:
    """Every icon name in the story is one the kit can draw: an unknown one is left out (nothing drawn rather than
    a wrong picture; the voice still says it). Only the story format's icon places are touched: props[].icon, bubble.icon,
    a counter's icon and compare.icon, and icons[].name (2026-11-17: a first version also hit lower_third names).
    Returns what changed. No model call."""
    known = known or kit_icons()
    changed: list[str] = []

    def near(name: str) -> str | None:
        # owner 2026-11-17: never a different picture from what is said; only the same name in another spelling
        n = str(name or "").strip().lower().replace(" ", "_").replace("-", "_")
        return n if n in known else None

    def fix(holder: dict, key: str, card: bool = False) -> bool:
        """True when the holder keeps a drawable icon."""
        value = holder.get(key)
        if not isinstance(value, str) or not value or value in known:
            return True
        to = near(value)
        if to:
            changed.append(f"{value} -> {to}")
            holder[key] = to
            return True
        if card:                              # 2026-11-21 (owner): never dropped; a card with its name
            changed.append(f"{value} -> label card")
            holder[key] = "label"
            holder.setdefault("text", value.replace("_", " "))
            return True
        changed.append(f"{value} -> left out")
        holder.pop(key, None)
        return False

    for shot in story.get("shots") or []:
        if not isinstance(shot, dict):
            continue
        if isinstance(shot.get("props"), list):
            shot["props"] = [p for p in shot["props"] if isinstance(p, dict) and fix(p, "icon", card=True)]
        for key in ("bubble", "compare"):
            if isinstance(shot.get(key), dict):
                fix(shot[key], "icon")
        if isinstance(shot.get("icon"), str):
            fix(shot, "icon")
        if isinstance(shot.get("icons"), list):
            shot["icons"] = [i for i in shot["icons"] if isinstance(i, dict) and fix(i, "name", card=True)]
            if not shot["icons"]:
                shot.pop("icons")
        # repair of the first version's damage: a name card that lost its name goes
        if isinstance(shot.get("lower_third"), dict) and not str(shot["lower_third"].get("name") or "").strip():
            shot.pop("lower_third")
            changed.append("lower_third without a name -> left out")
    return changed


LOGO_MOVES = ("kart_race", "podium", "dominoes")


def attach_logos(story: dict[str, Any]) -> list[str]:
    """Real brand marks (owner 2026-11-10/21): a shot's "logo" (hq, cutaway, press...) and the names in a kart race,
    podium or logo_pop get the brand's own simple-icons mark (vector/logos.py). A brand simple-icons does not carry
    stays its name in text, never a look-alike. Returns the names that had no mark (for the missing list)."""
    from ..vector import logos

    missing: list[str] = []

    def art(name: Any) -> dict | None:
        if not isinstance(name, str) or not name.strip():
            return None
        icon = logos.find(name.strip())
        if not icon:
            missing.append(name.strip())
            return None
        return {"svg": icon["svg"], "hex": icon.get("hex", "000000"), "title": icon.get("title", name)}

    for shot in story.get("shots") or []:
        if not isinstance(shot, dict):
            continue
        if shot.get("logo") and "logo_art" not in shot:
            found = art(shot["logo"])
            if found:
                shot["logo_art"] = found
        for m in shot.get("moves") or []:
            if not isinstance(m, dict) or "logo_art" in m:
                continue
            if m.get("do") == "logo_pop":
                found = art(m.get("logo") or m.get("text"))
                if found:
                    m["logo_art"] = found
            elif m.get("do") in LOGO_MOVES and isinstance(m.get("names"), list):
                m["logo_art"] = [art(n) for n in m["names"]]
    return missing


def fix_story_icons(project: Path) -> None:
    path = project / "story.json"
    story = json.loads(path.read_text(encoding="utf-8"))
    before = json.dumps(story, sort_keys=True)
    changed = fix_icons(story)
    attach_logos(story)
    from .rm_roles import apply_roles
    apply_roles(story)
    if changed or json.dumps(story, sort_keys=True) != before:
        path.write_text(json.dumps(story, indent=1, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"status": "stickman_icons_fixed", "changed": changed[:20]}), flush=True)


def clean_up(project: Path, rounds: int = 4) -> None:
    """The last resort: take out the text that still collides, until nothing does."""
    from .collide import drop

    last = None
    for _ in range(rounds):
        found = collisions(project)
        if not found["problems"]:
            return
        if last is not None and len(found["hits"]) >= last:
            # owner 2026-11-17: only the colliding text is ever removed, never a whole shot swapped for another
            raise RuntimeError("stickman: text that cannot be removed still collides: " + "; ".join(found["problems"][:8]))
        story = drop(json.loads((project / "story.json").read_text(encoding="utf-8")), found["hits"])
        (project / "story.json").write_text(json.dumps(story, indent=1, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"status": "stickman_collisions_removed", "count": len(found["hits"]),
                          "examples": found["problems"][:6]}), flush=True)
        last = len(found["hits"])
    if collisions(project)["problems"]:
        raise RuntimeError("stickman: collisions remain after clean-up")


def gaps(project: Path) -> list[tuple[float, float]]:
    """The pauses the silent chapter cards put into the video: (voice time, seconds), from the kit's own timeline."""
    sys.path.insert(0, str(KIT))
    try:
        from engine.timeline import Timeline
    finally:
        sys.path.remove(str(KIT))
    story = json.loads((project / "story.json").read_text(encoding="utf-8"))
    timing_doc = json.loads((project / "timing.json").read_text(encoding="utf-8"))
    return [(float(v), float(d)) for v, d in Timeline(story, timing_doc).gaps]


def shift_srt(srt: str, pauses: list[tuple[float, float]]) -> str:
    """Captions moved by the chapter-card pauses before them, so they stay on the voice in the finished video."""
    def at(stamp: str) -> str:
        h, m, rest = stamp.split(":")
        sec, ms = rest.split(",")
        t = int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000
        t += sum(d for v, d in pauses if v <= t + 1e-9)
        ms_total = int(round(t * 1000))
        return f"{ms_total // 3600000:02d}:{ms_total // 60000 % 60:02d}:{ms_total // 1000 % 60:02d},{ms_total % 1000:03d}"
    return re.sub(r"(\d\d:\d\d:\d\d,\d\d\d) --> (\d\d:\d\d:\d\d,\d\d\d)",
                  lambda m: f"{at(m.group(1))} --> {at(m.group(2))}", srt)


def render(project: Path, res: str | None = None) -> Path:
    """render -> audio -> final, as the kit's skill does. Returns the MP4."""
    extra = ["--res", res] if res else []
    kit("render", project, *extra)
    kit("audio", project, *extra)
    kit("final", project, *extra, "--title", "stickman")
    found = sorted((project / "out").glob("stickman*.mp4"))
    if not found:
        raise RuntimeError("stickman final wrote no video")
    return found[-1]
