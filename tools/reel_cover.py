"""Make and email the reel cover for one long video that is already uploaded.

New long videos get theirs automatically after upload (cli automation-run). This is for
a video uploaded before that existed:  python tools/reel_cover.py golide-long-2026-10-31
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golide_engine.operations.reel_cover import make_reel_cover  # noqa: E402
from golide_engine.providers.registry import ProviderRegistry  # noqa: E402


def main(production_id: str) -> None:
    record = json.loads((ROOT / "data/production-records" / f"{production_id}.json").read_text(encoding="utf-8"))
    spec_path = ROOT / "production-queue" / f"{production_id}.completed.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8")) if spec_path.exists() else {}
    metadata = record.get("metadata") or {}
    result = make_reel_cover(
        production_id=production_id,
        title=str(metadata.get("title") or (record.get("production") or {}).get("title") or spec.get("title", "")),
        story=str(spec.get("brief") or metadata.get("description", "")),
        youtube_video_id=str(record.get("youtube_video_id", "")),
        source_url=str((spec.get("source_breakout") or {}).get("url", "")),
        providers=ProviderRegistry(ROOT / "config" / "providers.json"),
        out_dir=ROOT / "reel-covers",
    )
    print(json.dumps(result))
    if result["status"] != "sent":
        raise SystemExit("cover made but the email did not go out")


if __name__ == "__main__":
    main(sys.argv[1])
