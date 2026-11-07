"""Stage: turn research about any subject into a checked blueprint of a 3D object."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from .catalog import WORLD3D, load, menu

MAX_PARTS = 24
VECTOR = {"type": "array", "items": {"type": "number"}}
OUTLINE = {"type": "array", "items": VECTOR}
PROFILE = {"type": "object", "properties": {"top": OUTLINE, "bottom": OUTLINE, "width": OUTLINE},
           "required": ["top", "bottom", "width"], "additionalProperties": False}
BLUEPRINT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
        "simplified": {"type": "array", "items": {"type": "string"}},
        "parts": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "label": {"type": "string"},
            "builder": {"type": "string"}, "material": {"type": "string"},
            "params": {"type": "array", "items": {"type": "object", "properties": {
                "name": {"type": "string"}, "value": {"type": "number"},
            }, "required": ["name", "value"], "additionalProperties": False}},
            "profile": PROFILE,
            "at": VECTOR, "turn": VECTOR, "explode": VECTOR, "anchor": VECTOR,
        }, "required": ["id", "label", "builder", "material", "params", "profile", "at", "turn", "explode", "anchor"],
            "additionalProperties": False}},
    },
    "required": ["name", "sources", "simplified", "parts"], "additionalProperties": False,
}


def slug(subject: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")[:60] or "object"


def instructions(catalog: dict | None = None) -> str:
    return f"""You turn research about a real thing into a simple, accurate 3D blueprint for an explainer video.

Use the real structure: real parts, real order, real proportions, real sizes in metres. Search for
published facts when the research does not give them. List the URLs you relied on in sources. Anything
you had to estimate or leave out goes in simplified, in plain words. Never present a guess as fact.
For weapons, give only the general layout and how it works, never manufacturing detail.

Use {MAX_PARTS} parts or fewer: the parts a viewer needs to understand how it works, not every screw.
Each part has a short lowercase id, a viewer-facing label, one builder and one material.
Parts are positioned with at (x, y, z), z up. Keep the main axis along +X so stacked parts add up.
turn is the part's rotation in degrees about x, y, z, applied at its at point; [0,0,0] for most parts.
A wing or fin is a shell built along its span then turned (span across: [0,0,90]; fin upright: [90,0,0]).
Something tall like a bottle or tower is built lying along +X and turned upright with [0,-90,0].
turn spins a part about its own start point, so at is where that start ends up: a cap on an upright
0.3 m bottle has at [0,0,0.3]. Explode upward or sideways; never through the ground.
explode is the offset that moves the part away so the inside shows; use [0,0,0] for parts that stay.
anchor is the point on the part, relative to its own at, where a label line lands.

SHAPE MUST BE RECOGNISABLE. A viewer has to know what the thing is at a glance. Never build a curved
object out of boxes. Its main body and any curved part use shell with profile, read from the real thing:
- top: the side-view top line as [x, z] points from front (x=0) to back (x=length), z up from the base.
  Follow the real silhouette: bumper, bonnet, windscreen, roof, tail; or nose cone, body, fins.
- bottom: the side-view bottom line the same way (ground clearance, belly, keel).
- width: the plan-view full width as [x, w] points along the length (narrow nose, wide middle).
Use 6-14 points per line, from published dimensions and photos. Every other builder gets empty lists.
For a round body (missile, bottle, fuselage) the top and bottom lines mirror each other about the centre.
A glass canopy or cabin is its own shell. Wheels use wheel. Colours follow the real product.

{menu(catalog or load())}"""


def params_to_dict(part: dict[str, Any]) -> dict[str, Any]:
    raw = part.get("params", {})
    return {p["name"]: p["value"] for p in raw} if isinstance(raw, list) else dict(raw)


def problems(blueprint: dict[str, Any], catalog: dict | None = None) -> list[str]:
    """Everything that would stop a build, in words the model can fix on a retry."""
    catalog = catalog or load()
    found: list[str] = []
    parts = blueprint.get("parts") or []
    if not parts:
        found.append("the blueprint has no parts")
    if len(parts) > MAX_PARTS:
        found.append(f"{len(parts)} parts is over the limit of {MAX_PARTS}")
    if not blueprint.get("sources"):
        found.append("sources is empty")
    seen: set[str] = set()
    for part in parts:
        pid = str(part.get("id", ""))
        if not pid or pid in seen:
            found.append(f"part id '{pid}' is empty or repeated")
        seen.add(pid)
        for key in ("at", "turn", "explode", "anchor"):
            if key in part and len(part[key]) != 3:
                found.append(f"{pid}: {key} needs exactly 3 numbers")
        builder = catalog["builders"].get(part.get("builder"))
        if builder is None:
            found.append(f"{pid}: unknown builder '{part.get('builder')}'")
            continue
        if part.get("material") not in catalog["materials"]:
            found.append(f"{pid}: unknown material '{part.get('material')}'")
        values = params_to_dict(part)
        for name in builder["required"]:
            if name not in values:
                found.append(f"{pid}: {part['builder']} needs {name}")
        allowed = set(builder["required"]) | set(builder["optional"])
        for name, value in values.items():
            if name not in allowed:
                found.append(f"{pid}: {part['builder']} has no setting '{name}'")
            elif not isinstance(value, (int, float)) or not math.isfinite(value):
                found.append(f"{pid}: {name} must be a number")
            elif name in builder["required"] and value <= 0:
                found.append(f"{pid}: {name} must be above zero")
        if part["builder"] == "shell":
            prof = part.get("profile") or {}
            length = values.get("length", 0)
            for line in ("top", "width"):
                pts = prof.get(line) or []
                if len(pts) < 2:
                    found.append(f"{pid}: shell needs at least 2 {line} points")
                elif any(len(pt) != 2 for pt in pts):
                    found.append(f"{pid}: every {line} point is [x, value]")
                elif any(not (-0.01 <= pt[0] <= length * 1.01) for pt in pts):
                    found.append(f"{pid}: {line} x values must lie between 0 and length")
    return found


def clean(blueprint: dict[str, Any]) -> dict[str, Any]:
    out = dict(blueprint)
    out["parts"] = []
    for p in blueprint["parts"]:
        part = {**p, "params": params_to_dict(p)}
        if not any((p.get("profile") or {}).values()):
            part.pop("profile", None)
        out["parts"].append(part)
    return out


def library_path(subject: str, folder: Path | None = None) -> Path:
    return (folder or WORLD3D / "blueprints") / f"{slug(subject)}.json"


def obtain(subject: str, research: str, text: Any, folder: Path, attempts: int = 3) -> tuple[Path, list[Any]]:
    """Reuse a saved blueprint, or generate one. A subject is only ever paid for once.
    Returns its path and the model outputs used, so the caller can record their cost."""
    for known in (library_path(subject, folder), library_path(subject)):
        if known.exists():
            return known, []
    catalog = load()
    outputs: list[Any] = []
    note = ""
    for _ in range(attempts):
        output = text.generate_json(instructions(catalog), f"SUBJECT={subject}\n{note}RESEARCH\n{research}",
                                    BLUEPRINT_SCHEMA, web_search=True, max_output_tokens=9000)
        outputs.append(output)
        found = problems(output.value, catalog)
        if not found:
            path = library_path(subject, folder)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(clean(output.value), indent=2) + "\n", encoding="utf-8")
            return path, outputs
        note = "YOUR LAST BLUEPRINT FAILED. Fix these: " + "; ".join(found[:12]) + "\n"
    raise ValueError(f"No usable blueprint for {subject}: {'; '.join(found[:6])}")
