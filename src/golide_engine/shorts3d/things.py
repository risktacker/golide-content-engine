"""Every thing a 3D Short's storyboard names, found or built (owner 2026-11-23: "anything that is thrown on Stickman, the
engine has to be able to illustrate").

No fixed prop list. For each thing the storyboard names, the free CC0 model libraries are searched by its name and
search words (Poly Haven's whole model catalogue and Kenney's 3D kits, downloaded on the render machine and cached);
a model is used only when the thing's own noun is in the model's name or tags (a "ball" never becomes a "ballerina").
No library model: the thing is built from the 3D parts the storyboard wrote for it (recipes.object_parts, the engine's
part format). Nothing is ever dropped.

    python -m golide_engine.shorts3d.things --board board.json --engine ~/c3d/engine --lib ~/c3d-lib
"""
from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

UA = {"User-Agent": "golide-content-engine/1.0 (+https://studio.golidee.com)"}
POLYHAVEN = "https://api.polyhaven.com"
# Kenney's 3D kits (CC0). A kit that fails to download is skipped; more can be added without touching anything else.
KENNEY_KITS = ["car-kit", "city-kit-roads", "city-kit-commercial", "city-kit-suburban", "city-kit-industrial", "nature-kit",
               "food-kit", "furniture-kit", "train-kit", "survival-kit", "space-kit", "pirate-kit", "castle-kit",
               "holiday-kit", "conveyor-kit", "minigolf-kit", "blaster-kit", "graveyard-kit", "fantasy-town-kit",
               "racing-kit", "watercraft-kit", "tower-defense-kit", "retro-urban-kit", "toy-car-kit", "mini-market",
               "modular-buildings", "platformer-kit", "prototype-kit", "hexagon-kit", "mini-arena", "coaster-kit",
               "animal-pack", "cube-pets", "weapon-pack", "medieval-town", "factory-kit", "tank-kit", "space-station-kit"]
STOP = {"a", "an", "the", "of", "and", "with", "for", "on", "in", "to", "model", "3d", "big", "small", "old", "new",
        "red", "blue", "green", "white", "black", "yellow", "large", "little", "one", "two"}


def words(text: str) -> list[str]:
    """Plain lower-case words of a name or file name (camelCase and snake_case split), each made singular."""
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(text))
    out = []
    for w in re.split(r"[^A-Za-z0-9]+", text.lower()):
        if not w or w.isdigit() or w in STOP:
            continue
        if len(w) > 4 and w.endswith("ies"):
            w = w[:-3] + "y"
        elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


def head(name: str) -> str:
    """The thing's own noun: the last plain word of its name ("steam locomotive" -> "locomotive")."""
    ws = words(name)
    return ws[-1] if ws else ""


def score(thing: dict, entry_words: set[str]) -> float:
    """How well a library model fits a thing; 0 unless the thing's own noun is in the model's words."""
    h = head(thing.get("name", ""))
    if not h or h not in entry_words:
        return 0.0
    q = set(words(thing.get("name", ""))) | set(words(thing.get("search", "")))
    return 1.0 + len(q & entry_words) / max(1, len(q)) - 0.02 * max(0, len(entry_words) - len(q & entry_words))


def best(thing: dict, index: list[dict]) -> dict | None:
    scored = [(score(thing, set(e["words"])), e) for e in index]
    scored = [x for x in scored if x[0] > 0]
    return max(scored, key=lambda x: x[0])[1] if scored else None


# ---------------- libraries (render machine only: needs the network) ----------------
def _get(url: str, timeout: int = 60) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def _polyhaven_index(lib: Path) -> list[dict]:
    f = lib / "polyhaven-index.json"
    if not f.exists():
        data = json.loads(_get(f"{POLYHAVEN}/assets?t=models"))
        f.write_text(json.dumps(data), encoding="utf-8")
    data = json.loads(f.read_text(encoding="utf-8"))
    return [{"lib": "polyhaven", "id": k, "words": sorted(set(words(v.get("name", k)) + words(k) + [w for t in v.get("tags", []) for w in words(t)]))}
            for k, v in data.items()]


