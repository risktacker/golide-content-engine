"""Ready-made 3D objects for the live 3D engine (vector/motion3d).

The engine draws any triangle mesh in the house look (charcoal, white seams, one gold part), so a
licence-clear model file gives it a real object at once. Each library object is grouped into a few
named parts so moves work as they do for built objects: explode, lift, slide, spin.

Rules (owner, 2026-11-07): only CC0 or NASA sources, listed in config/library3d.json with their
licence. Colours and textures from the file are dropped, so printed logos and insignia never show.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
INDEX = ROOT / "config" / "library3d.json"
CACHE = Path(os.environ.get("GOLIDE_LIBRARY3D", Path.home() / ".cache" / "golide-library3d"))
FACE_BUDGET = 60000          # whole object, after simplifying; small pieces are never simplified
KEEP_WHOLE = 1500           # a piece this small keeps every face (simplifying thin panels tears them)


@lru_cache(maxsize=1)
def index() -> dict:
    return json.loads(INDEX.read_text(encoding="utf-8"))["objects"]


def find(name: str) -> str | None:
    """The library key for a storyboard name, or None."""
    want = re.sub(r"\s+", " ", str(name or "").strip().lower())
    for key, entry in index().items():
        if want == key or want in entry.get("aliases", []):
            return key
    return None


def path(key: str) -> Path:
    return CACHE / index()[key]["repo_path"]


def available(name: str) -> bool:
    key = find(name)
    return key is not None and path(key).exists()


def _simplify(vertices: np.ndarray, faces: np.ndarray, target: int) -> tuple[np.ndarray, np.ndarray]:
    if len(faces) <= target:
        return vertices, faces
    import fast_simplification

    v, f = fast_simplification.simplify(vertices.astype(np.float32), faces.astype(np.int32),
                                        target_reduction=1 - target / len(faces))
    return np.asarray(v, np.float64), np.asarray(f, np.int64)


def _two_sided(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Thin panels (solar arrays, dishes, wings) have one side only; the engine hides faces that
    point away, so each face gets a back copy on its own vertices, slightly offset inward."""
    a, b, c = vertices[faces[:, 0]], vertices[faces[:, 1]], vertices[faces[:, 2]]
    n = np.cross(b - a, c - a)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    back = vertices[faces.reshape(-1)] - np.repeat(n, 3, axis=0) * 1e-4
    start = len(vertices)
    back_faces = (np.arange(len(back)).reshape(-1, 3) + start)[:, [0, 2, 1]]
    return np.vstack([vertices, back]), np.vstack([faces, back_faces])


@lru_cache(maxsize=16)
def parts(key: str) -> tuple:
    """((points, triangles, gold, mover), ...): Z-up, longest side 3 units, centred, standing on
    z = 0, the same frame motion3d uses for built objects."""
    import trimesh

    entry = index()[key]
    scene = trimesh.load(str(path(key)), force="scene")
    rules = [(label, [re.compile(p) for p in pats]) for label, pats in entry["parts"].items()]
    grouped: dict[str, list] = {label: [] for label, _ in rules}
    for node in scene.graph.nodes_geometry:
        transform, geometry = scene.graph[node]
        mesh = scene.geometry[geometry]
        if not hasattr(mesh, "faces") or len(mesh.faces) == 0:
            continue
        label = next(label for label, pats in rules if any(p.search(node) for p in pats))
        verts = trimesh.transformations.transform_points(mesh.vertices, transform)
        grouped[label].append((verts, np.asarray(mesh.faces)))
    total = sum(len(f) for meshes in grouped.values() for _, f in meshes) or 1
    ratio = min(1.0, FACE_BUDGET / total)
    out = []
    for label, meshes in grouped.items():
        if not meshes:
            continue
        verts, faces, offset = [], [], 0
        for v, f in meshes:
            if len(f) > KEEP_WHOLE and ratio < 1:      # each piece on its own, so pieces never fuse or tear
                v, f = _simplify(v, f, max(KEEP_WHOLE, int(len(f) * ratio)))
            verts.append(v)
            faces.append(f + offset)
            offset += len(v)
        v, f = np.vstack(verts), np.vstack(faces)
        v, f = _two_sided(v, f)
        out.append((label, v[:, [0, 2, 1]] * (1, -1, 1), f))     # glTF is Y-up; the engine is Z-up
    every = np.vstack([v for _, v, _ in out])
    lo, hi = every.min(0), every.max(0)
    scale = 3.0 / max(1e-9, float((hi - lo).max()))
    shift = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
    return tuple(((v - shift) * scale, f, label == entry.get("gold"), label == entry.get("mover"), label)
                 for label, v, f in out)
