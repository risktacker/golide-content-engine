"""The editor (production plan step 4): one model call turns the day's words into an edit list.

The model is the editor. It sees every spoken line with its time, the real pages captured for the
story (and the exact phrases found on each), and the house rules (skills/golide-edit/SKILL.md, in
short). It answers with scenes over line ranges. Code then does what code is good at: exact times
from the owner's recording, spoken-word times for every move, Goli's pose and mouth timing, and
checks that every reference it was given is real.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

POSES = ["talk", "explain", "point", "point_up", "point_left", "shock", "think", "thumbs_up", "shrug", "wave"]
TYPES = ["studio", "source", "stat", "compare", "steps", "timeline", "quote", "words", "logos", "chapter", "follow"]

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
pangolin in a GOLIDE hoodie who talks with the owner's voice from a studio desk. You cut a {"vertical Short" if short else "long video"}
the way the best channels in the niche do (AI Terry, Outskill): real proof on screen, a new picture every
{"1.5 to 2.5" if short else "2 to 4"} seconds, the host bringing the viewer back between the proof.

You get the spoken lines (numbered, with times), the real pages captured for this story with the exact phrases
found on each, and the chapters. Return scenes that cover every line exactly once, in order, with no gaps:
scene N+1's first_line = scene N's last_line + 1; the first scene starts at line 0 and the last ends at the last line.

Scene types (fill only the fields the type uses, null or [] for the rest):
- studio: Goli at his desk, the screen behind him shows screen_words (max 6 words, the line's hook, never a full
  sentence) with one punch word. Use it to open (line 0), to come back between proof runs, and to land the payoff.
  poses: 1 to 3, each on a word actually spoken in the scene (talk, explain, point, point_up, point_left, shock,
  think, thumbs_up, shrug, wave). shock for a surprising number, think for a question, thumbs_up for a win,
  shrug for a limit, explain for how it works.
- source: a real captured page as a card (source = page index, phrase = phrase index on that page to highlight,
  callout = the fact in at most 4 words, e.g. "$40", callout_sub = what it is in 3 to 6 words, edge glass or fade).
  Use it whenever a line states a fact a captured page shows. Prefer this over any drawn card: real proof first.
  goli_corner true lets Goli react in a corner bubble (do it on about half of the source scenes, with 1 to 2 poses).
- stat: one number that matters (value as a number, prefix like "$", suffix like "%" or "x", label 2 to 5 words).
- compare: left vs right with 2 to 4 rows (label, a, b, winner).
- steps: 2 to 4 short imperative items (max 5 words each) when the line tells the viewer what to do.
- timeline: 3 to 4 points (when, what) when the line moves through time.
- quote: a short real quote from the research (quote, quote_by).
- words: kinetic words for a line with no proof and no number: screen_words (max 6 words) and a punch word.
- logos: 2 to 4 real product or company names (brands) when the line names them together.
- chapter: on the first line of a chapter: label = the chapter title.
- follow: the line that asks the viewer to follow (marked FOLLOW): label = the reason, max 6 words.

House rules: proof before claims; never two scenes of the same type in a row, except source after source
when they are different pages; no studio scene longer than {"4" if short else "8"} seconds; screen text never
repeats the spoken sentence word for word, it names the point; numbers and names exactly as in the lines or
on the page, never invented. Only use source and phrase indexes that are listed. Every pose word must be a word
spoken inside that scene."""


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
        found = "; ".join(f"{j}: \"{h['phrase']}\"" for j, h in enumerate(page.get("highlights") or []))
        pages.append(f"[{i}] {page.get('title', '')[:90]} ({_domain(page.get('url', ''))})\n    phrases: {found or 'none'}")
    chap = "\n".join(f"- {getattr(m, 'number', '')} {getattr(m, 'title', '')} at {getattr(m, 'start', 0):.1f}s" for m in chapters)
    return (f"TITLE: {title}\n\nLINES\n" + "\n".join(rows) + "\n\nCAPTURED PAGES\n" + ("\n".join(pages) or "none")
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
          capture_dir: Path | None, cues: list[dict], chapters: list[Any], logo_tiles=None) -> dict[str, Any]:
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
            spots = page.get("highlights") or []
            ph = s.get("phrase")
            spot = spots[ph] if isinstance(ph, int) and 0 <= ph < len(spots) else None
            highlights = []
            if spot:
                at = _phrase_time(lines, spot["phrase"], t0, t1)
                highlights.append({"rect": spot["rects"][0], "ring": len(spot["phrase"]) <= 8,
                                   "at": round(max(0.9, (at - t0) if at is not None else 1.2), 3),
                                   "label": s.get("callout") or None, "sub": s.get("callout_sub") or ""})
            elif ph is not None:
                notes.append(f"scene {k}: phrase {ph} not on page {src}")
            out.append({"type": "browser_shot", "start": t0, "duration": dur, "data": {
                "image": capture_dir / page["top"],
                "url": page.get("url", ""), "edge": s.get("edge") or "glass",
                "page_width": 1440, "highlights": [h for h in highlights if h]}})
            if s.get("goli_corner") and dur >= 1.8:
                out.append({"type": "host", "start": t0 + 0.35, "duration": dur - 0.35, "data": {
                    "place": "corner", "cues": _cues_between(cues, t0 + 0.35, t1),
                    "poses": [dict(p, at=max(0, p["at"] - 0.35)) for p in poses] or [{"pose": "point_left", "at": 0}]}})
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
            out.append({"type": "follow_cta", "start": t0, "duration": dur, "data": {"reason": s.get("label") or ""}})
            out.append({"type": "host", "start": t0 + 0.3, "duration": max(0.5, dur - 0.3), "data": {
                "place": "corner", "cues": _cues_between(cues, t0 + 0.3, t1), "poses": [{"pose": "wave", "at": 0}]}})
        else:
            if kind not in ("words", None):
                notes.append(f"scene {k}: {kind} without its data, shown as words")
            out.append(words_scene())
    if fmt == "short":
        out = _lower_host(out, cues)
    return {"format": fmt, "duration": duration, "scenes": out, "notes": notes,
            "chapters": [{"title": f"{getattr(m, 'number', '')} · {getattr(m, 'title', '')}".strip(" ·"),
                          "at": float(getattr(m, "start", 0))} for m in chapters]}


