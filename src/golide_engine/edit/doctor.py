"""The doctor (owner 2026-11-25): "if something is broken before it goes, it has to be fixed before it goes".

After the render and before YouTube, the finished video is read every 0.5 s against the script, the way the owner
reviews it. Every block is checked:

- black or empty: its picture area shows nothing (a black box, a blank page, a TV with nothing on it);
- repeated: the same picture shown again (a product the line names may come back, up to 3 times);
- off the words: a picture whose page names nothing the sentence says;
- held too long: a chapter card past the moment its stage is named, a number card past 3 s.

Every finding gets a free fix from what the engine already has (the next real picture that matches the words, else
Goli in the studio with the line's own words on the TV, which is always valid), the video is rendered again and
read again. After two rounds anything still wrong becomes the studio block, so a video never goes out broken and
never waits on anyone. Each finding is also written as a general rule for the lessons (edit/lessons.py).
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

STEP = 0.5                      # seconds between the frames read
W, H = 320, 180                 # long frames are read at this size (a Short at 180 x 320)
PICTURES = ("photo", "browser_shot", "source", "walkthrough", "steps", "object3d")
ROUNDS = 2

# the rule each kind of finding teaches (never a topic or a thing's name: lessons are general)
RULES = {
    "empty": "Never leave a block's picture area empty: a scene needs a real captured picture or the line's own words.",
    "repeat": "Never show the same picture twice unless it is the product the line names (3 times at most).",
    "off_words": "A picture must come from a page that names what its sentence says; otherwise use the line's words.",
    "long_card": "A chapter card leaves the moment its stage is named; a number card holds 3 seconds at most.",
    "unplanned": "Every sentence's named thing must be on screen while it is said: build each scene from its plan row.",
}


def frames(video: Path, fmt: str) -> np.ndarray:
    """The finished video, one grey frame every STEP seconds, small."""
    w, h = (W, H) if fmt != "short" else (H, W)
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={1 / STEP:g},scale={w}:{h}", "-f", "rawvideo",
         "-pix_fmt", "gray", "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(-1, h, w)


def picture_box(sc: dict, fmt: str) -> tuple[float, float, float, float]:
    """Where a scene's picture sits, as fractions of the frame (x0, y0, x1, y1)."""
    if sc["type"] == "host" and sc["data"].get("place") == "studio":
        from . import studio
        x0, y0, x1, y1 = studio.screen_rect(fmt)
        fw, fh = (1920, 1080) if fmt != "short" else (1080, 1920)
        return x0 / fw + 0.02, y0 / fh + 0.06, x1 / fw - 0.02, y1 / fh - 0.04
    if fmt == "short":
        return 0.12, 0.10, 0.88, 0.52            # the proof sits on top, above the captions
    return 0.04, 0.10, 0.70, 0.86                # beside Goli's quarter


def empty_box(img: np.ndarray, box) -> bool:
    """Nothing to see: almost flat and almost no edges (a black box, a blank page, an unlit TV)."""
    h, w = img.shape
    x0, y0, x1, y1 = box
    a = img[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)].astype(np.int16)
    if a.size < 100:
        return False
    edges = (np.abs(np.diff(a, axis=0)).mean() + np.abs(np.diff(a, axis=1)).mean()) / 2
    return float(a.std()) < 9 and edges < 2.5


