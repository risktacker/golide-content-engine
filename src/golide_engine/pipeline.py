from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .scoring import score_concept


@dataclass(frozen=True)
class PipelinePlan:
    project_id: str
    format: str
    score: float
    verdict: str
    stages: tuple[str, ...]
    output_directory: str


STAGES = (
    "research", "concept_scoring", "script", "voice", "captions",
    "editorial_beats", "storyboard", "assets", "render", "thumbnail",
    "automated_qa", "release_package", "private_upload", "schedule",
)


def build_plan(spec: dict[str, Any], output_root: Path) -> PipelinePlan:
    concept = spec["concept"]
    result = score_concept(spec["format"], concept["scores"])
    if result.verdict == "reject":
        raise ValueError("concept failed scoring gate: " + "; ".join(result.blockers or (str(result.total),)))
    destination = output_root / spec["id"]
    destination.mkdir(parents=True, exist_ok=True)
    plan = PipelinePlan(spec["id"], spec["format"], result.total, result.verdict, STAGES, str(destination))
    (destination / "plan.json").write_text(json.dumps(asdict(plan), indent=2) + "\n", encoding="utf-8")
    for folder in STAGES:
        (destination / folder).mkdir(exist_ok=True)
    return plan
