"""Collision check (owner 2026-11-12): nothing on screen may overlap: object on object, text on text,
captions on anything, Goli on the proof.

The finished composition is opened in headless Chrome and seeked to several moments of every scene
and every caption line. Every visible box (screenshot cards, cards, texts, source tags, logos, Goli,
captions, the brand marks) is measured. Then, in order of what may give way:
1. a caption line moves to the nearest free band at its moment;
2. Goli moves to his other spot (Short: side <-> desk, long: side <-> corner), and steps out of the
   scene when both collide;
3. a source tag that touches something is dropped for that scene;
4. the brand corner marks hide while they would touch content.
It runs again after the changes (up to 3 rounds); anything left is reported in the edit list's notes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROBE = r"""
(t) => {
  for (const c of document.querySelectorAll('.clip')) {
    const s = +c.dataset.start, d = +c.dataset.duration;
    c.style.display = (t >= s && t < s + d) ? '' : 'none';
  }
  window.__timelines.main.seek(t, false);
  const out = [];
  const boxes = [...document.querySelectorAll('[data-box]')];
  for (const el of boxes) {
    let o = 1, e = el, shown = true;
    while (e && e !== document.body) {
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden') { shown = false; break; }
      o *= parseFloat(cs.opacity);
      e = e.parentElement;
    }
    if (!shown || o < 0.35) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 6 || r.height < 6) continue;
    const scene = el.closest('.clip');
    const cap = el.closest('.cap');
    out.push({ i: boxes.indexOf(el), id: el.id || '', kind: el.dataset.box, cap: cap ? cap.id : '',
               floor: el.dataset.floor ? +el.dataset.floor : null, scene: scene ? scene.id : el.closest('#caps') ? 'caps' : 'brand',
               x: r.left, y: r.top, w: r.width, h: r.height,
               inside: boxes.filter((p) => p !== el && p.contains(el)).map((p) => boxes.indexOf(p)) });
  }
  return out;
}
"""

# 2026-11-13 (owner, point 5): every scene is measured for its smallest readable text and how much of the frame
# its content fills; a scene that is too small or mostly empty is enlarged before anything else is checked.
TEXT_PROBE = r"""
(t) => {
  for (const c of document.querySelectorAll('.clip')) {
    const s = +c.dataset.start, d = +c.dataset.duration;
    c.style.display = (t >= s && t < s + d) ? '' : 'none';
  }
  window.__timelines.main.seek(t, false);
  const out = {};
  for (const sec of document.querySelectorAll('section.scene.clip')) {
    if (sec.style.display === 'none' || sec.id.includes('-host')) continue;
    let small = 1e9, x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, n = 0;
    const visible = (el) => { let o = 1, e = el;
      while (e && e !== sec) { const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return 0;
        o *= parseFloat(cs.opacity); e = e.parentElement; } return o; };
    for (const el of sec.querySelectorAll('*')) {
      if (el.closest('.bar') || el.classList.contains('url')) continue;
      const own = [...el.childNodes].some((k) => k.nodeType === 3 && k.textContent.trim().length > 1);
      const pic = ['IMG', 'CANVAS', 'svg'].includes(el.tagName) || el.classList.contains('card') || el.classList.contains('frame');   // words, pictures and the cards around them; not full-width containers
      if (!own && !pic) continue;
      if (visible(el) < 0.35) continue;
      const er = el.getBoundingClientRect();
      let r = er;
      if (own && !(el instanceof SVGElement)) { const rg = document.createRange(); rg.selectNodeContents(el); r = rg.getBoundingClientRect(); }
      // what a card with overflow hidden cuts off is not on screen (a page zoomed inside its card)
      let cx0 = r.left, cy0 = r.top, cx1 = r.right, cy1 = r.bottom;
      for (let a = el.parentElement; a && a !== sec; a = a.parentElement) {
        const ov = getComputedStyle(a).overflow;
        if (ov === 'visible') continue;
        const ar = a.getBoundingClientRect();
        cx0 = Math.max(cx0, ar.left); cy0 = Math.max(cy0, ar.top); cx1 = Math.min(cx1, ar.right); cy1 = Math.min(cy1, ar.bottom);
      }
      r = { left: cx0, top: cy0, right: cx1, bottom: cy1, width: cx1 - cx0, height: cy1 - cy0 };
      if (r.width < 4 || r.height < 4 || r.right < 0 || r.left > innerWidth) continue;
      if (own) {
        const svgText = el instanceof SVGElement;
        const scale = !svgText && el.offsetWidth ? er.width / el.offsetWidth : 1;
        const px = svgText ? r.height * 0.78 : parseFloat(getComputedStyle(el).fontSize) * scale;
        if (px > 4) small = Math.min(small, px);
      }
      x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); n++;
    }
    if (n) out[sec.id] = { small: small < 1e9 ? small : null, fill: Math.max(0, (x1 - x0) * (y1 - y0)) / (innerWidth * innerHeight),
                           box: [x0, y0, x1, y1] };
  }
  return out;
}
"""

MIN_TEXT = {"long": 26.0, "short": 30.0}   # px on the 1080-high frame: smaller is unreadable on a phone
MIN_FILL = 0.22                            # content covering less than this share of the frame looks empty
MAX_BOOST = {"long": 1.6, "short": 1.4}


def legibility(edit: dict[str, Any], comp_builder, comp: Path, size: tuple[int, int]) -> list[str]:
    """Measure each scene after it has come in; enlarge the ones with tiny text or an empty frame."""
    from playwright.sync_api import sync_playwright

    fmt = edit["format"]
    comp_builder(edit)
    scenes = [sc for sc in edit["scenes"] if sc["type"] not in ("host",)]
    notes: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": size[0], "height": size[1]})
        page.add_init_script("window.__timelines = {};")
        page.goto((comp / "index.html").as_uri())
        page.wait_for_function("() => !!(window.__timelines && window.__timelines.main)", timeout=20000)
        page.evaluate("document.fonts.ready")
        for sc in scenes:
            t = round(sc["start"] + min(sc["duration"] * 0.75, max(0.2, sc["duration"] - 0.3)), 3)
            got = page.evaluate(TEXT_PROBE, t)
            if not got:
                continue
            m = max(got.values(), key=lambda v: v["fill"])
            boost = 1.0
            if m["small"] and m["small"] < MIN_TEXT[fmt]:
                boost = max(boost, MIN_TEXT[fmt] / m["small"])
            if m["fill"] < MIN_FILL:
                boost = max(boost, (MIN_FILL / max(m["fill"], 0.05)) ** 0.5)
            # as far as this scene's own content can grow without reaching Goli (long: his quarter on the right)
            # or the frame's edges; it grows from the zone's anchor (long) or the middle (Short)
            w, h = size
            x0, y0, x1, y1 = m["box"]
            if fmt == "long":
                ox, oy = 0.02 * w, h / 2
                fit = lambda right: min((right - ox) / max(1.0, x1 - ox), (oy - 40) / max(1.0, oy - y0),
                                        (h - 60 - oy) / max(1.0, y1 - oy))
                room, beside = fit(w - 40), fit(w - 470)
                # 2026-11-13 (owner): a wide design that needs Goli's quarter gets it: he fades out for this scene
                # ...but Goli stays the host: his steps aside for space add up to at most 10% of the video
                away = sum(b - a for a, b in edit.get("goli_gaps", []))
                if min(boost, room, MAX_BOOST[fmt]) > beside + 0.02 and \
                        away + sc["duration"] <= 0.10 * float(edit.get("duration") or 1e9):
                    edit.setdefault("goli_gaps", []).append([sc["start"], round(sc["start"] + sc["duration"], 3)])
                else:
                    room = min(room, beside)
            else:
                ox, oy = w / 2, h / 2
                room = min((w / 2 - 30) / max(1.0, max(ox - x0, x1 - ox)), (h / 2 - 60) / max(1.0, max(oy - y0, y1 - oy)))
            boost = round(max(1.0, min(boost, room, MAX_BOOST[fmt])), 3)
            if boost > 1.01:
                sc["data"]["boost"] = boost
                notes.append(f"{sc['type']} at {sc['start']:.1f}s enlarged x{boost} (smallest text "
                             f"{(m['small'] or 0):.0f}px, fills {m['fill']:.0%})")
        browser.close()
    return notes


# 2026-11-13 (owner: "objects can't be reaching the edges"): YouTube fills a tall phone with a Short and crops its
# sides (about 9% each side on a 19.5:9 screen), the like/comment column covers the right, the Shorts bar the top.
# Every scene's content stays inside this box, measured through the whole scene (after it lands, before it leaves).
SAFE = {"short": (130, 230, 1080 - 160, 1920 - 120), "long": (36, 30, 1920 - 36, 1080 - 30)}


def safe_factor(box: list[float], fmt: str, size: tuple[int, int]) -> float:
    """How much a box (x0, y0, x1, y1) must shrink about the scene's scale origin to sit inside the safe area."""
    w, h = size
    l, t, r, b = SAFE[fmt] if fmt in SAFE else (30, 30, w - 30, h - 30)
    ox, oy = (0.02 * w, h / 2) if fmt == "long" else (w / 2, h / 2)
    x0, y0, x1, y1 = box
    f = 1.0
    if x0 < l and ox - x0 > 1:
        f = min(f, (ox - l) / (ox - x0)) if ox > l else f
    if x1 > r and x1 - ox > 1:
        f = min(f, (r - ox) / (x1 - ox))
    if y0 < t and oy - y0 > 1:
        f = min(f, (oy - t) / (oy - y0))
    if y1 > b and y1 - oy > 1:
        f = min(f, (b - oy) / (y1 - oy))
    return max(0.5, f)


