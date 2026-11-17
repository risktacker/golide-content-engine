"""No collision in a Stickman long video (owner 2026-11-17: "I don't want collision in anything").

Draws real frames of every shot with the ReachMora engine (unchanged; its kit.label is wrapped from here before the
engine loads, to record where each word lands on screen) and finds:
- two pieces of text that touch,
- text leaving the frame,
- text over a character's head.
Run as `python -m golide_engine.stickman.collide <project>`; prints JSON {"problems": [...], "hits": [...]}.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KIT = ROOT / "vendor" / "reachmora"
FRACS = (0.35, 0.65, 0.95)       # labels pop in during a shot: look early, middle and at its end
PAD, MARGIN = 8.0, 0.02


def _boxes_overlap(a, b, pad=PAD):
    return min(a[2], b[2]) + pad > max(a[0], b[0]) and min(a[3], b[3]) + pad > max(a[1], b[1])


def _texts_touch(a, b, share=0.06):
    """Two words collide when their boxes really overlap: more than `share` of the smaller one (the boxes are
    measured from the font, a little taller than the ink, so stacked lines of one card do not count)."""
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return False
    small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])) or 1
    return w * h / small > share


def check(project: Path) -> dict:
    sys.path.insert(0, str(KIT))
    import skia
    import engine.kit as kit

    found: list[dict] = []
    original = kit.label

    def label(c, s, x, y, size, color, font=None, align="left", stroke=0, stroke_col=kit.INK, skew=-0.16, alpha=1.0,
              rot=0.0):
        if alpha > 0.5 and str(s).strip():
            f = skia.Font(font or kit.KALAM, size)
            w = f.measureText(s)
            ox = -w / 2 if align == "center" else -w if align == "right" else 0
            c.save(); c.translate(x, y); c.rotate(rot); c.skew(skew, 0)
            m = c.getTotalMatrix()
            c.restore()
            pts = [m.mapXY(px, py) for px, py in ((ox, -size * 0.78), (ox + w, -size * 0.78), (ox, size * 0.22), (ox + w, size * 0.22))]
            xs = [p.x() / kit.OS for p in pts]
            ys = [p.y() / kit.OS for p in pts]
            found.append({"text": str(s), "box": (min(xs), min(ys), max(xs), max(ys))})
        return original(c, s, x, y, size, color, font, align, stroke, stroke_col, skew, alpha, rot)

    kit.label = label
    from engine import render as R
    from engine import shots as SH

    R.setup(str(project))
    tl = R._G["tl"]
    problems, hits = [], []
    for i, spec in enumerate(tl.shots):
        try:
            shot = SH.build(spec, tl, R._G["cast"], R._G["env"])
            for q in FRACS:
                f = shot.f0 + int((shot.f1 - shot.f0 - 1) * q)
                R.draw_frame(shot, R.Frame(), f, False, False)
        except Exception as error:  # noqa: BLE001 - a shot the kit cannot draw (2026-11-17: an unknown icon)
            problems.append(f"shot {i} cannot be drawn: {str(error)[:200]}")
            hits.append({"shot": i, "broken": True, "text": ""})
            continue
        for q in FRACS:
            f = shot.f0 + int((shot.f1 - shot.f0 - 1) * q)
            found.clear()
            fr = R.Frame()
            if shot.pol and f / R.FPS >= shot.pol["t"]:
                R.draw_frame(shot, fr, int(shot.pol["t"] * R.FPS + 1), False, False)
                found.clear()
            R.draw_frame(shot, fr, f, False, False)
            t = round(f / R.FPS, 2)
            z, fx, fy, _ = shot.camera((f - shot.f0) / max(shot.f1 - shot.f0 - 1, 1))
            heads = [((a.head[0] - fx) * z + kit.W / 2, (a.head[1] - fy) * z + kit.H / 2, 95 * a.s * z) for a in shot.actors]
            for k, a in enumerate(found):
                x0, y0, x1, y1 = a["box"]
                if x0 < kit.W * MARGIN or y0 < kit.H * MARGIN or x1 > kit.W * (1 - MARGIN) or y1 > kit.H * (1 - MARGIN):
                    problems.append(f'shot {i} at {t}s: "{a["text"]}" leaves the frame')
                    hits.append({"shot": i, "text": a["text"]})
                for b in found[k + 1:]:
                    if a["text"] != b["text"] and _texts_touch(a["box"], b["box"]):
                        problems.append(f'shot {i} at {t}s: "{a["text"]}" and "{b["text"]}" touch')
                        hits.append({"shot": i, "text": b["text"]})
                for hx, hy, r in heads:
                    if _boxes_overlap(a["box"], (hx - r, hy - r * 1.1, hx + r, hy + r), pad=0):
                        problems.append(f'shot {i} at {t}s: "{a["text"]}" covers a character\'s head')
                        hits.append({"shot": i, "text": a["text"]})
    return {"problems": list(dict.fromkeys(problems)), "hits": hits}


def drop(story: dict, hits: list[dict]) -> dict:
    """The last resort, so the finished video is clean: the text that still collides is taken out of its shot
    (a label, a tag, a lower third, a stamp, a caption); the shot itself and its story stay."""
    shots = story.get("shots") or []
    broken = {h["shot"] for h in hits if h.get("broken")}
    for i in sorted(broken):
        # a shot the kit cannot draw takes a plain copy of the nearest shot that draws (its set and characters,
        # nothing timed to words), over its own sentences
        good = [j for j in sorted(range(len(shots)), key=lambda j: abs(j - i)) if j != i and j not in broken]
        if not good:
            continue
        twin = json.loads(json.dumps(shots[good[0]]))
        for key in ("labels", "props", "bubble", "tag", "caption", "lower_third", "stamp", "polaroid", "icons",
                    "value", "compare", "items", "left", "right", "at"):
            twin.pop(key, None)
        if twin.get("kind") not in ("wide", "closeup", "walk", "crowd", "table"):
            twin = {"kind": "wide", "set": "office", "chars": []}
        for c in twin.get("chars") or []:
            c.pop("beats", None)
        twin["s"] = shots[i].get("s")
        shots[i] = twin
    for h in hits:
        if h.get("broken"):
            continue
        if not 0 <= h["shot"] < len(shots):
            continue
        sp, text = shots[h["shot"]], h["text"].strip().lower()
        if sp.get("labels"):
            sp["labels"] = [l for l in sp["labels"] if str(l.get("text", "")).strip().lower() != text]
        for key in ("tag", "caption"):
            if str(sp.get(key, "")).strip().lower() == text:
                sp.pop(key)
        for key in ("lower_third", "stamp"):
            if isinstance(sp.get(key), dict) and text in json.dumps(sp[key]).lower():
                sp.pop(key)
        for side in ("left", "right"):
            if isinstance(sp.get(side), dict) and str(sp[side].get("title", "")).strip().lower() == text:
                sp[side].pop("title")
    return story


if __name__ == "__main__":
    print(json.dumps(check(Path(sys.argv[1]))))
