"""Exact real objects (owner 2026-11-10): a published 3D model of the real thing comes first; the
CAD model call (cad3d) builds one only when no usable published model exists.

Source: Sketchfab's downloadable models under licences that allow use in monetised videos: CC0
(no conditions) and CC BY 4.0 (credit in the description, which the engine writes). Share-alike and
non-commercial models are never used. The search needs SKETCHFAB_TOKEN (a free Sketchfab account's
API token, as a GitHub secret); without it this step is skipped and CAD builds the object.

The best match is chosen by the text model from the search results (title, description, tags), so a
"Tesla Roadster" never comes back as a toy car. The model is cut into its own parts (the meshes it
was published with), coloured from its own materials, reduced to a size the renderer draws quickly,
and stored in the same cache folder and format as a CAD build, so everything after this is shared.
"""

from __future__ import annotations

import io
import json
import os
import re
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

API = "https://api.sketchfab.com/v3"
LICENCES = {"cc0": "CC0 1.0", "by": "CC BY 4.0"}
MAX_FACES = 60000
MAX_PARTS = 24

PICK_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["index", "why"],
    "properties": {"index": {"type": "integer"}, "why": {"type": "string"}},
}


def token() -> str:
    return os.environ.get("SKETCHFAB_TOKEN", "").strip()


def _get(url: str, auth: bool = False) -> Any:
    headers = {"User-Agent": "golide-engine"}
    if auth:
        headers["Authorization"] = f"Token {token()}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        data = r.read()
    return json.loads(data) if data[:1] in (b"{", b"[") else data


def search(name: str, count: int = 12) -> list[dict]:
    found = []
    for licence in LICENCES:
        q = urllib.parse.urlencode({"type": "models", "q": name, "downloadable": "true", "license": licence,
                                    "count": count, "sort_by": "-likeCount"})
        for m in _get(f"{API}/search?{q}", auth=True).get("results", []):
            if (m.get("license") or {}).get("slug", licence) not in LICENCES:
                continue
            found.append({"uid": m["uid"], "name": m.get("name", ""), "author": (m.get("user") or {}).get("displayName", ""),
                          "url": m.get("viewerUrl", ""), "licence": (m.get("license") or {}).get("slug", licence),
                          "description": str(m.get("description", ""))[:300],
                          "tags": [t.get("name", "") for t in m.get("tags", [])][:12],
                          "faces": int(m.get("faceCount") or 0), "likes": int(m.get("likeCount") or 0)})
    return found


def choose(text: Any, name: str, research: str, results: list[dict]) -> tuple[dict | None, Any]:
    if not results:
        return None, None
    listing = "\n".join(f"{i}. {r['name']} | {r['description'][:160]} | tags: {', '.join(r['tags'])} | {r['faces']} faces"
                        for i, r in enumerate(results))
    out = text.generate_json(
        "Pick the published 3D model that IS the real object named (the same product, model and generation, "
        "not a toy, a concept, a fan-made look-alike, a scene containing it, or a different version). If none "
        "is clearly that exact object, answer index -1. Prefer complete, detailed, untextured-or-clean models.",
        f"OBJECT: {name}\nFACTS: {research[:1500]}\n\nRESULTS:\n{listing}", PICK_SCHEMA, max_output_tokens=400)
    i = int(out.value.get("index", -1))
    return (results[i] if 0 <= i < len(results) else None), out


def _download(uid: str) -> bytes:
    info = _get(f"{API}/models/{uid}/download", auth=True)
    url = (info.get("glb") or {}).get("url") or (info.get("gltf") or {}).get("url")
    if not url:
        raise RuntimeError("no downloadable glTF for this model")
    return _get(url)


def _scene(data: bytes):
    import trimesh

    if data[:4] == b"glTF":
        return trimesh.load(io.BytesIO(data), file_type="glb", force="scene")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        gltf = next(n for n in z.namelist() if n.endswith(".gltf"))
        root = Path(gltf).parent
        files = {str(Path(n).relative_to(root)) if str(root) != "." else n: z.read(n) for n in z.namelist() if not n.endswith("/")}
        resolver = trimesh.resolvers.ZipResolver(z) if hasattr(trimesh.resolvers, "ZipResolver") else None
        return trimesh.load(io.BytesIO(files[Path(gltf).name]), file_type="gltf", force="scene",
                            resolver=resolver or trimesh.resolvers.FilePathResolver("."))


