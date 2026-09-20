from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class ContentKind(StrEnum):
    SOCIAL = "social"
    VIDEO = "video"


class ContentValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PlatformVariant:
    platform: str
    body: str
    title: str = ""
    media_ref: str | None = None

    def normalized(self) -> "PlatformVariant":
        platform = self.platform.strip().lower()
        body = self.body.strip()
        title = self.title.strip()
        media_ref = self.media_ref.strip() if self.media_ref else None
        if not platform:
            raise ContentValidationError("platform is required")
        if not body:
            raise ContentValidationError(f"{platform} body is required")
        return PlatformVariant(platform=platform, body=body, title=title, media_ref=media_ref)


@dataclass(frozen=True)
class ContentDraft:
    master_text: str
    variants: tuple[PlatformVariant, ...]
    title: str = ""
    kind: ContentKind = ContentKind.SOCIAL

    @classmethod
    def build(
        cls,
        master_text: str,
        variants: Iterable[PlatformVariant],
        *,
        title: str = "",
        kind: ContentKind | str = ContentKind.SOCIAL,
    ) -> "ContentDraft":
        master = master_text.strip()
        if not master:
            raise ContentValidationError("master content is required")
        normalized = tuple(item.normalized() for item in variants)
        if not normalized:
            raise ContentValidationError("at least one platform variant is required")
        platforms = [item.platform for item in normalized]
        if len(platforms) != len(set(platforms)):
            raise ContentValidationError("only one variant per platform is allowed")
        try:
            content_kind = kind if isinstance(kind, ContentKind) else ContentKind(str(kind))
        except ValueError as exc:
            raise ContentValidationError(f"unsupported content kind: {kind}") from exc
        return cls(master_text=master, variants=normalized, title=title.strip(), kind=content_kind)
