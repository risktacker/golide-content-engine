"""Labels are drawn on finished frames from 3D positions, so text stays perfectly sharp
and changing a word never needs a new render."""
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view

from .ease import smooth, span


def project(scene, model, specs, t):
    """Screen position of each label's part at time t (0-1 from top-left)."""
    out = []
    for s in specs:
        part = model.part(s["part"])
        p = world_to_camera_view(scene, scene.camera, part.anchor_world())
        u = smooth(span(t, s["start"], s["start"] + 0.45)) * (1 - smooth(span(t, s["end"] - 0.4, s["end"])))
        out.append({"text": s.get("text", part.label), "x": p.x, "y": 1 - p.y, "alpha": u,
                    "dx": s.get("dx", 0.08), "dy": s.get("dy", -0.08)})
    return out
