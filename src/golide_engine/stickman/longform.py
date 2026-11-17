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
- cover every sentence number once, in order; about one shot per 3-8 s (the sentence times are given);
- never more than two of the same kind in a row; rotate world shots (wide, closeup, walk) with graphics (icon,
  counter, chart, table, versus, list);
- every number in the script on screen (counter, chart or label), with an everyday comparison where it helps;
  numbers ONLY from the script and research, never invented (charts without real numbers use show_values false);
- a reaction closeup after every big claim or twist; re-hook moments (spoken title, stamp, versus) every 60-90 s;
- tag the first shot in each new place or era; a lower_third the first time each person appears;
- chapter cards: 1-2 silent title cards for 5 min, 3-6 for 10-15 min, 0-1 for 3 min (as the format says);
- cue mid-shot events with words from that shot's own sentences ("at": "word");
- end on a polaroid shot whose caption is the payoff line, cued 1-2 s before the end.
- cast: 2-4 ORIGINAL characters with distinct silhouettes and colours. Real people (a CEO, a founder) are generic
  puppets with a lower_third name card, never a likeness; no brand mascots or logos.
- labels: 1-4 words each, at most 3 per shot; characters' x between 250 and 1670.
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
    result = subprocess.run([sys.executable, "-m", "engine", command, str(project), *args], cwd=KIT, text=True,
                            capture_output=True, timeout=timeout, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
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
    result = subprocess.run([sys.executable, "-m", "golide_engine.stickman.collide", str(project)], capture_output=True,
                            text=True, timeout=1800,
                            env=dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT / "src"), os.environ.get("PYTHONPATH", "")])))
    if result.returncode != 0:
        raise RuntimeError(f"stickman collision check failed: {result.stderr[-800:]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


def storyboard(text, project: Path, title: str, doc: dict[str, Any], research: dict[str, Any], record=None) -> list[str]:
    """Write story.json, then check it: the kit's plan check and our collision check (owner 2026-11-17: no collision
    in anything). Problems go back to the writer once. Any collision still there after that is removed (the text
    that collides is taken out), so the video is clean. Returns the plan warnings left."""
    problems = ""
    left: list[str] = []
    for attempt in (1, 2):
        out = text.generate_json(instructions(), request(title, (project / "script.txt").read_text(encoding="utf-8"),
                                                         doc, research, problems), STORY_SCHEMA, max_output_tokens=60000)
        if record:
            record(f"stickman-story-{attempt}", out)
        story = json.loads(out.value["story_json"])
        story["title"] = title
        (project / "story.json").write_text(json.dumps(story, indent=1, ensure_ascii=False), encoding="utf-8")
        try:
            left = warnings(kit("plan", project, timeout=900))
        except RuntimeError as error:
            left = [str(error)]
        hit = collisions(project)["problems"] if not any("failed" in w for w in left) else []
        print(json.dumps({"status": "stickman_plan", "attempt": attempt, "warnings": len(left), "collisions": len(hit)}),
              flush=True)
        if not left and not hit:
            return []
        problems = "\n".join(f"- {w}" for w in left + hit)
    clean_up(project)
    return left


def clean_up(project: Path, rounds: int = 4) -> None:
    """The last resort: take out the text that still collides, until nothing does."""
    from .collide import drop

    for _ in range(rounds):
        found = collisions(project)
        if not found["problems"]:
            return
        story = drop(json.loads((project / "story.json").read_text(encoding="utf-8")), found["hits"])
        (project / "story.json").write_text(json.dumps(story, indent=1, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"status": "stickman_collisions_removed", "count": len(found["hits"])}), flush=True)
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