def keep_inside(edit: dict[str, Any], comp_builder, comp: Path, size: tuple[int, int]) -> list[str]:
    """Shrink every scene whose content goes past the safe area at any moment of its time on screen."""
    from playwright.sync_api import sync_playwright

    fmt = edit["format"]
    comp_builder(edit)
    notes: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": size[0], "height": size[1]})
        page.add_init_script("window.__timelines = {};")
        page.goto((comp / "index.html").as_uri())
        page.wait_for_function("() => !!(window.__timelines && window.__timelines.main)", timeout=20000)
        page.evaluate("document.fonts.ready")
        for sc in [x for x in edit["scenes"] if x["type"] != "host"]:
            a, d = float(sc["start"]), float(sc["duration"])
            times = sorted({round(a + min(0.45, d * 0.4), 3), round(a + d * 0.6, 3), round(a + max(d * 0.6, d - 0.35), 3)})
            worst = 1.0
            for t in times:
                for v in (page.evaluate(TEXT_PROBE, t) or {}).values():
                    worst = min(worst, safe_factor(v["box"], fmt, size))
            if worst < 0.99:
                old = float(sc["data"].get("boost") or 1.0)
                sc["data"]["boost"] = round(old * worst * 0.98, 3)
                notes.append(f"{sc['type']} at {a:.1f}s kept inside the frame (x{sc['data']['boost']})")
        browser.close()
    return notes


