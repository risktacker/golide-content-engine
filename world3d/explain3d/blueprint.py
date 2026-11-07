"""Stage: turn research about any real thing into a real CAD model of it.

Luna writes build123d code from the object's published architecture; cad.py builds it. Build errors
go back to Luna to fix, so the model is never a guess made of boxes. A built object is saved and
never paid for twice.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import cad
from .catalog import WORLD3D, load

MAX_PARTS = 16
VECTOR = {"type": "array", "items": {"type": "number"}}
BLUEPRINT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
        "simplified": {"type": "array", "items": {"type": "string"}},
        "code": {"type": "string"},
        "parts": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "label": {"type": "string"},
            "material": {"type": "string"}, "explode": VECTOR,
        }, "required": ["id", "label", "material", "explode"], "additionalProperties": False}},
    },
    "required": ["name", "sources", "simplified", "code", "parts"], "additionalProperties": False,
}


def slug(subject: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")[:60] or "object"


def instructions(catalog: dict | None = None) -> str:
    catalog = catalog or load()
    return f"""You are a CAD engineer. You model a real thing so a viewer recognises it at a glance and sees how
it really works, for an explainer video. You write Python for build123d (the open-source CAD library).

Research first: search for its published dimensions, drawings, patents, teardowns and photos. Model the
real architecture: the real parts, their real shapes, sizes in metres, order and how they connect. List
the URLs you relied on in sources. Anything estimated or left out goes in simplified, in plain words.
For weapons, only the general layout and how it works, never manufacturing detail.

CODE RULES
- Import only build123d and math. Define build() that returns a dict {{part_id: shape}}.
- Units are metres. Z is up, the object stands on z=0, its front faces -Y.
- Use real CAD: sketches, extrude, revolve, loft, sweep, fillet, chamfer, mirror, boolean cuts, arrays.
  Curved bodies are lofts or revolves of real cross-sections, never stacks of boxes.
- Round the visible edges (fillet) so it reads as a real manufactured object.
- {MAX_PARTS} parts or fewer: the parts a viewer needs to understand it, each a separate solid, in place.

PARTS list each part id from build() with a viewer-facing label, a material and explode: the offset in
metres that moves it out so the inside shows ([0,0,0] for parts that stay). Open upward or outward.
MATERIALS: {", ".join(catalog["materials"])}. Colours follow the real product."""


def problems(blueprint: dict[str, Any], catalog: dict | None = None) -> list[str]:
    """Problems found without building."""
    catalog = catalog or load()
    found: list[str] = []
    parts = blueprint.get("parts") or []
    if not parts:
        found.append("parts is empty")
    if len(parts) > MAX_PARTS:
        found.append(f"{len(parts)} parts is over the limit of {MAX_PARTS}")
    if not blueprint.get("sources"):
        found.append("sources is empty")
    seen: set[str] = set()
    for part in parts:
        pid = str(part.get("id", ""))
        if not re.fullmatch(r"[a-z0-9_]+", pid) or pid in seen:
            found.append(f"part id '{pid}' must be unique lowercase letters, digits or _")
        seen.add(pid)
        if part.get("material") not in catalog["materials"]:
            found.append(f"{pid}: unknown material '{part.get('material')}'")
        if len(part.get("explode", [])) != 3:
            found.append(f"{pid}: explode needs exactly 3 numbers")
    found += cad.unsafe(blueprint.get("code", ""))
    return found


def build(blueprint: dict[str, Any], folder: Path) -> list[str]:
    """Run the CAD code; record each part's mesh in the blueprint. Returns problems, if any."""
    made, error = cad.run(blueprint["code"], folder)
    if error:
        return [f"the code failed to build: {error}"]
    listed = {p["id"] for p in blueprint["parts"]}
    missing, extra = listed - set(made), set(made) - listed
    found = [f"build() did not return part '{p}'" for p in sorted(missing)]
    found += [f"build() returned '{p}' which is not in parts" for p in sorted(extra)]
    for part in blueprint["parts"]:
        if part["id"] in made:
            part.update({"mesh": Path(made[part["id"]]["mesh"]).name, "min": made[part["id"]]["min"],
                         "max": made[part["id"]]["max"]})
    return found


def library_path(subject: str, folder: Path | None = None) -> Path:
    return (folder or WORLD3D / "blueprints") / slug(subject) / "blueprint.json"


def obtain(subject: str, research: str, text: Any, folder: Path, attempts: int = 4) -> tuple[Path, list[Any]]:
    """Reuse a built object, or have it modelled. Returns its blueprint path and the model calls used."""
    for known in (library_path(subject, folder), library_path(subject)):
        if known.exists():
            return known, []
    catalog = load()
    outputs: list[Any] = []
    note, found = "", []
    target = library_path(subject, folder)
    for _ in range(attempts):
        output = text.generate_json(instructions(catalog), f"OBJECT={subject}\n{note}RESEARCH\n{research}",
                                    BLUEPRINT_SCHEMA, web_search=not note, max_output_tokens=16000)
        outputs.append(output)
        bp = dict(output.value)
        found = problems(bp, catalog) or build(bp, target.parent)
        if not found:
            target.write_text(json.dumps(bp, indent=2) + "\n", encoding="utf-8")
            return target, outputs
        note = ("YOUR LAST ATTEMPT FAILED. Fix these and return the whole blueprint again:\n- "
                + "\n- ".join(found[:10]) + "\nYOUR LAST CODE:\n" + bp.get("code", "")[:12000] + "\n")
    raise ValueError(f"No buildable model for {subject}: {'; '.join(found[:4])[:600]}")
