"""Recipe scenes (owner 2026-11-17): Futurepedia's 3D style recipes (assets/styles/futurepedia/*.txt), each a
complete three.js stage kit plus a reference scene, used the way they are meant to be used: for a beat that fits the
style, a model writes a NEW scene for that beat's content from the recipe ("rebuild the animation around my
content"), the engine checks it on three stills, renders it as a clip and the clip goes into the video at that beat.

The kit (assets/recipes/stage.js) and the reference scenes are copied unchanged. Our own rules on top: the scene is
one narrated beat (no title card, callouts only, events on the spoken words), sized for the frame it fills, and
one accent colour picked for the object or brand. A scene that fails its check twice is replaced by the house 3D.
"""

from __future__ import annotations

import base64
import functools
import http.server
import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
KIT = ROOT / "assets" / "recipes"
BOOK = ROOT / "assets" / "styles" / "futurepedia"

# the recipes wired in so far; one at a time, each checked against its own reference before the next
RECIPES: dict[str, dict[str, str]] = {
    "xray": {
        "file": "x-ray.txt", "name": "X-Ray",
        "fits": "what is INSIDE a real thing and how it works (a chip, a battery, a phone, an engine, a data-centre "
                "rack, a body part): up to three inner parts, each lit and named in turn, with a simple flow (heat, "
                "air, current, data, force) shown acting on them",
    },
    "layers": {
        "file": "layer-stack.txt", "name": "Layer Stack",
        "fits": "anything BUILT IN LAYERS: a tech stack, what an AI product is made of, a product teardown, how a request "
                "travels through a system: 3 to 5 layers, top to bottom, each a glass sheet with a simple diagram, a "
                "name and a short line, and a pulse that shows the order things happen in",
    },
    # 2026-11-17 (owner): the last four, each from its own prompt; "fits" is the prompt's own "Good for" line
    "white": {
        "file": "white-model.txt", "name": "White Model",
        "fits": "how something FLOWS THROUGH A SYSTEM (energy, water, money, data, people): the system built as a white "
                "architect's model, the path laid through it as conduits, one accent travelling the path in the right "
                "order while a numbered label names each stop",
    },
    "circuit": {
        "file": "circuit-city.txt", "name": "Circuit City",
        "fits": "JOURNEYS AND PIPELINES: something travels through a system and each stage does its part (a prompt "
                "through a chip, a payment through a network, a signal through a device): every stage a landmark on a "
                "circuit board with its printed name, a pulse and the camera carrying the order",
    },
    "glass": {
        "file": "glass-and-light.txt", "name": "Glass and Light",
        "fits": "MIXTURES, RATIOS AND AMOUNTS (a recipe, a split of money or time, a blend of parts, chemistry): "
                "anything that fills, pours, layers or changes colour, told with real glassware; amounts are levels "
                "against the marks, ingredients are colours, one action per beat",
    },
    "blueprint": {
        "file": "blueprint-build.txt", "name": "Blueprint Build",
        "fits": "PLANS, SET-UPS AND HOW SOMETHING IS MADE: first the layout as a flat drawing on a blueprint sheet, "
                "then the same thing as a real object standing on its plan, with dimensions and two or three numbered "
                "pointers on the places the words talk about",
    },
}

# 2026-11-17 (owner): cost to cents. Each reference scene opens with a block marked "content (change this block for a
# new topic)": the prompt's own way to reuse it. Where that block holds the whole topic (the objects are generic), the
# storyboard fills it and no model writes code ($0 extra): Layer Stack, Circuit City, Glass and Light. X-Ray, White
# Model and Blueprint build their object in code below the block, so a new subject needs the writer (paid, chosen
# per video in Studio with a count).
FREE = ("layers", "circuit", "glass", "white", "xray", "blueprint")
WHITE_KIT = KIT / "kits" / "white-kit.js"
# 2026-11-18: White Model as a kit of pieces (assets/recipes/kits/white-kit.js): the storyboard names the stops in
# order and a few extras; code lays them out on the board so no two pieces overlap
WHITE_PIECES = {   # kind: footprint width on the board
    "house": 3.0, "tower": 2.0, "bank": 3.6, "factory": 4.6, "datacenter": 5.4, "shop": 2.6, "school": 4.0,
    "hospital": 3.8, "tree": 1.3, "pine": 1.2, "forest": 3.4, "mountain": 6.0, "hill": 4.8, "lake": 4.6,
    "river": 12.0, "cloud": 1.8, "sun": 1.4, "rain": 1.8, "road": 12.0, "bridge": 6.2, "car": 1.9, "truck": 3.0,
    "bus": 3.4, "train": 9.8, "plane": 3.4, "ship": 5.4, "pole": 1.1, "turbine": 2.2, "solar": 3.6,
    "tower_mast": 1.2, "person": 0.6, "crowd": 2.6, "battery": 3.0, "dam": 6.2,
}
WIDE = ("road", "river", "train")
# 2026-11-18: Circuit City as a kit of landmarks (assets/recipes/kits/circuit-kit.js): 2-6 stops, each a real part of
# a board, in the order the signal travels; the kit lays them out away from the camera and flies after the pulse
CIRCUIT_KIT = KIT / "kits" / "circuit-kit.js"
CIRCUIT_PARTS = ("port", "memory", "processor", "chip", "battery", "antenna", "power", "sensor")
_OLD_FOUR = ("port", "memory", "processor", "port")
# 2026-11-18: X-Ray as a kit of real objects whose inner parts are known (assets/recipes/kits/xray-kit.js)
XRAY_KIT = KIT / "kits" / "xray-kit.js"
XRAY_FLOWS = ("current", "data", "heat", "air", "force")
# 2026-11-18: Blueprint as a kit (assets/recipes/kits/blueprint-kit.js): any structure from parts, notes on named parts
BLUEPRINT_KIT = KIT / "kits" / "blueprint-kit.js"
PAID = tuple(k for k in RECIPES if k not in FREE)
DIAGRAMS = ("chat", "steps", "network", "files", "chips")      # Layer Stack's prints (its DIAGRAMS)


