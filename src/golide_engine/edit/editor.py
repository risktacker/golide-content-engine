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
from pathlib import Path
from typing import Any

POSES = ["talk", "explain", "point", "point_up", "point_left", "shock", "think", "thumbs_up", "shrug", "wave"]
TYPES = ["studio", "source", "photo", "stat", "compare", "steps", "timeline", "flow", "quote", "words", "logos", "icon",
         "chapter", "follow"]

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
        "points": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
            "when": _str, "what": _str}, "required": ["when", "what"]}},
        "brands": {"type": "array", "items": _str},
    },
    "required": ["type", "first_line", "last_line", "goli_corner", "poses", "screen_words", "punch", "source", "phrase",
                 "callout", "callout_sub", "edge", "value", "prefix", "suffix", "label", "quote", "quote_by", "left",
                 "right", "rows", "items", "points", "brands"],
}
EDIT_SCHEMA = {"type": "object", "additionalProperties": False,
               "properties": {"scenes": {"type": "array", "items": SCENE}}, "required": ["scenes"]}


def instructions(fmt: str) -> str:
    short = fmt == "short"
    return f"""You are the editor of GOLIDE, a faceless AI-explainer channel. Its host is Goli, an original cartoon
pangolin in a GOLIDE hoodie who talks with the owner's voice. You cut a {"vertical Short" if short else "long video"} the way
the best channels in the niche do: fast, real proof on screen, and the picture ALWAYS shows what is being said
at that moment.

{"The narration is cut into BEATS of about 2 seconds: the Short is fast. Give every beat its own picture that shows exactly what that beat says. A scene normally covers ONE beat (first_line = last_line = the beat number). Only a stat, compare, steps, timeline or flow card may cover 2 beats, and a studio scene at most 2." if short else "The narration is cut into BEATS of about 4 to 5 seconds: a long video EXPLAINS, so every picture stays long enough to be read and understood. Give every beat its own picture that shows what that beat says. A scene covers 1 beat, or 2 when the picture needs time (a page the camera walks through, a flow, a comparison, steps)."}
Scenes cover every beat exactly once, in order, no gaps: scene N+1's first_line = scene N's last_line + 1.

You also get CAPTURED PAGES: the real web pages behind the story, each cut into SHOTS (its headline, the exact
facts found on it, and every paragraph, list item and table cell with its text). A shot is a place on the page the
camera zooms to. Match beats to shots by meaning: when a beat states a fact, pick the shot whose text says it.
Never use the same shot twice in the whole video. {"On a Short, screenshots are the proof, not the whole show: at most one beat in three is a source scene, never two source scenes in a row; the rest are photos, numbers, flows, comparisons, steps, logos, quotes and words." if short else "On a long video the pages carry the explanation: walk through a page across its shots, but put another kind of picture between pages."}

Scene types (fill only the fields the type uses; null or [] for the rest):
- source: a captured page, zoomed to one shot (source = page index, phrase = shot index). callout = the fact in at
  most 4 words (e.g. "$40") or null, callout_sub = what it is (3 to 6 words), edge glass or fade.
- photo: the page's own picture (source = page index; only pages marked "photo: yes").
- stat: one number that matters (value as a number, prefix like "$", suffix like "%" or "x", label 2 to 5 words).
- compare: left vs right, 2 to 4 rows (label, a, b, winner).
- steps: 2 to 4 short imperative items (max 5 words each) when the beat tells the viewer what to do.
- timeline: 3 to 4 points (when, what) when the beat moves through time.
- flow: how something works or what leads to what: 2 to 4 short nodes in items (max 3 words each).
- quote: a short real quote from the pages or research (quote, quote_by).
- logos: 2 to 4 real product or company names (brands) named together in the beat.
- icon: one product or company named in the beat (brands = [that name], label = what about it, max 5 words).
- words: kinetic words only when nothing else fits: screen_words (max 5 words) and a punch word.
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


def beats(lines: list[Any], fmt: str) -> list[Any]:
    """The narration cut into beats of about 2 s (Short) or 3 s (long), at pauses and inside each line,
    so a picture can be chosen for every few words (owner 2026-11-11: what is on screen is what is said)."""
    from ..vector.align import TimedLine

    # owner 2026-11-12: the Short's pace is right; a long video explains, so its pictures stay 4 to 6 s
    target, low = (1.9, 1.1) if fmt == "short" else (4.6, 2.6)
    out: list[Any] = []
    for line in lines:
        words = list(getattr(line, "words", []) or [])
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
            if nxt is None or (span >= low and remaining >= low and (span >= target or pause > 0.22 or
                                                                    str(w.text)[-1:] in ",.;:?!")):
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
    return out


def request(title: str, lines: list[Any], sources: list[dict[str, Any]], chapters: list[Any],
            follow: set[int]) -> str:
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
        listed = "\n".join(f"    {j} [{sh['kind']}] {sh['text']}" for j, sh in enumerate(shots(page)))
        pages.append(f"[{i}] {page.get('title', '')[:90]} ({_domain(page.get('url', ''))})"
                     f"{' photo: yes' if page.get('photo') else ''}\n{listed or '    (no shots)'}")
    chap = "\n".join(f"- {getattr(m, 'number', '')} {getattr(m, 'title', '')} at {getattr(m, 'start', 0):.1f}s" for m in chapters)
    return (f"TITLE: {title}\n\nBEATS\n" + "\n".join(rows) + "\n\nCAPTURED PAGES\n" + ("\n".join(pages) or "none")
            + "\n\nCHAPTERS\n" + (chap or "none"))


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
          bookends: tuple[str, str] | None = None) -> dict[str, Any]:
    """The editor's answer as a timed edit list for compose.Composer. Line ranges are repaired so every
    line is covered once; references to pages, phrases or words that do not exist are dropped (the scene
    keeps its words), and every such repair is reported in the edit list's `notes`."""
    n = len(lines)
    notes: list[str] = []
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

    out: list[dict] = []
    for k, s in enumerate(fixed):
        t0 = 0.0 if k == 0 else float(lines[s["first_line"]].start) - 0.12
        t1 = duration if k == len(fixed) - 1 else float(lines[fixed[k + 1]["first_line"]].start) - 0.12
        t0, t1 = max(0.0, t0), max(t0 + 0.4, t1)
        dur = t1 - t0
        kind = s.get("type")
        words = s.get("screen_words") or " ".join(lines[s["first_line"]].text.split()[:6])
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

        if kind == "studio":
            out.append({"type": "host", "start": t0, "duration": dur, "data": {
                "place": "studio", "cues": _cues_between(cues, t0, t1), "poses": poses,
                "words": _screen_words(words, lines, t0, t1), "punch": (s.get("punch") or "").lower().strip(".,!?")}})
        elif kind == "source":
            src = s.get("source")
            page = sources[src] if isinstance(src, int) and 0 <= src < len(sources) else None
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
                out.append({"type": "photo", "start": t0, "duration": dur, "data": {
                    "image": capture_dir / page["photo"], "url": page.get("url", "")}})
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
            value = float(s["value"])
            out.append({"type": "stat_counter", "start": t0, "duration": dur, "in": "whip", "data": {
                "value": value, "prefix": s.get("prefix") or "", "suffix": s.get("suffix") or "",
                "decimals": 0 if value == int(value) else 1, "label": s.get("label") or ""}})
        elif kind == "compare" and s.get("rows"):
            rows = s["rows"][:4]
            out.append({"type": "comparison", "start": t0, "duration": dur, "in": "wipe", "data": {
                "left": s.get("left") or "", "right": s.get("right") or "",
                "rows": [[r["label"], r["a"], r["b"]] for r in rows],
                "winners": [r["winner"] if r["winner"] != "none" else None for r in rows],
                "gap": min(0.55, max(0.25, (dur - 0.8) / max(1, len(rows))))}})
        elif kind == "steps" and s.get("items"):
            items = s["items"][:4]
            times = []
            for i, item in enumerate(items):
                at = _phrase_time(lines, item, t0, t1)
                times.append(round((at - t0) if at is not None else 0.3 + i * min(0.7, (dur - 0.6) / len(items)), 3))
            out.append({"type": "steps", "start": t0, "duration": dur, "in": "wipe",
                        "data": {"heading": s.get("label") or "", "items": items, "at": times}})
        elif kind == "timeline" and len(s.get("points") or []) >= 2:
            out.append({"type": "timeline", "start": t0, "duration": dur, "in": "whip", "data": {"points": s["points"][:4]}})
        elif kind == "quote" and s.get("quote"):
            out.append({"type": "quote_card", "start": t0, "duration": dur, "in": "rise", "data": {
                "text": s["quote"], "who": s.get("quote_by") or "", "mark": [s.get("punch") or ""]}})
        elif kind == "logos" and s.get("brands") and logo_tiles:
            tiles = [t for t in (logo_tiles(b) for b in s["brands"][:4]) if t]
            if len(tiles) >= 1:
                out.append({"type": "logo_tiles", "start": t0, "duration": dur, "data": {
                    "tiles": [{"image": t} for t in tiles], "caption": s.get("screen_words") or ""}})
            else:
                notes.append(f"scene {k}: no logos found for {s['brands']}, shown as words")
                out.append(words_scene(" ".join(s["brands"][:4])))
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
            if kind not in ("words", None):
                notes.append(f"scene {k}: {kind} without its data, shown as words")
            out.append(words_scene())
    out = _no_repeats(out, lines, fmt, notes)
    out = _pace(out, lines, fmt)
    out = _lower_host(out, cues, fmt)
    if bookends and lines:
        out = _bookends(out, lines, cues, duration, *bookends)
    return {"format": fmt, "duration": duration, "scenes": out, "notes": notes, "captions": captions(lines, fmt),
            "chapters": [{"title": f"{getattr(m, 'number', '')} · {getattr(m, 'title', '')}".strip(" ·"),
                          "at": float(getattr(m, "start", 0))} for m in chapters]}


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
         "timeline": "explain", "quote_card": "think", "logo_tiles": "thumbs_up", "kinetic_title": "talk",
         "chapter_card": "talk", "follow_cta": "wave"}


