from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderOutput:
    value: Any
    request_id: str | None = None
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    details: dict[str, Any] | None = None


class ResearchProvider(Protocol):
    def research(self, brief: str) -> ProviderOutput: ...


class ScriptProvider(Protocol):
    def write_script(self, brief: str, research_packet: str) -> ProviderOutput: ...


class AssetProvider(Protocol):
    def create_image(self, prompt: str, output: Path, size: str, reference_images: list[Path] | None = None) -> ProviderOutput: ...


class VoiceProvider(Protocol):
    def synthesize(self, script: str, output: Path) -> ProviderOutput: ...


class CaptionProvider(Protocol):
    def transcribe_words(self, audio: Path) -> ProviderOutput: ...


class ThumbnailProvider(Protocol):
    def create_thumbnail(self, prompt: str, output: Path, size: str, reference_images: list[Path] | None = None) -> ProviderOutput: ...


@dataclass(frozen=True)
class PublishRequest:
    post_id: str
    variant_id: str
    platform: str
    body: str
    title: str = ""
    media_ref: str | None = None
    parts: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublishResult:
    content_id: str
    url: str | None = None


class SocialProvider(Protocol):
    platform: str

    def publish(self, request: PublishRequest) -> PublishResult:
        """Publish one normalized platform variant and return its remote identity."""
        ...