def _colour(geom) -> list[int]:
    """The part's own colour from its material (base colour, or the mean of its texture)."""
    try:
        mat = geom.visual.material
        image = getattr(mat, "baseColorTexture", None) or getattr(mat, "image", None)
        if image is not None:
            px = np.asarray(image.convert("RGB").resize((32, 32)), float).reshape(-1, 3)
            return [int(v) for v in px.mean(0)]
        base = getattr(mat, "baseColorFactor", None)
        if base is not None:
            b = np.asarray(base, float)[:3]
            return [int(v) for v in (b * 255 if b.max() <= 1.0 else b)]
    except Exception:  # noqa: BLE001
        pass
    try:
        c = np.asarray(geom.visual.vertex_colors, float)[:, :3]
        return [int(v) for v in c.mean(0)]
    except Exception:  # noqa: BLE001
        return [190, 192, 196]


def _label(node: str, i: int) -> str:
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", re.sub(r"[_\-.]+", " ", node))
    words = re.sub(r"\b(mesh|object|geometry|primitive|node|polysurface|\d+)\b", " ", spaced, flags=re.I).split()
    return " ".join(words).strip().capitalize() or f"Part {i + 1}"


def to_parts(scene) -> list[dict]:
    """The model's own meshes as parts, Z-up, merged down to at most MAX_PARTS and MAX_FACES."""
    import trimesh

    items = []
    for node in scene.graph.nodes_geometry:
        transform, geom_name = scene.graph[node]
        geom = scene.geometry[geom_name]
        if not isinstance(geom, trimesh.Trimesh) or not len(geom.faces):
            continue
        mesh = geom.copy()
        mesh.apply_transform(transform)
        items.append({"mesh": mesh, "label": _label(str(node), len(items)), "color": _colour(geom)})
    if not items:
        raise RuntimeError("the model has no meshes")
    yup = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)   # glTF is Y-up
    for it in items:
        it["mesh"].apply_transform(yup)
    items.sort(key=lambda it: -len(it["mesh"].faces))
    if len(items) > MAX_PARTS:                    # small pieces join the closest-coloured big part
        keep, rest = items[:MAX_PARTS - 1], items[MAX_PARTS - 1:]
        keep.append({"mesh": trimesh.util.concatenate([r["mesh"] for r in rest]), "label": "Details",
                     "color": rest[0]["color"]})
        items = keep
    total = sum(len(it["mesh"].faces) for it in items)
    if total > MAX_FACES:
        for it in items:
            target = max(200, int(len(it["mesh"].faces) * MAX_FACES / total))
            try:
                it["mesh"] = it["mesh"].simplify_quadric_decimation(face_count=target)
            except Exception:  # noqa: BLE001 - keep it whole when the reducer is unavailable
                pass
    return items


def fetch(name: str, research: str, text: Any, out: Path) -> tuple[dict, list]:
    """Find, choose, download and store the real model. Returns (object.json, paid outputs)."""
    if not token():
        raise RuntimeError("SKETCHFAB_TOKEN is not set")
    results = search(name)
    pick, paid = choose(text, name, research, results)
    outputs = [paid] if paid is not None else []
    if pick is None:
        raise RuntimeError("no published model is clearly this exact object")
    items = to_parts(_scene(_download(pick["uid"])))
    out.mkdir(parents=True, exist_ok=True)
    every = np.vstack([np.asarray(it["mesh"].vertices) for it in items])
    centre, size = every.mean(0), float((every.max(0) - every.min(0)).max())
    parts = []
    for i, it in enumerate(items):
        pid = f"part_{i + 1}"
        it["mesh"].export(out / f"{pid}.stl")
        away = np.asarray(it["mesh"].vertices).mean(0) - centre
        n = float(np.linalg.norm(away)) or 1.0
        parts.append({"id": pid, "label": it["label"], "color": it["color"], "gold": i == 0 and len(items) > 1 and False,
                      "mover": False, "explode": [round(float(v), 4) for v in away / n * size * 0.35], "mesh": f"{pid}.stl"})
    obj = {"name": name, "source": "published-model", "parts": parts,
           "credit": {"title": pick["name"], "author": pick["author"], "url": pick["url"],
                      "licence": LICENCES[pick["licence"]]}}
    (out / "object.json").write_text(json.dumps(obj, indent=2), encoding="utf-8")
    print(json.dumps({"status": "real_model", "object": name, "model": pick["name"], "licence": pick["licence"],
                      "parts": len(parts)}))
    return obj, outputs


def credit_line(obj: dict) -> str:
    c = obj.get("credit") or {}
    if not c:
        return ""
    return f"3D model \"{c['title']}\" by {c['author']} ({c['licence']}): {c['url']}"
