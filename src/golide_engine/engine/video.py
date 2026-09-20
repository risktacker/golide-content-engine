from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WordTiming:
    word: str
    start: float
    end: float


@dataclass(frozen=True)
class VisualBeat:
    start: float
    end: float
    motion: str
    meaning: str
    anchor_word: str = ""


class VideoProfile:
    def __init__(self, raw: dict):
        self.raw = raw

    @classmethod
    def load(cls, path: str | Path = "config/video-profile.json") -> "VideoProfile":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def validate(self) -> None:
        voice = self.raw["voice"]
        render = self.raw["render"]
        motion = self.raw["motion"]
        if voice.get("source") != "owner_recording_only":
            raise ValueError("video profile must use the owner's recorded voice")
        if voice.get("ai_voice_allowed") or voice.get("cloned_voice_allowed"):
            raise ValueError("AI/cloned voice is not allowed")
        if not voice.get("audio_is_master_timeline"):
            raise ValueError("audio must be the master timeline")
        if render.get("intermediate_video_files"):
            raise ValueError("intermediate video files are forbidden")
        if render.get("final_render_count") != 1:
            raise ValueError("exactly one final render is allowed")
        beat = motion.get("micro_beat_seconds", {})
        if beat.get("min") != 0.5 or beat.get("max") != 1.0:
            raise ValueError("locked micro-beat range must remain 0.5-1.0 seconds")

    @property
    def allowed_motions(self) -> set[str]:
        return set(self.raw["motion"]["allowed"])


def validate_timeline(profile: VideoProfile, words: list[WordTiming], beats: list[VisualBeat]) -> None:
    """Reject edit plans that drift from the locked reference-video grammar."""
    profile.validate()
    allowed = profile.allowed_motions
    last_end = 0.0
    for beat in beats:
        if beat.motion not in allowed:
            raise ValueError(f"unsupported locked motion: {beat.motion}")
        if beat.start < 0 or beat.end <= beat.start:
            raise ValueError("invalid visual beat timing")
        if beat.start < last_end - 0.001:
            raise ValueError("visual beats must be ordered")
        last_end = beat.end
        if beat.anchor_word:
            matching = [word for word in words if word.word.lower() == beat.anchor_word.lower()]
            if not matching:
                raise ValueError(f"anchor word not found: {beat.anchor_word}")
            nearest = min(matching, key=lambda word: abs(word.start - beat.start))
            if abs(nearest.start - beat.start) > 0.35:
                raise ValueError("visual beat is not synchronized closely enough to its spoken anchor")