# 2026-11-12 (owner): in long videos Goli stands right of the proof in (nearly) every scene and reacts to it:
# points at the page, is shocked by the number, counts through the steps, shrugs at a doubt; never the same
# gesture twice in a row for the same kind of card.
REACT_LONG = {"browser_shot": ["point_left", "point_up", "explain"], "photo": ["point_left", "think"],
              "stat_counter": ["shock", "point_left"], "comparison": ["shrug", "think", "explain"],
              "steps": ["explain", "point_up", "thumbs_up"], "timeline": ["point_left", "explain"],
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
            for c in corner:            # the editor's own reaction words for this card win
                if abs(c["start"] - scene["start"]) < 0.6:
                    for p in c["data"].get("poses", []):
                        if p["at"] > 0.3:
                            poses.append({"pose": p["pose"], "at": round(c["start"] - t0 + p["at"], 3)})
        poses = sorted(poses, key=lambda p: p["at"])
        # 2026-11-11 (owner): not always at the desk: every other run of cards he stands beside them
        place = ("lower", "side")[runs[0] % 2] if fmt == "short" else ("side", "side", "corner")[runs[0] % 3]
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


def captions(lines: list[Any], fmt: str) -> list[dict[str, Any]]:
    """Spoken-word captions, chunked as the illustration engine does (short: up to 4 words, long: 7)."""
    from ..vector.align import caption_chunks

    out = []
    for c in caption_chunks(lines, max_words=4 if fmt == "short" else 7):
        if not c.words:
            continue
        out.append({"start": round(float(c.words[0].start) - 0.05, 3), "end": round(float(c.end), 3),
                    "words": [{"text": w.text, "at": round(float(w.start), 3)} for w in c.words],
                    "keys": sorted(int(k) for k in c.keys)})
    return out


# 2026-11-11 (owner): "too slow": in the niche the picture changes every second or two. A stretch longer
# than a beat is cut at word boundaries into beats that each show something new.
BEAT = {"short": 2.2, "long": 6.5}
STUDIO_BEAT = {"short": 3.0, "long": 10.0}
HOLD = {"stat_counter", "comparison", "steps", "timeline", "quote_card", "logo_tiles", "chapter_card", "follow_cta"}


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
    beat, out = BEAT.get(fmt, 4.0), []
    for s in scenes:
        t0, t1 = s["start"], s["start"] + s["duration"]
        kind = s["type"]
        if kind == "host" and s["data"].get("place") != "studio":
            out.append(s)
            continue
        limit = STUDIO_BEAT[fmt] if kind == "host" else beat * 1.6 if kind in HOLD else beat
        if t1 - t0 <= limit:
            out.append(s)
            continue
        if kind in HOLD:                       # the card keeps time for its build, then the words carry on
            starts = [w.start for w in _spoken(lines, t0 + limit - 0.6, t1 - 0.8)]
            first = (starts[0] - 0.05) if starts else t0 + limit
            out.append(dict(s, duration=first - t0))
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
    for sc in scenes:
        kind = sc["type"]
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
