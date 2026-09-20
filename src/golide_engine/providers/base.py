from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PublishRequest:
    post_id: str
    variant_id: str
    platform: str
    body: str
    title: str = ""
    media_ref: str | None = None


@dataclass(frozen=True)
class PublishResult:
    content_id: str
    url: str


class SocialProvider(Protocol):
    platform: str

    def publish(self, request: PublishRequest) -> PublishResult:
        """Publish one normalized platform variant and return its remote identity."""
        ...
