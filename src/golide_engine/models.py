from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ManifestError(ValueError):
    pass


MOTION_TYPES = {"hold", "push-in", "pull-out", "pan-left", "pan-right", "reframe", "layer-reveal"}
TRANSITIONS = {"cut", "paper-wipe", "match-cut", "object-transition"}
EASINGS = {"linear", "ease-in", "ease-out", "ease-in-out"}
INTENSITIES = {"subtle", "medium", "strong"}
AUDIO_CUES = {"none", "tick", "soft-trace", "paper", "swipe", "impact"}
ANNOTATION_KINDS = {"none", "keyword", "number", "label", "callout"}
ANNOTATION_POSITIONS = {"top", "center", "bottom", "left", "right"}
COLOR_TOKENS = {"warm-ivory", "deep-navy", "neon-blue", "golide-gold", "danger-red"}
LAYER_ROLES = {"foreground", "detail", "label", "inset"}
LAYER_POSITIONS = {"top", "center", "bottom", "left", "right"}
LAYER_ENTRANCES = {"fade", "drift-left", "drift-right", "pop"}


@dataclass(frozen=True)
class Layer:
    media: Path
    role: str
    position: str
    scale: float
    entrance: str
    start_offset: float
    duration: float

    @classmethod
    def from_dict(cls, raw: dict[str, Any], base: Path, scene_duration: float) -> "Layer":
        role = str(raw.get("role", "detail"))
        position = str(raw.get("position", "center"))
        entrance = str(raw.get("entrance", "fade"))
        scale = float(raw.get("scale", 0.3))
        start = float(raw.get("start_offset", 0))
        duration = float(raw.get("duration", scene_duration - start))
        if role not in LAYER_ROLES or position not in LAYER_POSITIONS or entrance not in LAYER_ENTRANCES:
            raise ManifestError("unsupported editorial layer recipe")
        if not 0.12 <= scale <= 0.65:
            raise ManifestError("editorial layer scale must be 0.12-0.65")
        if start < 0 or duration <= 0 or start + duration > scene_duration + 0.05:
            raise ManifestError("editorial layer timing must fit inside its narration beat")
        return cls(
            (base / str(raw["media"])).resolve(), role, position,
            scale, entrance, start, duration,
        )


@dataclass(frozen=True)
class Annotation:
    kind: str = "none"
    text: str = ""
    start_offset: float = 0.0
    duration: float = 0.0
    position: str = "center"
    color_token: str = "golide-gold"

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None, scene_duration: float) -> "Annotation":
        raw = raw or {}
        kind = str(raw.get("kind", "none"))
        text = str(raw.get("text", "")).strip()
        start = float(raw.get("start_offset", 0))
        duration = float(raw.get("duration", 0))
        position = str(raw.get("position", "center"))
        color = str(raw.get("color_token", "golide-gold"))
        if kind not in ANNOTATION_KINDS:
            raise ManifestError(f"unsupported annotation kind: {kind}")
        if position not in ANNOTATION_POSITIONS:
            raise ManifestError(f"unsupported annotation position: {position}")
        if color not in COLOR_TOKENS:
            raise ManifestError(f"unsupported annotation color token: {color}")
        if kind == "none":
            return cls()
        if not text:
            raise ManifestError("visible annotation requires text")
        if start < 0 or duration <= 0 or start + duration > scene_duration + 0.05:
            raise ManifestError("annotation timing must fit inside its narration beat")
        return cls(kind, text, start, duration, position, color)


@dataclass(frozen=True)
class Motion:
    type: str = "hold"
    intensity: str = "subtle"
    transition: str = "cut"
    easing: str = "ease-in-out"
    emphasis: str = ""
    audio_cue: str = "none"

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "Motion":
        raw = raw or {}
        values = {
            "type": str(raw.get("type", "hold")),
            "intensity": str(raw.get("intensity", "subtle")),
            "transition": str(raw.get("transition", "cut")),
            "easing": str(raw.get("easing", "ease-in-out")),
            "emphasis": str(raw.get("emphasis", "")).strip(),
            "audio_cue": str(raw.get("audio_cue", "none")),
        }
        if values["type"] not in MOTION_TYPES:
            raise ManifestError(f"unsupported motion type: {values['type']}")
        if values["intensity"] not in INTENSITIES:
            raise ManifestError(f"unsupported motion intensity: {values['intensity']}")
        if values["transition"] not in TRANSITIONS:
            raise ManifestError(f"unsupported transition: {values['transition']}")
        if values["easing"] not in EASINGS:
            raise ManifestError(f"unsupported easing: {values['easing']}")
        if values["audio_cue"] not in AUDIO_CUES:
            raise ManifestError(f"unsupported audio cue: {values['audio_cue']}")
        return cls(**values)


@dataclass(frozen=True)
class Scene:
    id: str
    media: Path
    duration: float
    caption: str
    start: float
    end: float
    visual_role: str
    motion: Motion
    annotation: Annotation
    layers: tuple[Layer, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any], base: Path) -> "Scene":
        try:
            duration = float(raw["duration"])
            if duration <= 0:
                raise ValueError
            start = float(raw.get("start", 0))
            end = float(raw.get("end", start + duration))
            if start < 0 or end <= start or abs((end - start) - duration) > 0.08:
                raise ManifestError("scene start/end must match duration")
            motion_raw = raw.get("motion") or {}
            annotation_raw = raw.get("annotation")
            if annotation_raw is None and isinstance(motion_raw, dict):
                annotation_raw = motion_raw.get("annotation")
            return cls(
                id=str(raw["id"]),
                media=(base / str(raw["media"])).resolve(),
                duration=duration,
                caption=str(raw.get("caption", "")).strip(),
                start=start,
                end=end,
                visual_role=str(raw.get("visual_role", "CONTEXT")),
                motion=Motion.from_dict(motion_raw),
                annotation=Annotation.from_dict(annotation_raw, duration),
                layers=tuple(
                    Layer.from_dict(item, base, duration)
                    for item in raw.get("layers", [])
                ),
            )
        except ManifestError:
            raise
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
    music_source: str | None
    music_license: str | None
    music_volume: float
    music_ducking: bool
    spoken_captions: Path | None
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
        audio = raw.get("audio", {})
        captions = raw.get("captions", {})
        music_source = str(audio.get("music_source", "")).strip() or None
        music_license = str(audio.get("music_license", "")).strip() or None
        music_volume = float(audio.get("music_volume", 0.08))
        if not 0 <= music_volume <= 0.25:
            raise ManifestError("audio.music_volume must be between 0 and 0.25")
        if music and (not music_source or not music_license):
            raise ManifestError("music_source and music_license are required when music is used")
        spoken_captions = captions.get("spoken_srt")
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
            music_source=music_source,
            music_license=music_license,
            music_volume=music_volume,
            music_ducking=bool(audio.get("duck_under_voice", True)),
            spoken_captions=(base / str(spoken_captions)).resolve() if spoken_captions else None,
            scenes=scenes,
            approved=bool(raw.get("publish", {}).get("approved", False)),
        )
