from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class Scene:
    id: str
    media: Path
    duration: float
    caption: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any], base: Path) -> "Scene":
        try:
            duration = float(raw["duration"])
            if duration <= 0:
                raise ValueError
            return cls(
                id=str(raw["id"]),
                media=(base / str(raw["media"])).resolve(),
                duration=duration,
                caption=str(raw.get("caption", "")).strip(),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ManifestError(f"Invalid scene: {raw!r}") from exc


@dataclass(frozen=True)
class Project:
    id: str
    title: str
    format: str
    width: int
    height: int
    fps: int
    max_cost_usd: float
    narration: Path
    music: Path | None
    scenes: tuple[Scene, ...]
    approved: bool

    @classmethod
    def from_dict(cls, raw: dict[str, Any], base: Path) -> "Project":
        fmt = str(raw.get("format", "short"))
        dimensions = {"short": (1080, 1920), "long": (1920, 1080)}
        if fmt not in dimensions:
            raise ManifestError("format must be 'short' or 'long'")
        width, height = dimensions[fmt]
        scenes = tuple(Scene.from_dict(x, base) for x in raw.get("scenes", []))
        if not scenes:
            raise ManifestError("at least one scene is required")
        max_duration = 90 if fmt == "short" else 300
        if sum(x.duration for x in scenes) > max_duration:
            raise ManifestError(f"{fmt} duration exceeds {max_duration} seconds")
        try:
            ceiling = float(raw["max_cost_usd"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ManifestError("max_cost_usd is required") from exc
        if ceiling <= 0:
            raise ManifestError("max_cost_usd must be positive")
        music = raw.get("music")
        return cls(
            id=str(raw["id"]),
            title=str(raw["title"]),
            format=fmt,
            width=width,
            height=height,
            fps=int(raw.get("fps", 30)),
            max_cost_usd=ceiling,
            narration=(base / str(raw["narration"])).resolve(),
            music=(base / str(music)).resolve() if music else None,
            scenes=scenes,
            approved=bool(raw.get("publish", {}).get("approved", False)),
        )

