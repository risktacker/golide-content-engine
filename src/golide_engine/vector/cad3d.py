"""Any real object for the live 3D engine, built with real CAD.

When a storyboard names a real object with no parts (`3d: object=<real name>; move=...; on=...`), the
text model writes build123d code (open-source CAD, Apache-2.0) from the object's published architecture,
this module checks the code is plain CAD, builds it in its own process and keeps the parts. motion3d then
draws them in the house look. Build errors go back to the model to fix. Anything that cannot be built is
skipped and the scene falls back to its drawing, so a video never fails on it.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "config" / "cad3d.json"
CACHE = Path(os.environ.get("GOLIDE_CAD3D", Path.home() / ".cache" / "golide-cad3d"))
ALLOWED_IMPORTS = {"build123d", "math"}
BLOCKED_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr",
                 "setattr", "delattr", "input", "breakpoint", "exit", "quit", "help", "memoryview"}
TIMEOUT = 240
MAX_PARTS = 12
SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
        "code": {"type": "string"},
        "parts": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "label": {"type": "string"},
            "gold": {"type": "boolean"}, "mover": {"type": "boolean"},
            "explode": {"type": "array", "items": {"type": "number"}},
            "color": {"type": "array", "items": {"type": "number"}},
        }, "required": ["id", "label", "gold", "mover", "explode", "color"], "additionalProperties": False}},
    },
    "required": ["name", "sources", "code", "parts"], "additionalProperties": False,
}
INSTRUCTIONS = f"""You are a CAD engineer. You model a real thing so a viewer recognises it at a glance and sees how
it works, for an explainer video. You write Python for build123d (the open-source CAD library).

Research first: search for its published dimensions, drawings, teardowns and photos. Model the real
architecture: the real parts, their real shapes, sizes in metres and how they connect. List the URLs you
used in sources. For weapons, only the general layout, never manufacturing detail.

CODE RULES
- Import only build123d and math. Define build() returning a dict {{part_id: shape}}.
- Metres. Z is up, the object stands on z=0, its front faces -Y.
- Real CAD: sketches, extrude, revolve, loft, sweep, fillet, chamfer, mirror, boolean cuts, arrays.
  Curved bodies are lofts or revolves of real cross-sections, never stacks of boxes. Fillet visible edges.
- {MAX_PARTS} parts or fewer, each a separate solid in place: the parts a viewer needs to see how it works.
- A repeated piece the story can count, point at or measure (a blade, a wheel, a cylinder, a leg) is
  its own part with its own id (blade_1, blade_2, blade_3), never fused into one solid.

PARTS lists every id from build() with a viewer-facing label in the words a narrator would use
("Blade", "Generator housing", "Rear wheel"). color is the part's real colour as the
real object is made and painted, as [r, g, b] 0-255 (brushed steel, white fibreglass, red paint, black
rubber, copper windings). Where the real colour is unknown or the part is hidden, pick the colour its story
suggests. Exactly one part has gold=true: the part the story is about; it glows in its own colour. mover=true on the parts that move when it opens. explode is the offset in metres that
moves the part out so the inside shows ([0,0,0] for parts that stay); open upward or outward."""

RUNNER = r'''
import json, math, sys, traceback
from build123d import *
from build123d import export_stl
code, out = sys.argv[1], sys.argv[2]
space = {"__name__": "golide_cad"}
try:
    exec(compile(open(code).read(), "object.py", "exec"), space)
    parts = space["build"]()
    if not isinstance(parts, dict) or not parts:
        raise ValueError("build() must return a non-empty dict of part id -> shape")
    made = {}
    for pid, shape in parts.items():
        shape = shape.part if hasattr(shape, "part") and not hasattr(shape, "bounding_box") else shape
        box = shape.bounding_box()
        size = max(box.size.X, box.size.Y, box.size.Z)
        if not size > 0:
            raise ValueError(f"part {pid} is empty")
        export_stl(shape, f"{out}/{pid}.stl", tolerance=size * 0.002, angular_tolerance=0.2)
        made[pid] = f"{pid}.stl"
    print("CAD_OK " + json.dumps(made))
except Exception:
    print("CAD_ERROR " + json.dumps(traceback.format_exc()[-1800:]))
'''


def settings() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")[:60]


def folder(name: str) -> Path:
    return CACHE / slug(name)


def available(name: str) -> bool:
    return bool(slug(name)) and (folder(name) / "object.json").exists()


def unsafe(code: str) -> list[str]:
    """Anything that is not plain CAD code."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return [f"syntax error on line {error.lineno}: {error.msg}"]
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [f"import {a.name} is not allowed" for a in node.names if a.name.split(".")[0] not in ALLOWED_IMPORTS]
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
            found.append(f"from {node.module} import is not allowed")
        elif isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            found.append(f"{node.id} is not allowed")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            found.append(f"private attribute {node.attr} is not allowed")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "build" for n in tree.body):
        found.append("the script must define build() returning {part_id: shape}")
    return found