GIVE_WAY = {"caption": 0, "brand": 1, "chip": 2, "goli": 3, "logo": 4, "text": 5, "card": 6}


def _shrink(b: dict) -> dict:
    """Goli's drawing does not fill its box: measure the character, not the empty corners."""
    if b["kind"] != "goli":
        return b
    out = dict(b, x=b["x"] + b["w"] * .14, y=b["y"] + b["h"] * .04, w=b["w"] * .72, h=b["h"] * .9)
    if b.get("floor"):                     # seated: everything under the desk top is hidden by the desk
        out["h"] = max(1.0, min(out["h"], b["floor"] - out["y"]))
    return out


def _overlap(a: dict, b: dict) -> float:
    a, b = _shrink(a), _shrink(b)
    w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    if w <= 0 or h <= 0:
        return 0.0
    return (w * h) / max(1.0, min(a["w"] * a["h"], b["w"] * b["h"]))


def collisions(boxes: list[dict], limit: float = 0.03) -> list[tuple[dict, dict, float]]:
    out = []
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if a["i"] in b["inside"] or b["i"] in a["inside"]:
                continue                       # a text inside its own card is not a collision
            if a["scene"] == b["scene"] and "-host" in a["scene"]:
                continue                       # Goli and his own bubble
            o = _overlap(a, b)
            if o > limit:
                out.append((a, b, o))
    return out


