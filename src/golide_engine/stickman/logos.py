"""Real brand logos for Stickman Shorts (owner 2026-11-18: "official logos and branding of those said companies").

The logos come from the simple-icons package (npm, CC0 data of each brand's own mark): the brands the script names
are found by their names (and known other names, such as Twitter for X), and each one's 24x24 path and brand colour
is handed to the world as `LOGO = { slug: { d, hex, title } }`, which the GOLIDE world kit draws on signs, boards,
karts, screens and satellites.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tarfile
import tempfile
import unicodedata
from pathlib import Path

VERSION = "13.21.0"
MOST = 16


def _cache() -> Path:
    return Path(os.environ.get("GOLIDE_CACHE") or Path.home() / ".cache" / "golide") / f"simple-icons-{VERSION}"


def package() -> Path | None:
    """The simple-icons package folder, fetched once with npm (the runner and this workspace both reach npm)."""
    root = _cache()
    if (root / "_data" / "simple-icons.json").exists():
        return root
    try:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["npm", "pack", f"simple-icons@{VERSION}", "--silent"], cwd=tmp, check=True,
                           capture_output=True, timeout=180)
            tgz = next(Path(tmp).glob("simple-icons-*.tgz"))
            with tarfile.open(tgz) as tar:
                tar.extractall(tmp, filter="data")
            root.parent.mkdir(parents=True, exist_ok=True)
            os.replace(Path(tmp) / "package", root)
        return root
    except (OSError, subprocess.SubprocessError, StopIteration, tarfile.TarError) as e:
        print(json.dumps({"status": "stickman_logos_unavailable", "error": str(e)[:200]}))
        return None


def slug_of(title: str) -> str:
    """simple-icons' own title-to-slug rule."""
    s = title.lower().replace("+", "plus").replace(".", "dot").replace("&", "and")
    s = unicodedata.normalize("NFD", s)
    return re.sub(r"[^a-z0-9]", "", s)


def _names(icon: dict) -> list[str]:
    names = [icon["title"]]
    aka = (icon.get("aliases") or {}).get("aka") or []
    return names + [a for a in aka if isinstance(a, str)]


def _said(name: str, text: str) -> bool:
    if len(name) < 3:
        return False
    # as written, capitals and all ("Google", "NVIDIA" or "Nvidia"); a common word that is also a brand ("First",
    # "Rocket") may come along: the storyboard writer uses only the logos of the companies the story is about
    alt = {name, name.capitalize()} if name.isupper() and len(name) > 3 else {name}
    return any(re.search(r"(?<![\w])" + re.escape(n) + r"(?![\w])", text) for n in alt)


def for_script(text: str, pkg: Path | None = None) -> dict[str, dict[str, str]]:
    """The logos of the brands the script names, most-mentioned first, up to MOST."""
    pkg = pkg or package()
    if not pkg:
        return {}
    data = json.loads((pkg / "_data" / "simple-icons.json").read_text(encoding="utf-8"))
    icons = data if isinstance(data, list) else data.get("icons", [])
    found: list[tuple[int, str, dict]] = []
    for icon in icons:
        hits = [n for n in _names(icon) if _said(n, text)]
        if not hits:
            continue
        slug = icon.get("slug") or slug_of(icon["title"])
        svg = pkg / "icons" / f"{slug}.svg"
        if not svg.exists():
            continue
        m = re.search(r' d="([^"]+)"', svg.read_text(encoding="utf-8"))
        if m:
            first = min(text.lower().find(n.lower()) for n in hits)
            found.append((first, slug, {"d": m.group(1), "hex": icon.get("hex") or "111111", "title": icon["title"]}))
    found.sort(key=lambda x: x[0])
    return {slug: v for _, slug, v in found[:MOST]}


def js(logos: dict[str, dict[str, str]]) -> str:
    return "const LOGO = " + json.dumps(logos, ensure_ascii=False) + ";\n"