def save(edit: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(edit, indent=2, default=str) + "\n", encoding="utf-8")


# A Short shows the proof on top and keeps Goli at his desk below it for the whole run of cards
# (owner 2026-11-11: no empty space above and below the cards). His pose follows each card.
REACT = {"browser_shot": "point_up", "stat_counter": "shock", "comparison": "explain", "steps": "point_up",
         "timeline": "explain", "quote_card": "think", "logo_tiles": "thumbs_up", "kinetic_title": "talk",
         "chapter_card": "talk", "follow_cta": "wave"}


def _lower_host(scenes: list[dict], cues: list[dict]) -> list[dict]:
    corner = [s for s in scenes if s["type"] == "host" and s["data"].get("place") == "corner"]
    main = [s for s in scenes if s not in corner]
    out: list[dict] = []
    run: list[dict] = []

    def close():
        if not run:
            return
        t0 = run[0]["start"]
        t1 = run[-1]["start"] + run[-1]["duration"]
        poses = []
        for scene in run:
            poses.append({"pose": REACT.get(scene["type"], "talk"), "at": round(scene["start"] - t0, 3)})
            for c in corner:            # the editor's own reaction words for this card win
                if abs(c["start"] - scene["start"]) < 0.6:
                    for p in c["data"].get("poses", []):
                        if p["at"] > 0.3:
                            poses.append({"pose": p["pose"], "at": round(c["start"] - t0 + p["at"], 3)})
        poses = sorted(poses, key=lambda p: p["at"])
        out.append({"type": "host", "start": t0, "duration": t1 - t0, "data": {
            "place": "lower", "cues": [{"start": round(c["start"] - t0, 3), "value": c["value"]}
                                       for c in cues if t0 <= c["start"] < t1], "poses": poses}})
        run.clear()

    for scene in main:
        if scene["type"] == "host":
            close()
        else:
            run.append(scene)
        out.append(scene)
    close()
    return sorted(out, key=lambda s: (s["start"], s["type"] == "host"))
