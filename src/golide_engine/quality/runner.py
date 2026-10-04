from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .audio import check_audio, measure_loudness
from .editorial import check_editorial
from .spelling import check_spelling
from .visual import check_safe_zones, check_thumbnail, check_video


@dataclass(frozen=True)
class QualityReport:
    passed: bool
    failures: tuple[str, ...]
    audio: dict[str, float]
    editorial: dict[str, float | int]
    checked_at: str


class QualityRunner:
    def __init__(self, policy_path: str | Path):
        self.policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))

    def run(self, video: Path, format_name: str, storyboard: dict, texts: list[str], output: Path | None = None, thumbnail: Path | None = None, editorial: bool = True) -> QualityReport:
        failures = check_audio(video, self.policy)
        failures.extend(check_video(video, format_name, self.policy))
        if editorial:
            # Still-image storyboards only; vector videos are built from a fixed,
            # pre-tested visual vocabulary and have no assets or safe-zone boxes.
            failures.extend(check_safe_zones(storyboard, self.policy))
            editorial_failures, editorial_metrics = check_editorial(storyboard, format_name, self.policy)
            failures.extend(editorial_failures)
        else:
            editorial_metrics = {"beats": len(storyboard.get("scenes", [])), "renderer": "vector"}
        if thumbnail:
            failures.extend(check_thumbnail(thumbnail))
        failures.extend(check_spelling(texts, self.policy))
        report = QualityReport(
            not failures,
            tuple(failures),
            measure_loudness(video),
            editorial_metrics,
            datetime.now(timezone.utc).isoformat(),
        )
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")
        return report