def _js(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _colour(value, default: str) -> str:
    v = str(value or "").strip()
    return v if len(v) == 7 and v.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in v[1:]) else default


def _caps(text, most: int) -> str:
    words = " ".join(str(text or "").split()).upper()
    return words[:most].strip()


def content_block(key: str, fill: dict[str, Any]) -> str:
    """The reference's content block, rewritten for our topic with the same names and shapes. Raises ValueError when
    the fill does not have what the block needs."""
    if key == "layers":
        layers = [x for x in (fill.get("layers") or []) if isinstance(x, dict) and str(x.get("name", "")).strip()][:5]
        if len(layers) < 3:
            raise ValueError("layers: 3 to 5 layers needed")
        title = [str(t)[:22] for t in (fill.get("title") or [])][:2]
        title = (title + ["", ""])[:2] if any(title) else ["", ""]
        rows = ",\n".join(f"    {{ name: {_js(_caps(x['name'], 14))}, note: {_js(' '.join(str(x.get('note', '')).split())[:24])}, "
                           f"diagram: {_js(x.get('diagram') if x.get('diagram') in DIAGRAMS else DIAGRAMS[i % len(DIAGRAMS)])} }}"
                           for i, x in enumerate(layers))
        return (f"  const TITLE = {_js(title)};\n  const LAYERS = [\n{rows},\n  ];\n  const N = LAYERS.length;\n")
    if key == "circuit":
        return "  const SCENE = " + json.dumps(circuit_layout(fill), ensure_ascii=False) + ";\n"
    if key == "glass":
        a, b = fill.get("first") or {}, fill.get("second") or {}
        pa, pb = int(a.get("parts") or 0), int(b.get("parts") or 0)
        if not (str(a.get("name", "")).strip() and str(b.get("name", "")).strip()) or not (1 <= pa <= 3 and 1 <= pb <= 3 and pa + pb <= 4):
            raise ValueError("glass: two liquids with 1-3 parts each, 4 parts at most")
        binder = fill.get("binder") or {}
        caps = [" ".join(str(c).split())[:34] for c in (fill.get("captions") or [])][:5]
        if len(caps) != 5:
            raise ValueError("glass: five captions needed")
        ta, tb = _colour(a.get("colour"), "#b8242f"), _colour(b.get("colour"), "#dcc82e")
        mix, spoon = _colour(fill.get("mix_colour"), "#f2cb66"), _colour(binder.get("colour"), "#e2b32c")
        return ("  const PART = 0.55;\n  const MARKS = 4;\n  const POURS = [\n"
                f"    {{ name: {_js(str(a['name'])[:20])}, tint: {_js(ta)}, parts: {pa}, pour: [1.5, 2.7], bottle: 'cruet', at: [-3.0, 0.45], stream: 0.055 }},\n"
                f"    {{ name: {_js(str(b['name'])[:20])}, tint: {_js(tb)}, parts: {pb}, pour: [3.9, 6.0], bottle: 'tall', at: [3.3, -0.35], stream: 0.08 }},\n"
                "  ];\n"
                f"  const MIX = {{ tint: {_js(mix)}, spoonful: {_js(spoon)}, spoon: 6.6, drop: 7.6, lid: 8.75, shake: [9.25, 10.25] }};\n"
                "  const CAPTIONS = [\n"
                f"    [0.15, 1.5, {_js(caps[0])}],\n    [1.6, 3.55, {_js(caps[1])}, POURS[0].tint],\n"
                f"    [3.8, 6.8, {_js(caps[2])}, POURS[1].tint],\n    [6.95, 8.6, {_js(caps[3])}, MIX.spoonful],\n"
                f"    [9.3, 99, {_js(caps[4])}, MIX.tint],\n  ];\n  const DURATION = 12;\n")
    if key == "white":
        return "  const SCENE = " + json.dumps(white_layout(fill), ensure_ascii=False) + ";\n"
    if key == "xray":
        return "  const SCENE = " + json.dumps(xray_layout(fill), ensure_ascii=False) + ";\n"
    if key == "blueprint":
        return "  const SCENE = " + json.dumps(blueprint_layout(fill), ensure_ascii=False) + ";\n"
    raise ValueError(f"{key} has no free mode")


