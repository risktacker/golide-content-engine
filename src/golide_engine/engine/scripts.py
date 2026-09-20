from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .research import TopicCandidate


class VideoFormat(StrEnum):
    VERTICAL = "9:16"
    HORIZONTAL = "16:9"


@dataclass(frozen=True)
class ScriptBrief:
    niche: str
    topic: TopicCandidate
    format: VideoFormat
    goal: str
    duration_seconds: int
    cta: str = ""

    def validate(self) -> None:
        if not self.niche.strip():
            raise ValueError("niche is required")
        if self.duration_seconds <= 0:
            raise ValueError("duration must be positive")
        if self.format is VideoFormat.VERTICAL and self.duration_seconds > 180:
            raise ValueError("9:16 scripts must stay short-form")
        if self.format is VideoFormat.HORIZONTAL and self.duration_seconds < 60:
            raise ValueError("16:9 scripts must be long-form")


@dataclass(frozen=True)
class ScriptPackage:
    title: str
    hook: str
    script: str
    cta: str
    visual_notes: tuple[str, ...]
    format: str
    duration_seconds: int


def build_script_instruction(brief: ScriptBrief) -> str:
    """Provider-agnostic instruction for the AI adapter."""
    brief.validate()
    evidence = brief.topic.evidence.strip()
    if brief.format is VideoFormat.VERTICAL:
        structure = (
            "Write for 9:16 short-form video. Hook in the first second. "
            "Use dense spoken value, fast payoff, short natural sentences, "
            "and a short CTA only when relevant. Do not pad a long-form script."
        )
    else:
        structure = (
            "Write for 16:9 long-form video. Use a cold open, clear promise, "
            "logical sections, evidence/examples, payoff, conclusion, and CTA. "
            "Do not write a stretched short."
        )
    return (
        f"Niche: {brief.niche.strip()}\n"
        f"Topic: {brief.topic.topic.strip()}\n"
        f"Goal: {brief.goal.strip()}\n"
        f"Target duration: {brief.duration_seconds} seconds\n"
        f"Evidence: {evidence}\n"
        f"CTA: {brief.cta.strip()}\n\n"
        f"{structure}\n"
        "Return a title, hook, exact spoken script for the owner to record, "
        "brief visual notes, and CTA. Never invent a trend claim not supported "
        "by the supplied evidence."
    )