def probe(comp: Path, size: tuple[int, int], times: list[float]) -> dict[float, list[dict]]:
    from playwright.sync_api import sync_playwright

    result: dict[float, list[dict]] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": size[0], "height": size[1]})
        page.add_init_script("window.__timelines = {};")
        page.goto((comp / "index.html").as_uri())
        page.wait_for_function("() => !!(window.__timelines && window.__timelines.main)", timeout=20000)
        page.evaluate("document.fonts.ready")
        for t in times:
            result[round(t, 3)] = page.evaluate(PROBE, t)
        browser.close()
    return result


def _times(edit: dict[str, Any]) -> list[float]:
    ts: set[float] = set()
    for sc in edit["scenes"]:
        a, d = float(sc["start"]), float(sc["duration"])
        for t in (a + min(0.8, d * .45), a + d * .6, a + d - 0.12):
            if 0 <= t < edit["duration"]:
                ts.add(round(t, 2))
    for c in edit.get("captions") or []:
        for t in (c["start"] + 0.1, (c["start"] + c["end"]) / 2, c["end"] - 0.08):
            if 0 <= t < edit["duration"]:
                ts.add(round(t, 2))
    return sorted(ts)


def bands(fmt: str, h: int) -> list[int]:
    """Caption positions to try, nearest to the usual place first."""
    if fmt == "short":
        return [1062, 1150, 980, 1592, 900, 1250, 820, 1680]     # 1680 sits under YouTube's title: last
    return [h - 150, h - 250, h - 360, 120, 230]