# 2026-11-18 (owner: "every script has different objects"): X-Ray and Blueprint draw ANY object the storyboard
# writes, in the engine's own 3D part format (vector/figures/devices.py): "name: box|cyl|sphere|cone x y z w d h
# [rx90] [ry0] [rz45] [gold]", z up, z = the part's base. Parts with the same name are one part (4 motors).
PART_SHAPES = ("box", "cyl", "sphere", "cone")
PART_MAX = 40


def object_parts(lines: Any, span: tuple[float, float, float]) -> list[dict[str, Any]]:
    """Named parts in three.js terms ({name, shape, c: centre, s: size [x, y up, z], r: radians, gold}), scaled as
    one so the object fits span (x, height, z), standing on y = 0 and centred. Raises ValueError when there are no
    readable parts."""
    import math
    import re as _re

    parts = []
    for line in (lines if isinstance(lines, list) else []):
        m = _re.match(r"\s*([^:]{1,24}):\s*(.+)$", str(line))
        if not m:
            continue
        name = " ".join(m.group(1).lower().split())
        words = m.group(2).replace(",", " ").split()
        if not words or words[0].lower() not in PART_SHAPES:
            continue
        nums, rot, gold = [], [0.0, 0.0, 0.0], False
        for w in words[1:]:
            low = w.lower()
            if low == "gold":
                gold = True
            elif low[:2] in ("rx", "ry", "rz"):
                try:
                    rot["xyz".index(low[1])] = math.radians(float(low[2:].lstrip("=")))
                except ValueError:
                    pass
            else:
                try:
                    nums.append(float(w))
                except ValueError:
                    pass
        if len(nums) < 6 or min(nums[3:6]) <= 0 or max(abs(v) for v in nums[:6]) > 100:
            continue
        x, y, z, w, d, h = nums[:6]
        # engine (x, y depth, z up, base) -> three (x, y up, z), centre; rx stays x, ry turns about z, rz about y
        parts.append({"name": name, "shape": words[0].lower(), "c": [x, z + h / 2, y], "s": [w, h, d],
                      "r": [rot[0], rot[2], rot[1]], "gold": gold})
    if not parts:
        raise ValueError("no readable parts: write each as 'name: box|cyl|sphere|cone x y z w d h'")
    parts = parts[:PART_MAX]
    lo = [min(p["c"][k] - p["s"][k] / 2 for p in parts) for k in range(3)]
    hi = [max(p["c"][k] + p["s"][k] / 2 for p in parts) for k in range(3)]
    k = min(span[i] / max(hi[i] - lo[i], 1e-6) for i in range(3))
    mid = [(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2]
    for p in parts:
        p["c"] = [round((p["c"][i] - mid[i]) * k, 4) for i in range(3)]
        p["s"] = [round(v * k, 4) for v in p["s"]]
        p["r"] = [round(v, 4) for v in p["r"]]
    return parts


def blueprint_layout(fill: dict[str, Any]) -> dict[str, Any]:
    """ANY structure or object, written by the storyboard as named parts ("build", the engine's part format), a
    two-line title and 1-3 notes tied to its named parts; real sizes ("dims": width, depth, height) are printed when
    given. Raises ValueError when there are no readable parts or no note names one of them."""
    build = object_parts(fill.get("build"), (1.2, 1.35, 1.2))
    names = {p["name"] for p in build}
    notes, seen = [], set()
    for n in fill.get("notes") or []:
        at = " ".join(str(n.get("at", "")).lower().split()) if isinstance(n, dict) else ""
        lines = [_caps(x, 14) for x in (n.get("lines") or [])[:2] if str(x).strip()] if isinstance(n, dict) else []
        if lines and at in names and at not in seen:
            seen.add(at)
            notes.append({"at": at, "lines": lines})
    if not notes:
        raise ValueError(f"blueprint: 1 to 3 notes on the parts needed: {', '.join(sorted(names))}")
    title = [_caps(x, 14) for x in (fill.get("title") or [])[:2] if str(x).strip()] or ["GENERAL", "ARRANGEMENT"]
    dims = [" ".join(str(x).upper().split())[:8] for x in (fill.get("dims") or [])]
    out = {"build": build, "title": title, "notes": notes[:3]}
    if len(dims) == 3 and all(dims):
        out["dims"] = dims
    return out


def xray_layout(fill: dict[str, Any]) -> dict[str, Any]:
    """ANY object, written by the storyboard as named parts ("build", the engine's part format, lying on the scanner
    bed), and 1-3 of those parts to light in the order the flow reaches them. Raises ValueError when the object has
    no readable parts or none of the named ones is in it."""
    build = object_parts(fill.get("build"), (8.0, 3.2, 6.0))
    names = {p["name"] for p in build}
    parts, seen = [], set()
    for p in fill.get("parts") or []:
        key = " ".join(str(p.get("part", "")).lower().split()) if isinstance(p, dict) else ""
        if key in names and key not in seen and str(p.get("name", "")).strip():
            seen.add(key)
            parts.append({"part": key, "name": _caps(p["name"], 14), "note": " ".join(str(p.get("note", "")).split())[:28]})
    if not parts:
        raise ValueError(f"xray: 1 to 3 of the object's own parts needed: {', '.join(sorted(names))}")
    flow = fill.get("flow") if fill.get("flow") in XRAY_FLOWS else "current"
    return {"object": _caps(fill.get("object") or "object", 20), "build": build, "parts": parts[:3], "flow": flow,
            "accent": _colour(fill.get("accent"), "#ff9a22")}


def circuit_layout(fill: dict[str, Any]) -> dict[str, Any]:
    """Stops in the order the signal travels, each a real part of a board (a plain name list keeps the reference's
    own port, memory, processor, port). Raises ValueError when there is nothing to show."""
    raw = [x for x in (fill.get("stops") or []) if x]
    if raw and all(isinstance(x, str) for x in raw) and len(raw) == 4:
        raw = [{"kind": k, "name": n} for k, n in zip(_OLD_FOUR, raw)]
    stops = [x if x.get("kind") in CIRCUIT_PARTS else {**x, "kind": "chip"} for x in raw if isinstance(x, dict) and str(x.get("name", "")).strip()][:6]
    if len(stops) < 2:
        raise ValueError("circuit: 2 to 6 stops of known parts needed")
    refs, n = [], {"J": 0, "U": 0, "BT": 0, "L": 0, "S": 0, "ANT": 0}
    for st in stops:
        pre = {"port": "J", "battery": "BT", "power": "L", "sensor": "S", "antenna": "ANT"}.get(st["kind"], "U")
        n[pre] += 1
        refs.append(f"{pre}{n[pre]}")
    return {"stops": [{"kind": st["kind"], "name": _caps(st.get("name"), 12), "ref": r} for st, r in zip(stops, refs)]}


def white_layout(fill: dict[str, Any]) -> dict[str, Any]:
    """Stops in story order left to right on the board (a gentle zigzag so the path reads), extras in the gaps in
    front and behind, wide pieces (road, river, track) across the front. Raises ValueError when there is nothing to
    show."""
    # a stop or extra the 35 pieces do not cover is written as parts ("build") and built in white card (kind custom)
    def custom(item):
        try:
            return {"kind": "custom", "build": object_parts(item.get("build"), (2.6, 3.2, 2.0))} if isinstance(item, dict) and item.get("build") else None
        except ValueError:
            return None
    stops = []
    for s in fill.get("stops") or []:
        if isinstance(s, dict) and s.get("kind") in WHITE_PIECES and s.get("kind") not in WIDE:
            stops.append(s)
        elif custom(s):
            stops.append({**s, **custom(s)})
    stops = stops[:6]
    if len(stops) < 2:
        raise ValueError("white: 2 to 6 stops of known kinds needed")
    # people as a stop of the story stand out: a figure or a crowd at 2.4x scale (a person among buildings would
    # otherwise be a speck, owner 2026-11-18 "people, i didnt see it")
    hero = {"person": 2.4, "crowd": 2.2}
    widths = [(2.6 if s["kind"] == "custom" else WHITE_PIECES[s["kind"]]) * hero.get(s["kind"], 1) for s in stops]
    gap = 1.6                                           # the pieces sit together: the camera frames what is there
    span = sum(widths) + gap * (len(stops) - 1)
    scale = min(1.0, 26 / span)
    x = -span * scale / 2
    pieces, path, steps, used = [], [], [], []
    for i, (st, w) in enumerate(zip(stops, widths)):
        cx = x + w * scale / 2
        z = -1.6 if i % 2 == 0 else -3.4
        pid = f"s{i}"
        pieces.append({"id": pid, "kind": st["kind"], "at": [round(cx, 2), z], "scale": round(scale * hero.get(st["kind"], 1), 2),
                       **({"build": st["build"]} if st["kind"] == "custom" else {})})
        used.append((cx - w * scale / 2, cx + w * scale / 2))
        path.append(pid)
        steps.append({"name": " ".join(str(st.get("name", "")).upper().split())[:16],
                      "note": " ".join(str(st.get("note", "")).split())[:26]})
        x += (w + gap) * scale
    extras = [e if isinstance(e, str) else custom(e) for e in (fill.get("extras") or []) if (isinstance(e, str) and e in WHITE_PIECES) or custom(e)][:6]
    front = [e for e in extras if isinstance(e, str) and e in WIDE][:1]
    if front:
        pieces.append({"kind": front[0], "at": [0, 3.2]})
    half = span * scale / 2
    # extras stand behind the row and at its ends, never in front of a stop (the camera looks from the front)
    slots = [(-half - 1.4, -2.4), (half + 1.4, -2.4), (-half * 0.5, -6.0), (half * 0.5, -6.0), (0, -6.4), (-half - 1.2, -5.8), (half + 1.2, -5.8)]
    for e, (ex, ez) in zip([e for e in extras if not (isinstance(e, str) and e in WIDE)], slots):
        if isinstance(e, dict):
            pieces.append({**e, "at": [ex, ez], "scale": round(min(1.0, scale + 0.15), 2)})
            continue
        on_road = front and front[0] == "road" and e in ("car", "truck", "bus")
        pieces.append({"kind": e, "at": [ex, 3.2 if on_road else ez], "scale": round(min(1.0, scale + 0.15), 2),
                       "turn": 180 if on_road and ex > 0 else 0})
    accent = str(fill.get("accent") or "#ff6a00")
    return {"accent": accent if len(accent) == 7 and accent.startswith("#") else "#ff6a00", "title": ["", ""],
            "pieces": pieces, "path": path, "steps": steps}


def reference_code(key: str) -> str:
    text = (BOOK / RECIPES[key]["file"]).read_text(encoding="utf-8")
    ref = _section(text, "REFERENCE STYLE SOURCE", None)
    a = ref.find("```js") + 5
    return ref[a:ref.rfind("```")].strip() + "\n"


def fill_code(key: str, fill: dict[str, Any], duration: float) -> str:
    """The reference scene with its content block replaced, played over `duration` seconds (its own timing,
    stretched evenly: the picture keeps its order and rhythm). White Model is its kit of pieces, timed to the beat."""
    if key in ("white", "circuit", "xray", "blueprint"):
        scene = {"white": white_layout, "circuit": circuit_layout, "xray": xray_layout, "blueprint": blueprint_layout}[key](fill)
        scene["duration"] = round(float(duration), 3)
        kit = {"white": WHITE_KIT, "circuit": CIRCUIT_KIT, "xray": XRAY_KIT, "blueprint": BLUEPRINT_KIT}[key]
        return kit.read_text(encoding="utf-8").replace("__SCENE__", json.dumps(scene, ensure_ascii=False))
    code = reference_code(key)
    a = code.find("\n", code.find("// ----------------------------------------------------------------")) + 1
    b = code.find("  // ----------------------------------------------------------------", a)
    if a <= 0 or b < 0:
        raise ValueError(f"{key}: content block not found")
    code = code[:a] + content_block(key, fill) + "\n" + code[b:]
    return code + f"""
// GOLIDE (2026-11-17): the scene played over the beat's length, its own timing stretched evenly
(function () {{
  const st = STYLES[STYLES.length - 1], D0 = st.duration, D = {float(duration):.3f}, k = D0 / D, build = st.build;
  st.duration = D;
  st.build = function (S) {{
    const wrap = (api) => Object.assign({{}}, api, {{
      update: (t) => api.update(t * k),
      overlay: api.overlay ? (ctx, t, W, H) => api.overlay(ctx, t * k, W, H) : undefined,
    }});
    const out = build.call(this, S);
    if ({'true' if key == 'layers' else 'false'}) {{
      // 2026-11-18: in the Short's square frame the lens widens so labels beside the stack stay inside
      const cam = S.camera, G = Math.pow(Math.max(1, 1.78 / cam.aspect), 0.75);
      let base = cam.fov, last = null;
      const widen = (api) => Object.assign({{}}, api, {{ update: (t) => {{
        api.update(t);
        if (cam.fov !== last) base = cam.fov;
        cam.fov = 2 * Math.atan(Math.tan(base * Math.PI / 360) * G) * 360 / Math.PI;
        cam.updateProjectionMatrix(); last = cam.fov;
      }} }});
      return out && typeof out.then === 'function' ? out.then((a) => widen(wrap(a))) : widen(wrap(out));
    }}
    return out && typeof out.then === 'function' ? out.then(wrap) : wrap(out);
  }};
}})();
"""


def make_free(key: str, fill: dict[str, Any], duration: float, fmt: str, folder: Path, samples: int = 5,
              workers: int = 3) -> dict[str, Any] | None:
    """A free scene: no model call. Filled, checked (errors, empty frames, motion, collisions) and rendered; one
    that fails its check is not retried (that would cost a model call): the caller shows the free stand-in."""
    size = FRAME[fmt]
    try:
        code = fill_code(key, fill, duration)
    except ValueError as error:
        print(json.dumps({"status": "recipe_free_unfilled", "recipe": key, "why": str(error)}))
        return None
    stills, problems = check(code, folder / "free", size, duration)
    print(json.dumps({"status": "recipe_free_check", "recipe": key, "ok": not problems, "problems": problems[:300]}))
    if problems:
        return None
    video = render_clip(code, folder / "free", size, duration, folder / f"{key}.mp4", samples=samples, workers=workers)
    (folder / "style.js").write_text(code, encoding="utf-8")
    return {"video": str(video), "accent": "", "events": [], "stills": [str(s) for s in stills], "size": list(size),
            "free": True}


CODE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "code": {"type": "string"},
        "accent": {"type": "string"},
        "events": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
            "t": {"type": "number"}, "what": {"type": "string", "enum": ["start", "scan", "part", "flow", "result"]},
            "label": {"type": "string"}}, "required": ["t", "what", "label"]}},
    },
    "required": ["code", "accent", "events"],
}