def build(code: str, out: Path) -> tuple[dict, str]:
    """Run the CAD code in its own process. ({part_id: mesh file}, "") or ({}, error)."""
    bad = unsafe(code)
    if bad:
        return {}, "; ".join(bad)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        script, runner = Path(tmp) / "object.py", Path(tmp) / "runner.py"
        script.write_text(code, encoding="utf-8")
        runner.write_text(RUNNER, encoding="utf-8")
        try:
            done = subprocess.run([os.environ.get("GOLIDE_CAD_PYTHON", sys.executable), "-I", str(runner),
                                   str(script), str(out)], capture_output=True, text=True, timeout=TIMEOUT, cwd=tmp)
        except subprocess.TimeoutExpired:
            return {}, f"the build took longer than {TIMEOUT} seconds; simplify it"
    for line in done.stdout.splitlines():
        if line.startswith("CAD_OK "):
            return json.loads(line[7:]), ""
        if line.startswith("CAD_ERROR "):
            return {}, json.loads(line[10:])
    return {}, (done.stderr or done.stdout or "the build produced nothing")[-1500:]


def problems(obj: dict) -> list[str]:
    parts = obj.get("parts") or []
    found = [] if parts else ["parts is empty"]
    if len(parts) > MAX_PARTS:
        found.append(f"{len(parts)} parts is over {MAX_PARTS}")
    ids = [str(p.get("id", "")) for p in parts]
    if len(set(ids)) != len(ids) or not all(re.fullmatch(r"[a-z0-9_]+", i) for i in ids):
        found.append("part ids must be unique lowercase letters, digits or _")
    if sum(bool(p.get("gold")) for p in parts) != 1:
        found.append("exactly one part must have gold=true")
    if any(len(p.get("explode", [])) != 3 for p in parts):
        found.append("every explode needs exactly 3 numbers")
    if any(len(p.get("color", [])) != 3 or not all(0 <= c <= 255 for c in p.get("color", [])) for p in parts):
        found.append("every color needs 3 numbers from 0 to 255")
    return found + unsafe(obj.get("code", ""))


def make(name: str, research: str, text: Any, attempts: int = 4) -> list[Any]:
    """Model and build one object, retrying with its own errors. Returns the model outputs used."""
    out = folder(name)
    outputs, note, found = [], "", []
    for _ in range(attempts):
        output = text.generate_json(INSTRUCTIONS, f"OBJECT={name}\n{note}RESEARCH\n{research}", SCHEMA,
                                    web_search=not note, max_output_tokens=16000)
        outputs.append(output)
        obj = dict(output.value)
        found = problems(obj)
        if not found:
            made, error = build(obj["code"], out)
            listed = {p["id"] for p in obj["parts"]}
            found = [f"the code failed to build: {error}"] if error else (
                [f"build() and parts disagree: {sorted(listed ^ set(made))}"] if listed != set(made) else [])
            if not found:
                for part in obj["parts"]:
                    part["mesh"] = made[part["id"]]
                (out / "object.json").write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
                return outputs
        note = ("YOUR LAST ATTEMPT FAILED. Fix these and return the whole object again:\n- " + "\n- ".join(found[:10])
                + "\nYOUR LAST CODE:\n" + obj.get("code", "")[:12000] + "\n")
    raise ValueError(f"no buildable model for {name}: {'; '.join(found[:3])[:500]}")


def named_objects(scenes: list[dict]) -> list[str]:
    """Real objects the storyboard asked for by name only (no parts, not a preset)."""
    from .motion3d import OBJECTS

    names = []
    for scene in scenes:
        for key in ("figure", "figure_b"):
            line = str(scene.get(key) or "").strip()
            if not line.lower().startswith("3d:"):
                continue
            items = [i.strip() for i in line[3:].split(";") if i.strip()]
            fields = dict(i.split("=", 1) for i in items if "=" in i)
            has_parts = any(re.match(r"(box|cyl|sphere|cone)\s", i) for i in items)
            name = fields.get("object", "").strip()
            if name and not has_parts and name.lower() not in OBJECTS and name not in names:
                names.append(name)
    return names


def prepare(scenes: list[dict], research: str, text: Any, record: Callable[[str, Any], None]) -> list[str]:
    """Build every named object a video needs, once. Returns the names that could not be built."""
    cfg = settings()
    if not cfg.get("enabled"):
        return []
    failed = []
    for name in named_objects(scenes)[: cfg.get("max_objects_per_video", 4)]:
        if available(name):
            continue
        try:
            for output in make(name, research, text):
                record("cad3d", output)
        except Exception as error:  # noqa: BLE001 - one object must never stop a video
            failed.append(name)
            print(json.dumps({"status": "cad3d_skipped", "object": name, "reason": str(error)[:300]}))
    return failed


@lru_cache(maxsize=32)
def parts(name: str) -> tuple:
    """((points, triangles, gold, mover, explode, label, colour), ...) Z-up, longest side 3, centred, on z=0."""
    import trimesh

    obj = json.loads((folder(name) / "object.json").read_text(encoding="utf-8"))
    loaded = []
    for part in obj["parts"]:
        mesh = trimesh.load(str(folder(name) / part["mesh"]), force="mesh")
        loaded.append((np.asarray(mesh.vertices, float), np.asarray(mesh.faces, np.int64), part))
    every = np.vstack([v for v, _, _ in loaded])
    lo, hi = every.min(0), every.max(0)
    scale = 3.0 / max(1e-9, float((hi - lo).max()))
    shift = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
    return tuple(((v - shift) * scale, f, bool(p["gold"]), bool(p["mover"]),
                  np.asarray(p["explode"], float) * scale, p["label"],
                  np.asarray(p.get("color") or (70, 74, 82), np.float32)) for v, f, p in loaded)
