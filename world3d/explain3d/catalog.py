"""What the 3D kit can build. The model is only ever offered what really exists."""

from __future__ import annotations

import json
from pathlib import Path

WORLD3D = Path(__file__).resolve().parents[1]


def load() -> dict:
    return json.loads((WORLD3D / "catalog.json").read_text(encoding="utf-8"))


def menu(catalog: dict) -> str:
    rows = ["PART BUILDERS (every part is built along +X from x=0; numbers are metres):"]
    for name, b in catalog["builders"].items():
        rows.append(f"- {name}: {b['use']}. Needs {', '.join(b['required'])}."
                    + (f" May use {', '.join(b['optional'])}." if b["optional"] else ""))
    rows.append("MATERIALS: " + ", ".join(catalog["materials"]))
    return "\n".join(rows)