FRAME = {"long": (1600, 900), "short": (1000, 1000)}


def _section(text: str, start: str, end: str | None) -> str:
    a = text.find(start)
    if a < 0:
        return ""
    b = text.find(end, a + len(start)) if end else -1
    return text[a:b if b > 0 else len(text)].strip()


def recipe_text(key: str) -> str:
    """The parts of the recipe the writer follows, unchanged: its style rules, the style card, the stage kit and
    the reference scene. Left out: its storyboard and player steps (the engine does those) and its sound kit (the
    video has its own sound)."""
    text = (BOOK / RECIPES[key]["file"]).read_text(encoding="utf-8")
    rules = _section(text, "HOW TO STAY IN THE STYLE", "SOUND (")
    card_and_kit = _section(text, "STYLE CARD", "SOUND KIT (")
    reference = _section(text, "REFERENCE STYLE SOURCE", None)
    parts = [rules, card_and_kit]
    # Blueprint Build's lettering library (lib/strokefont.js, loaded by the player unchanged): its API, as written
    lib = _section(text, "STROKEFONT (lib/strokefont.js)", "*/")
    if lib:
        parts.append(lib + "\n */\n(the library itself is loaded for you as a global STROKEFONT, unchanged)")
    return "\n\n".join(parts + [reference])


