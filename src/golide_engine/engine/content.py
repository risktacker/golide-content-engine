from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class ContentKind(StrEnum):
    """Legacy storage family kept for database compatibility."""
    SOCIAL = "social"
    VIDEO = "video"


class ContentClass(StrEnum):
    POST = "post"
    SHORT = "short"
    LONG = "long"

    @property
    def storage_kind(self) -> ContentKind:
        return ContentKind.SOCIAL if self is ContentClass.POST else ContentKind.VIDEO


class ContentValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PlatformVariant:
    platform: str
    body: str
    title: str = ""
    media_ref: str | None = None
    parts: tuple[str, ...] = ()

    def normalized(self) -> "PlatformVariant":
        platform = self.platform.strip().lower()
        body = self.body.strip()
        title = self.title.strip()
        media_ref = self.media_ref.strip() if self.media_ref else None
        parts = tuple(item.strip() for item in self.parts if str(item).strip())
        if not platform:
            raise ContentValidationError("platform is required")
        if not body and not parts:
            raise ContentValidationError(f"{platform} body or parts are required")
        return PlatformVariant(
            platform=platform,
            body=body,
            title=title,
            media_ref=media_ref,
            parts=parts,
        )


@dataclass(frozen=True)
class ContentDraft:
    master_text: str
    variants: tuple[PlatformVariant, ...]
    title: str = ""
    content_class: ContentClass = ContentClass.POST
    weekly_theme: str = ""
    content_lane: str = ""
    value_units: tuple[str, ...] = ()
    product_bridge_position: int | None = None
    product_url: str = ""
    product_mode: str = "brand"
    product_id: str = ""
    owner_voice_media_ref: str | None = None
    media_approved: bool = False
    qa_approved: bool = False
    release_approved: bool = False

    @property
    def kind(self) -> ContentKind:
        return self.content_class.storage_kind

    @classmethod
    def build(
        cls,
        master_text: str,
        variants: Iterable[PlatformVariant],
        *,
        title: str = "",
        content_class: ContentClass | str | None = None,
        kind: ContentKind | str | None = None,
        weekly_theme: str = "",
        content_lane: str = "",
        value_units: Iterable[str] = (),
        product_bridge_position: int | None = None,
        product_url: str = "",
        product_mode: str = "brand",
        product_id: str = "",
        owner_voice_media_ref: str | None = None,
        media_approved: bool = False,
        qa_approved: bool = False,
        release_approved: bool = False,
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

        if content_class is None:
            legacy = str(kind or ContentKind.SOCIAL).lower()
            mapping = {
                "social": ContentClass.POST,
                "post": ContentClass.POST,
                "video": ContentClass.SHORT,
                "short": ContentClass.SHORT,
                "long": ContentClass.LONG,
                "long_video": ContentClass.LONG,
            }
            try:
                resolved_class = mapping[legacy]
            except KeyError as exc:
                raise ContentValidationError(f"unsupported content kind/class: {legacy}") from exc
        else:
            try:
                resolved_class = (
                    content_class
                    if isinstance(content_class, ContentClass)
                    else ContentClass(str(content_class))
                )
            except ValueError as exc:
                raise ContentValidationError(
                    f"unsupported content class: {content_class}"
                ) from exc

        units = tuple(str(item).strip() for item in value_units if str(item).strip())
        owner_ref = owner_voice_media_ref.strip() if owner_voice_media_ref else None
        return cls(
            master_text=master,
            variants=normalized,
            title=title.strip(),
            content_class=resolved_class,
            weekly_theme=weekly_theme.strip(),
            content_lane=content_lane.strip(),
            value_units=units,
            product_bridge_position=product_bridge_position,
            product_url=product_url.strip(),
            product_mode=str(product_mode or "brand").strip().lower(),
            product_id=str(product_id or "").strip(),
            owner_voice_media_ref=owner_ref,
            media_approved=bool(media_approved),
            qa_approved=bool(qa_approved),
            release_approved=bool(release_approved),
        )
