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
MAX_GROUPS = 6              # parts kept when a model gives no part list (the rest join the body)
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
    """True when the object is in the library and its file is (or can be made) local."""
    key = find(name)
    return key is not None and (path(key).exists() or fetch(key))


_FAILED: set = set()


def fetch(key: str) -> bool:
    """Bring one model file into the cache with a sparse git checkout (only that file). Any
    failure just means the object is unavailable, so the scene falls back to its drawing."""
    entry = index()[key]
    repo = json.loads(INDEX.read_text(encoding="utf-8")).get("_sources", {}).get(entry["source"])
    if not repo or key in _FAILED or os.environ.get("GOLIDE_LIBRARY3D_OFFLINE"):
        return False
    import subprocess
    import tempfile

    target = path(key)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            run = lambda *a: subprocess.run(a, cwd=tmp, check=True, capture_output=True, timeout=300)
            run("git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout", repo, "r")
            r = Path(tmp) / "r"
            subprocess.run(["git", "sparse-checkout", "set", "--no-cone", entry["repo_path"]], cwd=r,
                           check=True, capture_output=True, timeout=300)
            subprocess.run(["git", "checkout", "-q"], cwd=r, check=True, capture_output=True, timeout=300)
            got = r / entry["repo_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            got.replace(target)
        return target.exists()
    except Exception:
        _FAILED.add(key)
        return False


def names() -> list[str]:
    return sorted(index())


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


def _clusters(meshes: list) -> dict[str, list]:
    """Split meshes into their connected pieces and gather the pieces into up to MAX_GROUPS
    clusters by position (k-means on piece centres, weighted by size), so any model opens up."""
    import trimesh

    pieces = []
    for v, f in meshes:
        for piece in trimesh.Trimesh(v, f, process=False).split(only_watertight=False):
            pieces.append((np.asarray(piece.vertices), np.asarray(piece.faces)))
    if len(pieces) < 2:
        return {"body": meshes}
    centres = np.array([v.mean(0) for v, _ in pieces])
    weight = np.array([len(f) for _, f in pieces], float)
    k = min(MAX_GROUPS, len(pieces))
    rng = np.random.default_rng(7)
    seeds = centres[rng.choice(len(pieces), k, replace=False, p=weight / weight.sum())]
    for _ in range(25):
        label = np.argmin(((centres[:, None] - seeds[None]) ** 2).sum(-1), axis=1)
        for j in range(k):
            if (label == j).any():
                seeds[j] = np.average(centres[label == j], axis=0, weights=weight[label == j])
    out: dict[str, list] = {}
    for piece, j in zip(pieces, label):
        out.setdefault(f"section {j + 1}", []).append(piece)
    return out


@lru_cache(maxsize=16)
def parts(key: str) -> tuple:
    """((points, triangles, gold, mover), ...): Z-up, longest side 3 units, centred, standing on
    z = 0, the same frame motion3d uses for built objects."""
    import trimesh

    entry = index()[key]
    scene = trimesh.load(str(path(key)), force="scene")
    meshes_by_node = []
    for node in scene.graph.nodes_geometry:
        transform, geometry = scene.graph[node]
        mesh = scene.geometry[geometry]
        if not hasattr(mesh, "faces") or len(mesh.faces) == 0:
            continue
        verts = trimesh.transformations.transform_points(mesh.vertices, transform)
        meshes_by_node.append((node, verts, np.asarray(mesh.faces)))
    grouped: dict[str, list] = {}
    if entry.get("parts"):                      # named parts from the index
        rules = [(label, [re.compile(p) for p in pats]) for label, pats in entry["parts"].items()]
        grouped = {label: [] for label, _ in rules}
        for node, verts, faces in meshes_by_node:
            label = next((label for label, pats in rules if any(p.search(node) for p in pats)), "body")
            grouped.setdefault(label, []).append((verts, faces))
    else:                                       # any model: its own node names, biggest groups kept
        stems: dict[str, list] = {}
        for node, verts, faces in meshes_by_node:
            stem = re.sub(r"(\.\d+|_[0-9a-f]{6})+$", "", node)
            stems.setdefault(stem, []).append((verts, faces))
        ranked = sorted(stems, key=lambda k: -sum(len(f) for _, f in stems[k]))
        for i, stem in enumerate(ranked):
            grouped.setdefault(stem if i < MAX_GROUPS else "body", []).extend(stems[stem])
        if len(ranked) < 3:                     # one-piece model: split it by where its pieces sit
            grouped = _clusters([m for meshes in stems.values() for m in meshes])
            ranked = sorted(grouped, key=lambda k: -sum(len(f) for _, f in grouped[k]))
        if not entry.get("gold") and len(ranked) > 1:
            entry = {**entry, "gold": ranked[1], "mover": ranked[1]}
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
