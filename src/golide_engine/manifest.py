import json
from pathlib import Path

from .models import Project


def load_project(path: str | Path) -> Project:
    manifest = Path(path).resolve()
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    return Project.from_dict(raw, manifest.parent)


def validate_assets(project: Project) -> list[str]:
    missing = []
    if not project.narration.exists():
        missing.append(str(project.narration))
    if project.music and not project.music.exists():
        missing.append(str(project.music))
    if project.spoken_captions and not project.spoken_captions.exists():
        missing.append(str(project.spoken_captions))
    missing.extend(str(scene.media) for scene in project.scenes if not scene.media.exists())
    return missing