def resolve(edit: dict[str, Any], comp_builder, comp: Path, size: tuple[int, int], rounds: int = 3) -> dict[str, Any]:
    """Build, measure, fix, until nothing collides (or `rounds` runs out). comp_builder(edit) rebuilds."""
    fmt = edit["format"]
    caps = edit.get("captions") or []
    hosts = [sc for sc in edit["scenes"] if sc["type"] == "host" and sc["data"].get("place") in ("side", "corner", "lower")]
    left: list[str] = []
    try:
        edit.setdefault("notes", []).extend(legibility(edit, comp_builder, comp, size))
    except Exception as error:  # noqa: BLE001 - the readability pass never stops a render
        edit.setdefault("notes", []).append(f"legibility check skipped: {str(error)[:120]}")
    try:
        edit.setdefault("notes", []).extend(keep_inside(edit, comp_builder, comp, size))
    except Exception as error:  # noqa: BLE001 - logged; the collision pass still runs
        edit.setdefault("notes", []).append(f"safe-area check skipped: {str(error)[:120]}")
    for rnd in range(rounds):
        comp_builder(edit)
        seen = probe(comp, size, _times(edit))
        hits = [(t, a, b, o) for t, boxes in seen.items() for a, b, o in collisions(boxes)]
        if not hits:
            break
        changed = False
        # 1. captions: per line, the first band that is free at all its moments
        for i, c in enumerate(caps):
            mine = [t for t in seen if c["start"] <= t < c["end"]]
            cap_hits = [(t, a, b) for t, a, b, _ in hits if t in mine and "caption" in (a["kind"], b["kind"])
                        and f"c{i}" in (_cap_id(a), _cap_id(b))]
            if not cap_hits:
                continue
            me = next(x for t, a, b in cap_hits for x in (a, b) if x["kind"] == "caption")
            current = c.get("top", int(me["y"]))
            for band in bands(fmt, size[1]):
                if band == current:
                    continue
                trial = dict(me, y=band + (me["y"] - current))
                if not any(_overlap(trial, o) > 0.03 for t in mine for o in seen[t]
                           if o["kind"] != "caption" and o["i"] != me["i"]):
                    c["top"] = band
                    changed = True
                    break
        # 2. Goli: the other spot, then out
        for sc in hosts:
            a0, a1 = sc["start"], sc["start"] + sc["duration"]
            sid_hits = [x for t, a, b, _ in hits if a0 <= t < a1 for x in (a, b)
                        if x["kind"] == "goli" and x["scene"].startswith(sc.get("_sid", "?"))]
            if not sid_hits or sc["data"].get("tried_out"):
                continue
            place = sc["data"]["place"]
            other = {"side": "lower", "lower": "side"} if fmt == "short" else {"side": "corner", "corner": "side"}
            if not sc["data"].get("tried_swap") and place in other:
                sc["data"]["place"] = other[place]
                sc["data"]["tried_swap"] = True
            elif fmt == "long":
                # 2026-11-13 (owner): nothing may overlap him: he fades out for each content scene he touches
                for t, a, b, _ in hits:
                    if not (a0 <= t < a1) or "goli" not in (a["kind"], b["kind"]):
                        continue
                    for other in edit["scenes"]:
                        if other["type"] != "host" and other["start"] <= t < other["start"] + other["duration"]:
                            gap = [other["start"], round(other["start"] + other["duration"], 3)]
                            if gap not in edit.setdefault("goli_gaps", []):
                                edit["goli_gaps"].append(gap)
                                changed = True
                continue
            else:
                sc["data"]["tried_out"] = True
                sc["duration"] = 0.0           # Goli steps out of this scene
            changed = True
        # 3. a source tag gives way
        for t, a, b, _ in hits:
            for x in (a, b):
                if x["kind"] == "chip" and x["id"].endswith("-src"):
                    for sc in edit["scenes"]:
                        if sc["type"] in ("browser_shot", "photo") and sc["start"] <= t < sc["start"] + sc["duration"]:
                            if not sc["data"].get("no_tag"):
                                sc["data"]["no_tag"] = True
                                changed = True
        # 4. the brand marks hide while they would touch content
        for t, a, b, _ in hits:
            if "brand" in (a["kind"], b["kind"]):
                edit.setdefault("brand_hide", [])
                if t not in edit["brand_hide"]:
                    edit["brand_hide"].append(t)
                    changed = True
        edit["scenes"] = [sc for sc in edit["scenes"] if sc["duration"] > 0]
        hosts = [sc for sc in hosts if sc["duration"] > 0]
        if not changed:
            left = [f"{t:.1f}s {a['kind']}#{a['id'] or a['scene']} x {b['kind']}#{b['id'] or b['scene']} ({o:.0%})"
                    for t, a, b, o in hits]
            break
    else:
        comp_builder(edit)
        seen = probe(comp, size, _times(edit))
        left = [f"{t:.1f}s {a['kind']}#{a['id'] or a['scene']} x {b['kind']}#{b['id'] or b['scene']} ({o:.0%})"
                for t, boxes in seen.items() for a, b, o in collisions(boxes)]
    edit.setdefault("notes", []).extend(f"overlap left: {x}" for x in left[:20])
    edit["layout_checked"] = {"rounds": rnd + 1, "left": len(left)}
    return edit


def _cap_id(box: dict) -> str:
    return box.get("cap", "")


def save_report(edit: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps({"layout": edit.get("layout_checked"), "notes": edit.get("notes", [])}, indent=2),
                    encoding="utf-8")