def dhash(img: np.ndarray, box) -> int:
    h, w = img.shape
    x0, y0, x1, y1 = box
    a = img[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)].astype(np.float32)
    if a.size < 100:
        return 0
    ys = np.linspace(0, a.shape[0] - 1, 8).astype(int)
    xs = np.linspace(0, a.shape[1] - 1, 9).astype(int)
    s = a[np.ix_(ys, xs)]
    bits = (s[:, 1:] > s[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def _words(text: str) -> set[str]:
    from .editor import _SCREEN_STOP
    return {w for w in re.findall(r"[a-z0-9]+", str(text).lower()) if len(w) > 3 and w not in _SCREEN_STOP}


def _said(lines, sc: dict) -> str:
    from .editor import _spoken
    return " ".join(str(w.text) for w in _spoken(lines, sc["start"], sc["start"] + sc["duration"]))


def _picture_of(sc: dict) -> str:
    d = sc["data"]
    return str(d.get("screen") or d.get("image") or "")


def _page_words(path: str, sources: list[dict]) -> tuple[set[str], set[str]]:
    """The words of the page a picture came from (title and subject), and the subject's own words."""
    name = Path(path).name
    for p in sources or []:
        files = {str(p.get(k) or "") for k in ("top", "full", "photo")} | set(map(str, p.get("photos") or []))
        if name and name in {Path(f).name for f in files if f}:
            who = str(p.get("subject") or p.get("product") or "")
            return _words(str(p.get("title") or "") + " " + who), _words(who)
    return set(), set()


def examine(edit: dict[str, Any], video: Path | None, lines, sources: list[dict]) -> list[dict[str, Any]]:
    """Every finding in the finished video: {scene index, kind, why}."""
    from .editor import CARD_MAX, _chapter_end
    fmt = edit["format"]
    scenes = edit["scenes"]
    found: list[dict[str, Any]] = []
    shots = frames(video, fmt) if video and Path(video).exists() else None
    seen: dict[int, int] = {}
    shown: Counter = Counter()
    for i, sc in enumerate(scenes):
        d = sc["data"]
        main = sc["type"] in PICTURES or (sc["type"] == "host" and d.get("place") == "studio"
                                          and not d.get("intro") and not d.get("outro"))
        if sc["type"] in CARD_MAX:
            limit = _chapter_end(sc, lines) if sc["type"] == "chapter_card" else CARD_MAX[sc["type"]]
            if sc["duration"] > limit + 0.35:
                found.append({"scene": i, "kind": "long_card", "why": f"{sc['type']} held {sc['duration']:.1f} s"})
        if not main:
            continue
        said = _said(lines, sc)
        pic = _picture_of(sc)
        if pic and sc["type"] != "steps":
            keys, subject = _page_words(pic, sources)
            words = _words(said)
            product = bool(subject) and subject <= words
            if keys and not (keys & words) and sc["type"] != "walkthrough":
                found.append({"scene": i, "kind": "off_words", "why": f"{Path(pic).name} names nothing said"})
            shown[pic] += 1
            if shown[pic] > (3 if product else 1):
                found.append({"scene": i, "kind": "repeat", "why": f"{Path(pic).name} shown {shown[pic]} times"})
        if shots is None:
            continue
        if sc["type"] == "host" and d.get("place") == "studio" and (d.get("shot") or "main") != "main":
            # 2026-11-27: in the living studio the camera moves (wide, close, screen): the TV is only at its fixed place
            # in the main shot. Read elsewhere, the wall looked "empty" and good pictures were swapped for words.
            continue
        box = picture_box(sc, fmt)
        a = int((sc["start"] + 0.6) / STEP)              # after its entrance
        b = int((sc["start"] + sc["duration"] - 0.2) / STEP)
        idx = [k for k in range(a, b + 1) if 0 <= k < len(shots)]
        if not idx:
            continue
        flat = sum(empty_box(shots[k], box) for k in idx)
        if flat >= max(1, 0.6 * len(idx)):
            found.append({"scene": i, "kind": "empty", "why": f"{sc['type']} empty for {flat * STEP:.1f} s"})
            continue
        if sc["type"] in PICTURES or d.get("screen"):
            h = dhash(shots[idx[len(idx) // 2]], box)
            twin = next((j for j, hj in seen.items() if bin(h ^ hj).count("1") <= 4 and j != i - 1), None)
            if twin is not None and not any(f["scene"] == i for f in found):
                keys, subject = _page_words(pic, sources)
                if not (subject and subject <= _words(said)):
                    found.append({"scene": i, "kind": "repeat", "why": f"looks the same as scene {twin}"})
            seen[i] = h
    return found


def treat(edit: dict[str, Any], found: list[dict[str, Any]], lines, cues: list[dict], sources: list[dict],
          capture_dir: Path | None, final: bool = False) -> list[str]:
    """Fix every finding for free. A held card is trimmed; anything else takes the next real picture that matches
    its words (not in the last round), else Goli in the studio saying the line with its words on the TV."""
    from .editor import _cap_cards, _screen_pictures, _screen_words, _studio
    notes: list[str] = []
    scenes = edit["scenes"]
    out = list(scenes)
    once: dict[int, dict] = {}                         # one fix per scene (several findings, one cure)
    for f in found:
        if f["kind"] == "long_card" or f["scene"] not in once:
            once.setdefault(f["scene"] if f["kind"] != "long_card" else -1 - f["scene"], f)
    for f in sorted(once.values(), key=lambda f: -f["scene"]):
        sc = scenes[f["scene"]]
        if f["kind"] == "long_card":
            continue                                    # trimmed together below
        start, end = sc["start"], sc["start"] + sc["duration"]
        said = _said(lines, sc)
        host = _studio(start, end, cues)
        host["data"]["words"] = _screen_words(said, lines, start, end)
        host["data"]["doctor"] = f["kind"]
        if sc["type"] == "host" and sc["data"].get("place") == "studio":
            sc["data"].pop("screen", None)              # its picture was the trouble: the line's words instead
            sc["data"]["words"] = host["data"]["words"]
            sc["data"]["doctor"] = f["kind"]
        else:
            out[next(k for k, x in enumerate(out) if x is sc)] = host
        notes.append(f"doctor: {sc['type']} at {start:.1f}s ({f['why']}) -> "
                     + ("the studio with the line's words" if final else "a real picture or the line's words"))
    if any(f["kind"] == "long_card" for f in found):
        out = _cap_cards(out, lines, cues, notes)
    if not final:
        used = {_picture_of(s) for s in out if _picture_of(s)}
        fresh = [s for s in out if s["data"].get("doctor") and s["type"] == "host"]
        if fresh and capture_dir:
            # the studio TV may take a real matching picture not used yet (never one that was the trouble)
            bad = {Path(_picture_of(scenes[f["scene"]])).name for f in found if _picture_of(scenes[f["scene"]])}
            _screen_pictures(fresh, sources, capture_dir, lines, cues, notes)
            taken = {Path(u).name for u in used}
            for s in fresh:
                if _picture_of(s) and Path(_picture_of(s)).name in taken | bad:
                    s["data"].pop("screen", None)
    edit["scenes"] = sorted(out, key=lambda s: (s["start"], s["type"] == "host"))
    return notes


def run(edit: dict[str, Any], folder: Path, video: Path, lines, cues: list[dict], sources: list[dict],
        capture_dir: Path | None, rerender) -> dict[str, Any]:
    """Read, fix, render again, read again; at most ROUNDS fixes, then the studio block for anything left.
    rerender() renders the current edit list to `video`. Returns the report (also saved as doctor.json)."""
    report: dict[str, Any] = {"rounds": [], "rules": [RULES["unplanned"]] if edit.get("plan_misses") else [],
                               "plan_misses": edit.get("plan_misses") or []}
    for r in range(ROUNDS + 1):
        found = examine(edit, video, lines, sources)
        report["rounds"].append({"round": r, "found": found})
        for f in found:
            print(f"::notice title=Doctor::{f['kind']}: scene {f['scene']} ({f['why']})")
        if not found:
            break
        report["rules"] += [RULES[f["kind"]] for f in found]
        if r == ROUNDS:
            report["left"] = found                     # should never happen: the studio block is always valid
            break
        report.setdefault("notes", []).extend(
            treat(edit, found, lines, cues, sources, capture_dir, final=r == ROUNDS - 1))
        rerender()
    report["fixed"] = sum(len(x["found"]) for x in report["rounds"][:-1]) if len(report["rounds"]) > 1 else 0
    (folder / "doctor.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    return report
