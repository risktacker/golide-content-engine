from __future__ import annotations

import json
import os
from pathlib import Path

from .elevenlabs import ElevenLabsVoiceProvider
from .openai_media import OpenAICaptionProvider, OpenAIImageProvider
from .openai_text import OpenAITextProvider


class ProviderRegistry:
    def __init__(self, config_path: str | Path = "config/providers.json"):
        self.config = json.loads(Path(config_path).read_text(encoding="utf-8"))

    def _require_live(self) -> None:
        if self.config.get("dry_run_by_default", True) and os.getenv("GOLIDE_ENABLE_PAID_PRODUCTION") != "1":
            raise RuntimeError("paid providers are locked; set GOLIDE_ENABLE_PAID_PRODUCTION=1 only for an approved release")

    def text(self, *, live: bool = False) -> OpenAITextProvider:
        if live:
            self._require_live()
        cfg = self.config["text"]
        return OpenAITextProvider(cfg["model"], cfg["reasoning_effort"])

    def images(self, *, live: bool = False) -> OpenAIImageProvider:
        if live:
            self._require_live()
        cfg = self.config["assets"]
        return OpenAIImageProvider(cfg["model"], cfg["quality"])

    def voice(self, *, live: bool = False) -> ElevenLabsVoiceProvider:
        if live:
            self._require_live()
        cfg = self.config["voice"]
        if cfg.get("provider") != "elevenlabs":
            raise RuntimeError("production narration provider must be elevenlabs")
        return ElevenLabsVoiceProvider(
            model=cfg["model"],
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", cfg["voice_id"]),
            output_format=cfg.get("output_format", "mp3_44100_128"),
            voice_settings=cfg.get("settings", {}),
            max_characters_per_request=cfg.get("max_characters_per_request", 10_000),
            monthly_character_limit=cfg.get("monthly_character_limit", 27_000),
        )

    def captions(self, *, live: bool = False) -> OpenAICaptionProvider:
        cfg = self.config["captions"]
        if cfg.get("provider") == "elevenlabs-alignment":
            raise RuntimeError("captions are supplied by ElevenLabs narration alignment; transcription is disabled")
        if live:
            self._require_live()
        return OpenAICaptionProvider(cfg["model"])

    def thumbnails(self, *, live: bool = False) -> OpenAIImageProvider:
        if live:
            self._require_live()
        cfg = self.config["thumbnail"]
        return OpenAIImageProvider(cfg["model"], cfg["quality"])