def instructions(key: str) -> str:
    r = RECIPES[key]
    return f"""You write ONE scene of a GOLIDE video in the "{r['name']}" style, from the recipe below: its style rules,
style card, the stage kit it runs on and a complete reference scene. Follow the recipe's rules exactly: keep the
reference's materials, lighting, camera language, grade and the way things move; change the story, the objects
and the words to the content you are given; never reuse the reference's object (the reference shows the look, not
the story).

WHAT YOU WRITE
- One JavaScript block built exactly like the reference: `{{ content constants...; registerStyle({{ id, name, duration,
  fonts, render, build(S) {{ ... return {{ update(t), overlay(ctx, t, W, H) }} }} }}); }}`. A classic script: THREE, K and
  registerStyle are globals; no import, no fetch, no Math.random, Date or timers (use K.rng(seed)); build everything
  in code (no files, models, images or textures).
- duration = the scene length you are given, exactly. The frame is the size you are given: read S.W and S.H, scale
  every overlay size by H / 1080 like the reference, and frame the camera for that shape (it may be square).
- render: keep the reference's tone, exposure, bloom, vignette, grain, fov and background. samples is set by the
  engine.
- update(t) sets the WHOLE scene for time t; nothing builds up between calls (the kit renders each frame many times).

THIS SCENE IS ONE BEAT OF A NARRATED VIDEO
- The host's voice is already saying the words you are given and captions show them under the picture. So: NO
  title, overline or headline card. Labels are callouts only (a NAME of 1-3 words and a note of 2-5 words, both from
  what is said), at most 3, each appearing as its part lights up.
- Land every event on its spoken word, using the word times you are given (seconds from the start of this scene):
  the effect starting, each part lighting up, the flow arriving, the result.
- The first frame already shows the object (never an empty frame); the last half second holds the result.
- Everything that matters stays inside the frame with a 6% margin through the whole camera move; labels never cover
  each other or the part they name; text large enough to read on a phone.
- Colour: keep the style's palette rule. Set ACCENT to fit the object or brand in the story (e.g. Nvidia green for an
  Nvidia chip, a warning orange for a battery fire); still ONE accent. Before the effect, draw the object in its real
  materials and colours.
- Draw the subject accurately (real proportions, the parts the words name); simple forms beautifully lit beat
  complicated models that look wrong. Only facts from the words and brief you are given.
- No collision: words never touch each other or leave the frame; printed labels on the same surface never touch.
  The engine measures every word you draw (overlay text, K.textPlane, text painted on a texture). Lettering made of
  lines (STROKEFONT, e.g. the reference's letter()) cannot be seen by the engine, so register each block once it is
  built: `K.words(text, records, object)` with the records letter() returned and the Object3D they are drawn in
  (the mesh ink() made from them, or null when they are in world space).
- No sound() is needed: the video has its own sound. Instead return `events`: every moment something lands (t in
  seconds, what, label).

Return JSON: code (the block), accent (#rrggbb), events.

========================= THE RECIPE =========================
{recipe_text(key)}"""


