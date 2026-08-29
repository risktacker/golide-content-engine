from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .audio import check_audio, measure_loudness
from .spelling import check_spelling
from .visual import check_safe_zones, check_thumbnail, check_video


@dataclass(frozen=True)
class QualityReport:
    passed: bool
    failures: tuple[str, ...]
    audio: dict[str, float]
    checked_at: str


class QualityRunner:
    def __init__(self, policy_path: str | Path):
        self.policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))

    def run(self, video: Path, format_name: str, storyboard: dict, texts: list[str], output: Path | None = None, thumbnail: Path | None = None) -> QualityReport:
        failures = check_audio(video, self.policy)
        failures.extend(check_video(video, format_name, self.policy))
        failures.extend(check_safe_zones(storyboard, self.policy))
        if thumbnail:
            failures.extend(check_thumbnail(thumbnail))
        failures.extend(check_spelling(texts, self.policy))
        report = QualityReport(not failures, tuple(failures), measure_loudness(video), datetime.now(timezone.utc).isoformat())
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")
        return report
