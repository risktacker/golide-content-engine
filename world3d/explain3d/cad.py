"""Real CAD: build any object from code with build123d (Apache-2.0, open source).

Luna writes a build123d script from the object's real architecture. This module checks the script
is plain CAD code, runs it in its own process with a time limit, and exports every part as a
mesh file the renderer loads. Errors come back as text so the writer can fix its own code.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ALLOWED_IMPORTS = {"build123d", "math"}
BLOCKED_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr",
                 "setattr", "delattr", "input", "breakpoint", "exit", "quit", "help", "memoryview"}
TIMEOUT = 240

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
        path = f"{out}/{pid}.stl"
        export_stl(shape, path, tolerance=size * 0.0015, angular_tolerance=0.15)
        made[pid] = {"mesh": path, "min": [box.min.X, box.min.Y, box.min.Z], "max": [box.max.X, box.max.Y, box.max.Z]}
    print("CAD_OK " + json.dumps(made))
except Exception:
    print("CAD_ERROR " + json.dumps(traceback.format_exc()[-1800:]))
'''


def python() -> str:
    return os.environ.get("WORLD3D_CAD_PYTHON", sys.executable)


def unsafe(code: str) -> list[str]:
    """Anything that is not plain CAD code. The script may only use build123d and math."""
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


def run(code: str, out: Path) -> tuple[dict, str]:
    """Build the object. Returns ({part_id: {mesh, min, max}}, "") or ({}, error text)."""
    bad = unsafe(code)
    if bad:
        return {}, "; ".join(bad)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        script, runner = Path(tmp) / "object.py", Path(tmp) / "runner.py"
        script.write_text(code, encoding="utf-8")
        runner.write_text(RUNNER, encoding="utf-8")
        try:
            done = subprocess.run([python(), "-I", str(runner), str(script), str(out)], capture_output=True,
                                  text=True, timeout=TIMEOUT, cwd=tmp)
        except subprocess.TimeoutExpired:
            return {}, f"the build took longer than {TIMEOUT} seconds; simplify it"
    for line in done.stdout.splitlines():
        if line.startswith("CAD_OK "):
            return json.loads(line[7:]), ""
        if line.startswith("CAD_ERROR "):
            return {}, json.loads(line[10:])
    return {}, (done.stderr or done.stdout or "the build produced nothing")[-1500:]