def request(key: str, brief: str, words: list[dict[str, Any]], duration: float, size: tuple[int, int],
            problems: str = "") -> str:
    said = " ".join(f"{w['text']}@{w['t']:.2f}" for w in words)
    out = (f"STYLE: {RECIPES[key]['name']}\nSCENE LENGTH: {duration:.2f} s\nFRAME: {size[0]}x{size[1]} px\n"
           f"WHAT TO SHOW: {brief}\nWHAT THE VOICE SAYS (word@seconds from the scene start): {said}\n")
    if problems:
        out += f"\nYOUR LAST VERSION FAILED ITS CHECK. Fix this and send the whole block again:\n{problems}\n"
    return out


# ---------------------------------------------------------------- running a scene in headless Chromium
CHROMIUM_ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]


def stage_folder(code: str, folder: Path) -> Path:
    """A folder the player can run from: the player, the kit, three.js 0.187.0, the fonts and the written scene."""
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("player.html", "stage.js", "strokefont.js"):
        shutil.copy(KIT / name, folder / name)
    for sub in ("three", "fonts"):
        shutil.copytree(KIT / sub, folder / sub, dirs_exist_ok=True)
    (folder / "style.js").write_text(code, encoding="utf-8")
    return folder


class _Quiet(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript"}

    def log_message(self, *args):  # noqa: D401
        pass


def _serve(folder: Path):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(folder)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def frames(folder: Path, size: tuple[int, int], samples: int, times: list[float], out: Path,
           timeout_ms: int = 180000, boxes: list | None = None, printed: list | None = None) -> list[str]:
    """Render the scene at the given times into out/NNNNN.jpg (numbered by position in `times`). Returns the page's
    errors (empty when it ran clean). `boxes`, when given, gets the words written on screen at each time with their
    boxes (from the player's record of the overlay)."""
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    server = _serve(folder)
    errors: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=CHROMIUM_ARGS)
            page = browser.new_page(viewport={"width": 640, "height": 360})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{server.server_address[1]}/player.html?w={size[0]}&h={size[1]}&n={samples}")
            page.wait_for_function("window.ready === true", timeout=timeout_ms)
            errors += page.evaluate("window.errors")
            if printed is not None:
                printed += page.evaluate("window.printed || []")
            if not errors:
                for i, t in enumerate(times):
                    data = page.evaluate("(t) => { window.seek(t); return document.getElementById('c').toDataURL("
                                         "'image/jpeg', 0.94); }", t)
                    (out / f"{i:05d}.jpg").write_bytes(base64.b64decode(data.split(",", 1)[1]))
                    if boxes is not None:
                        boxes.append(page.evaluate("window.boxes"))
                errors += page.evaluate("window.errors")
                if printed is not None and page.evaluate("window.usesLettering()"):
                    printed.append({"unregistered": True})
            browser.close()
    finally:
        server.shutdown()
    return errors


