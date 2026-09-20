from __future__ import annotations

from typing import Protocol


class MediaResolver(Protocol):
    def resolve(self, media_ref: str) -> str: ...


class IdentityMediaResolver:
    def resolve(self, media_ref: str) -> str:
        return media_ref
