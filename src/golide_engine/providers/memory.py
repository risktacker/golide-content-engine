from __future__ import annotations

from .base import PublishRequest, PublishResult


class MemoryProvider:
    """Deterministic test adapter. It never contacts a real social network."""

    def __init__(self, platform: str):
        self.platform = platform.strip().lower()
        self.requests: list[PublishRequest] = []

    def publish(self, request: PublishRequest) -> PublishResult:
        if request.platform != self.platform:
            raise ValueError(f"provider {self.platform} cannot publish {request.platform}")
        self.requests.append(request)
        content_id = f"{self.platform}-{len(self.requests)}"
        return PublishResult(
            content_id=content_id,
            url=f"https://example.invalid/{self.platform}/{content_id}",
        )