def check(code: str, folder: Path, size: tuple[int, int], duration: float) -> tuple[list[Path], str]:
    """Three stills (start, middle, end) at a low sample count. Returns the stills and the problems found, if any:
    page errors, an empty or black frame, a frame with nothing moving between start and end."""
    from PIL import Image, ImageChops, ImageStat

    stage_folder(code, folder)
    times = [min(0.4, duration * 0.1), duration * 0.5, max(0.0, duration - 0.15), duration * 0.75]
    words: list = []
    printed: list = []
    errors = frames(folder, size, 2, times, folder / "check", boxes=words, printed=printed)
    if errors:
        return [], "The page threw errors:\n" + "\n".join(e[:600] for e in errors[:5])
    stills = [folder / "check" / f"{i:05d}.jpg" for i in range(3)]
    problems = []
    images = [Image.open(s).convert("L") for s in stills]
    for name, im in zip(("first", "middle", "last"), images):
        st = ImageStat.Stat(im.resize((160, 90)))
        if st.stddev[0] < 7 or st.mean[0] < 4:
            problems.append(f"the {name} frame is empty (nearly one flat colour): the object or the camera is wrong")
    if ImageStat.Stat(ImageChops.difference(images[0], images[2]).resize((160, 90))).mean[0] < 1.0:
        problems.append("nothing changes between the first and last frame: the scene does not move")
    for i, (t, found) in enumerate(zip(times, words)):
        problems += label_problems(found, size, t, last=(i == 2))
    problems += printed_problems(printed)
    return stills[:3], "\n".join(dict.fromkeys(problems))


