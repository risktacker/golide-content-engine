from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class VisualIdentity:
    def __init__(self, config_path: str | Path):
        self.path = Path(config_path)
        self.config: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
        if self.config.get("locked") is not True:
            raise RuntimeError("G$LIDE visual identity must remain locked for production")

    @property
    def avatar(self) -> dict[str, Any]:
        return dict(self.config["avatar"])

    def prompt_guard(self) -> str:
        avatar = self.avatar
        required = "; ".join(avatar["required_traits"])
        forbidden = "; ".join(avatar["forbidden_traits"])
        palette = ", ".join(self.config["palette"])
        return (
            "LOCKED G$LIDE VISUAL IDENTITY. "
            f"Palette: {palette}. "
            "Maintain a premium layered paper-cut/technical-explainer aesthetic. "
            "If the image contains the G$LIDE Esiah avatar or any representation of Esiah, "
            f"the canonical avatar direction is mandatory: {avatar['canonical_direction']} "
            f"Required avatar traits: {required}. "
            f"Forbidden avatar traits: {forbidden}. "
            f"Thumbnail rule: {avatar['thumbnail_rule']} "
            f"In-video rule: {avatar['in_video_rule']} "
            "Do not reinterpret the avatar as a cartoon, mascot, anime figure or animated-film character."
        )

    def apply(self, prompt: str) -> str:
        return self.prompt_guard() + "\n\nSCENE REQUEST:\n" + prompt.strip()