def _kenney_kit(lib: Path, kit: str) -> None:
    dest = lib / "kenney" / kit
    if dest.exists():
        return
    page = _get(f"https://kenney.nl/assets/{kit}").decode("utf-8", "replace")
    m = re.search(r'href="(https://kenney\.nl/media/pages/assets/[^"]+?\.zip)"', page)
    if not m:
        raise RuntimeError(f"no download on {kit}")
    z = zipfile.ZipFile(io.BytesIO(_get(m.group(1), timeout=180)))
    dest.mkdir(parents=True)
    for n in z.namelist():
        low = n.lower()
        if low.endswith(".glb") and "glb" in low:
            (dest / Path(n).name).write_bytes(z.read(n))
    if not any(dest.iterdir()):                                   # kits without a GLB folder: any .glb at all
        for n in z.namelist():
            if n.lower().endswith(".glb"):
                (dest / Path(n).name).write_bytes(z.read(n))


def _kenney_index(lib: Path) -> list[dict]:
    out = []
    for kit in KENNEY_KITS:
        try:
            _kenney_kit(lib, kit)
        except Exception as e:                                    # noqa: BLE001 - a kit that fails is skipped
            print(f"things: kenney {kit} skipped ({e})")
            continue
        for g in sorted((lib / "kenney" / kit).glob("*.glb")):
            out.append({"lib": "kenney", "id": f"{kit}/{g.name}", "path": str(g), "words": sorted(set(words(g.stem)))})
    return out


def index(lib: Path) -> list[dict]:
    lib.mkdir(parents=True, exist_ok=True)
    out: list[dict] = []
    for name, fn in (("polyhaven", _polyhaven_index), ("kenney", _kenney_index)):
        try:
            out += fn(lib)
        except Exception as e:                                    # noqa: BLE001 - parts still build everything
            print(f"things: library {name} unavailable ({e})")
    return out


def _fetch(entry: dict, lib: Path, dest: Path) -> str:
    """Copy (or download) the model into the engine folder; returns its path relative to the engine page."""
    if entry["lib"] == "kenney":
        f = dest / Path(entry["path"]).name
        shutil.copy2(entry["path"], f)
        return f"./golide/lib/{f.name}"
    pid = entry["id"]
    src = lib / "polyhaven" / pid
    if not (src / f"{pid}.gltf").exists():
        g = json.loads(_get(f"{POLYHAVEN}/files/{pid}"))["gltf"]["1k"]["gltf"]
        src.mkdir(parents=True, exist_ok=True)
        (src / f"{pid}.gltf").write_bytes(_get(g["url"]))
        for rel, v in g.get("include", {}).items():
            p = src / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(_get(v["url"]))
    out = dest / pid
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    return f"./golide/lib/{pid}/{pid}.gltf"


def parts_of(thing: dict) -> list[dict]:
    from ..edit.recipes import object_parts
    h = float(thing.get("height_m") or 1.0)
    try:
        return object_parts(thing.get("parts") or [], (1e4, h, 1e4))
    except ValueError:
        return []


def resolve(board: dict, engine: Path, lib: Path) -> list[dict]:
    """things.json for the board scene: each thing with a library model or its own parts."""
    dest = engine / "golide" / "lib"
    dest.mkdir(parents=True, exist_ok=True)
    idx = index(lib) if board.get("things") else []
    out = []
    for t in board.get("things") or []:
        e, model = best(t, idx), None
        if e:
            try:
                model = _fetch(e, lib, dest)
            except Exception as ex:                               # noqa: BLE001 - parts instead
                print(f"things: {t['id']} model {e['id']} failed ({ex})")
        parts = parts_of(t)
        print(f"things: {t['id']} ({t.get('name')}) -> {e['lib'] + ':' + e['id'] if model else ('parts' if parts else 'a labelled block')}")
        out.append({"id": t["id"], "model": model, "parts": parts, "source": (e["lib"] + ":" + e["id"]) if model else ("parts" if parts else "block")})
    (engine / "golide" / "things.json").write_text(json.dumps(out), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", type=Path, required=True)
    ap.add_argument("--engine", type=Path, required=True)
    ap.add_argument("--lib", type=Path, required=True)
    a = ap.parse_args(argv)
    resolve(json.loads(a.board.read_text(encoding="utf-8")), a.engine, a.lib)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
