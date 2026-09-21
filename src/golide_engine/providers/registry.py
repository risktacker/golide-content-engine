from __future__ import annotations

import json
import os
from pathlib import Path


class ProviderRegistry:
    def __init__(self, config_path: str | Path = "config/providers.json"):
        self.config = json.loads(Path(config_path).read_text(encoding="utf-8"))

    def _require_live(self) -> None:
        if self.config.get("dry_run_by_default", True) and os.getenv("GOLIDE_ENABLE_PAID_PRODUCTION") != "1":
            raise RuntimeError(
                "paid providers are locked; set GOLIDE_ENABLE_PAID_PRODUCTION=1 only for an approved release"
            )

    def text(self, *, live: bool = False):
        if live:
            self._require_live()
        from .openai_text import OpenAITextProvider
        cfg = self.config["text"]
        return OpenAITextProvider(cfg["model"], cfg["reasoning_effort"])

    def images(self, tier: str = "support", *, live: bool = False):
        if live:
            self._require_live()
        if tier not in {"support", "hero"}:
            raise ValueError("image tier must be support or hero")
        from .openai_media import OpenAIImageProvider
        cfg = self.config["assets"]
        return OpenAIImageProvider(cfg[f"{tier}_model"], cfg[f"{tier}_quality"])

    def voice(self, *, live: bool = False):
        raise RuntimeError(
            "voice synthesis is disabled; GOLIDE video narration must come from the owner's recording"
        )

    def captions(self, *, live: bool = False):
        cfg = self.config["captions"]
        if cfg.get("provider") != "openai-transcription":
            raise RuntimeError("captions must be derived from the owner recording")
        if live:
            self._require_live()
        from .openai_media import OpenAICaptionProvider
        return OpenAICaptionProvider(cfg["model"])

    def thumbnails(self, *, live: bool = False):
        if live:
            self._require_live()
        from .openai_media import OpenAIImageProvider
        cfg = self.config["thumbnail"]
        return OpenAIImageProvider(cfg["model"], cfg["quality"])
