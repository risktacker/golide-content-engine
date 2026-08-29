from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_FILES = ("video", "thumbnail", "metadata", "spoken_captions", "visual_captions", "source_ledger", "generation_parameters", "qa_report")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class ReleasePackager:
    def __init__(self, output_root: str | Path = "release-packages"):
        self.output_root = Path(output_root)

    def build(self, production_id: str, files: dict[str, str | Path], release: dict[str, Any], cost_summary: dict[str, Any]) -> Path:
        missing_keys = sorted(set(REQUIRED_FILES) - set(files))
        if missing_keys:
            raise RuntimeError(f"release files missing: {missing_keys}")
        if not release.get("approved"):
            raise RuntimeError("release must be approved before packaging")
        qa = json.loads(Path(files["qa_report"]).read_text(encoding="utf-8"))
        if qa.get("passed") is not True:
            raise RuntimeError("QA report has not passed")
        destination = self.output_root / production_id
        if destination.exists():
            failures = self.verify(destination) if (destination / "package-manifest.json").exists() else ["manifest missing"]
            archive = destination.with_suffix(".zip")
            if not failures and archive.exists():
                return archive
            raise FileExistsError(f"release package already exists but is incomplete: {destination}; {failures}")
        destination.mkdir(parents=True)
        manifest_files = {}
        for role in REQUIRED_FILES:
            source = Path(files[role])
            if not source.is_file():
                raise FileNotFoundError(source)
            target = destination / source.name
            shutil.copy2(source, target)
            manifest_files[role] = {"file": target.name, "sha256": sha256(target), "bytes": target.stat().st_size}
        (destination / "cost-summary.json").write_text(json.dumps(cost_summary, indent=2) + "\n", encoding="utf-8")
        package_manifest = {
            "version": 1, "production_id": production_id, "created_at": datetime.now(timezone.utc).isoformat(),
            "release": release, "files": manifest_files, "cost_summary": "cost-summary.json",
        }
        (destination / "package-manifest.json").write_text(json.dumps(package_manifest, indent=2) + "\n", encoding="utf-8")
        archive = shutil.make_archive(str(destination), "zip", root_dir=destination)
        return Path(archive)

    @staticmethod
    def verify(package_directory: str | Path) -> list[str]:
        root = Path(package_directory)
        manifest = json.loads((root / "package-manifest.json").read_text(encoding="utf-8"))
        failures = []
        for role, item in manifest["files"].items():
            path = root / item["file"]
            if not path.exists():
                failures.append(f"{role}: missing {item['file']}")
            elif sha256(path) != item["sha256"]:
                failures.append(f"{role}: checksum mismatch")
        return failures