def label_problems(found: list[dict], size: tuple[int, int], t: float, pad: float = 6, margin: float = 0.025,
                   last: bool = True) -> list[str]:
    """Words on screen that touch each other (with a small gap) or leave the frame. Words that live in the 3D world
    (`world`) may pass the frame edge while the camera travels, as the recipes' cameras do; they are held to the
    frame on the last frame, which holds. Words wholly off screen are not on screen."""
    out = []
    w, h = size
    found = [b for b in found if b["x1"] > 0 and b["y1"] > 0 and b["x0"] < w and b["y0"] < h]
    for b in found:
        if b.get("world") and not last:
            continue
        if b["x0"] < w * margin or b["y0"] < h * margin or b["x1"] > w * (1 - margin) or b["y1"] > h * (1 - margin):
            out.append(f'at {t:.1f} s the label "{b["text"]}" leaves the frame: keep labels inside it')
    for i, a in enumerate(found):
        for b in found[i + 1:]:
            if a["text"] == b["text"]:
                continue
            gap = 0 if a.get("world") or b.get("world") else pad    # 3D boxes are already the letters' outer box
            if min(a["x1"], b["x1"]) + gap > max(a["x0"], b["x0"]) and min(a["y1"], b["y1"]) + gap > max(a["y0"], b["y0"]):
                out.append(f'at {t:.1f} s the labels "{a["text"]}" and "{b["text"]}" overlap: move one so they never touch')
    return out


def printed_problems(found: list[dict], pad: float = 2) -> list[str]:
    """Words painted on the same texture (a board's silkscreen, the marks on a glass) that touch each other."""
    out = []
    if any(b.get("unregistered") for b in found):
        out.append("lettering made with STROKEFONT is not registered: call K.words(text, records, object) for every block")
    found = [b for b in found if not b.get("unregistered")]
    for i, a in enumerate(found):
        for b in found[i + 1:]:
            if a["sheet"] != b["sheet"] or a["text"] == b["text"]:
                continue
            if min(a["x1"], b["x1"]) + pad > max(a["x0"], b["x0"]) and min(a["y1"], b["y1"]) + pad > max(a["y0"], b["y0"]):
                out.append(f'the printed labels "{a["text"]}" and "{b["text"]}" touch on the same surface: move one apart')
    return out


def render_clip(code: str, folder: Path, size: tuple[int, int], duration: float, video: Path, samples: int = 5,
                fps: int = 30, workers: int = 3) -> Path:
    """The whole scene as an MP4, the frames split across `workers` browsers running side by side."""
    stage_folder(code, folder)
    n = max(1, int(round(duration * fps)))
    chunks = [(k * n // workers, (k + 1) * n // workers) for k in range(workers)]
    import os
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT / "src"), os.environ.get("PYTHONPATH", "")]))
    procs = [subprocess.Popen([sys.executable, "-m", "golide_engine.edit.recipes", "frames", str(folder), str(size[0]),
                               str(size[1]), str(samples), str(fps), str(a), str(b)], env=env)
             for a, b in chunks if b > a]
    if any(p.wait() != 0 for p in procs):
        raise RuntimeError("a recipe frame worker failed")
    video.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(folder / "frames" / "%05d.jpg"),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-an", str(video)],
                   check=True)
    return video


def _worker(argv: list[str]) -> None:
    folder, w, h, samples, fps, a, b = argv
    a, b, fps = int(a), int(b), int(fps)
    tmp = Path(folder) / f"part-{a}"
    errors = frames(Path(folder), (int(w), int(h)), int(samples), [i / fps for i in range(a, b)], tmp)
    if errors:
        print(json.dumps({"status": "recipe_frames_failed", "errors": errors[:3]}))
        raise SystemExit(1)
    final = Path(folder) / "frames"
    final.mkdir(exist_ok=True)
    for i in range(a, b):
        (tmp / f"{i - a:05d}.jpg").replace(final / f"{i:05d}.jpg")


def make(text, key: str, brief: str, words: list[dict[str, Any]], duration: float, fmt: str, folder: Path,
         samples: int = 5, workers: int = 3, record=None) -> dict[str, Any] | None:
    """Write, check (one retry with the problems fed back) and render one recipe scene. Returns {video, accent,
    events, stills} or None when it failed twice (the caller shows the house 3D instead)."""
    size = FRAME[fmt]
    problems = ""
    for attempt in (1, 2):
        output = text.generate_json(instructions(key), request(key, brief, words, duration, size, problems),
                                    CODE_SCHEMA, max_output_tokens=24000)
        if record:
            record(f"recipe-{key}-{attempt}", output)
        value = output.value
        stills, problems = check(value["code"], folder / f"try{attempt}", size, duration)
        print(json.dumps({"status": "recipe_check", "recipe": key, "attempt": attempt, "ok": not problems,
                          "problems": problems[:300]}))
        if not problems:
            video = render_clip(value["code"], folder / f"try{attempt}", size, duration, folder / f"{key}.mp4",
                                samples=samples, workers=workers)
            (folder / "style.js").write_text(value["code"], encoding="utf-8")
            return {"video": str(video), "accent": value.get("accent", ""), "events": value.get("events") or [],
                    "stills": [str(s) for s in stills], "size": list(size)}
    return None


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "frames":
    _worker(sys.argv[2:])
