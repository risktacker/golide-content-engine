"""The locked GOLIDE Black theme (colors, fonts, glow) shared by image and video."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Theme:
    raw: dict

    def color(self, name: str) -> str:
        return self.raw["colors"][name]

    def rgb(self, name: str) -> tuple[int, int, int]:
        value = self.color(name).lstrip("#")
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]

    def font(self, weight: str) -> Path:
        return ROOT / self.raw["fonts"][weight]

    @property
    def glow(self) -> dict:
        return self.raw["glow"]

    @property
    def watermark(self) -> dict:
        return self.raw["watermark"]


@lru_cache(maxsize=1)
def load_theme(path: str | Path | None = None) -> Theme:
    target = Path(path) if path else ROOT / "config/theme.json"
    raw = json.loads(target.read_text(encoding="utf-8"))
    if not raw.get("locked"):
        raise RuntimeError("theme is not locked")
    return Theme(raw)
