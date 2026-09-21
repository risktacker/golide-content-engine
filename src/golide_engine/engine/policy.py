from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .content import ContentClass, ContentValidationError, PlatformVariant


_FORBIDDEN_DASHES = ("—", "–")
_ALLOWED_LANES = {"awareness", "authority", "proof", "story", "conversion", "education", "flexible"}


class ContentPolicy:
    """Machine-enforced version of the locked GOLIDE operating manual."""

    def __init__(self, root: str | Path = "."):
        root = Path(root)
        self.routing = json.loads((root / "config/content-routing.json").read_text(encoding="utf-8"))
        self.calendar = json.loads((root / "config/content-calendar.json").read_text(encoding="utf-8"))
        self.social_image = json.loads((root / "config/social-image-profile.json").read_text(encoding="utf-8"))
        self.video = json.loads((root / "config/video-profile.json").read_text(encoding="utf-8"))

    def expected_platforms(self, content_class: ContentClass | str) -> tuple[str, ...]:
        value = content_class if isinstance(content_class, ContentClass) else ContentClass(str(content_class))
        key = "long_video" if value is ContentClass.LONG else value.value
        return tuple(self.routing["content_types"][key]["platforms"])

    def validate_route(
        self,
        content_class: ContentClass | str,
        platforms: Iterable[str],
        *,
        require_complete: bool = True,
    ) -> None:
        value = content_class if isinstance(content_class, ContentClass) else ContentClass(str(content_class))
        actual = tuple(str(item).strip().lower() for item in platforms)
        expected = self.expected_platforms(value)
        unsupported = sorted(set(actual) - set(expected))
        if unsupported:
            raise ContentValidationError(
                f"{value.value} cannot route to: {', '.join(unsupported)}"
            )
        if require_complete and set(actual) != set(expected):
            missing = sorted(set(expected) - set(actual))
            raise ContentValidationError(
                f"{value.value} route is locked; missing platforms: {', '.join(missing)}"
            )

    def validate_post_structure(
        self,
        value_units: Iterable[str],
        product_bridge_position: int | None,
        product_url: str,
    ) -> tuple[str, ...]:
        units = tuple(str(item).strip() for item in value_units if str(item).strip())
        if not 3 <= len(units) <= 4:
            raise ContentValidationError("static posts require 3 to 4 related value units")
        self._reject_extended_dashes(units)
        if product_bridge_position is not None:
            if product_bridge_position not in {2, 3}:
                raise ContentValidationError("product bridge must be at value unit 2 or 3")
            if product_bridge_position > len(units):
                raise ContentValidationError("product bridge position exceeds the value-unit count")
            if not str(product_url).strip().startswith("https://"):
                raise ContentValidationError("a product bridge requires an HTTPS product URL")
        return units

    def validate_lane(self, lane: str) -> None:
        if lane and lane.strip().lower() not in _ALLOWED_LANES:
            raise ContentValidationError(f"unsupported content lane: {lane}")

    def validate_variant_copy(self, variants: Iterable[PlatformVariant]) -> None:
        values: list[str] = []
        for variant in variants:
            values.append(variant.body)
            values.extend(variant.parts)
        self._reject_extended_dashes(values)

    def validate_ready_for_schedule(self, draft) -> None:
        self.validate_route(draft.content_class, (item.platform for item in draft.variants))
        self.validate_lane(draft.content_lane)
        self.validate_variant_copy(draft.variants)
        if not draft.release_approved:
            raise ContentValidationError("release approval is required before scheduling")

        if draft.content_class is ContentClass.POST:
            self.validate_post_structure(
                draft.value_units,
                draft.product_bridge_position,
                draft.product_url,
            )
            if not draft.media_approved:
                raise ContentValidationError("static image approval is required before scheduling")
            if any(not item.media_ref for item in draft.variants):
                raise ContentValidationError("every static platform variant requires approved media")
        else:
            if not draft.qa_approved:
                raise ContentValidationError("video QA approval is required before scheduling")
            if not draft.owner_voice_media_ref:
                raise ContentValidationError("owner-recorded voice is required before scheduling video")
            if any(not item.media_ref for item in draft.variants):
                raise ContentValidationError("every video route requires a final approved video media reference")

        if draft.content_class is ContentClass.LONG and self.expected_platforms(draft.content_class) != ("youtube",):
            raise ContentValidationError("long-form video is locked to YouTube only")

    @staticmethod
    def _reject_extended_dashes(values: Iterable[str]) -> None:
        for value in values:
            if any(mark in str(value) for mark in _FORBIDDEN_DASHES):
                raise ContentValidationError("extended dash typography is not allowed; use a normal hyphen or comma")

    def snapshot(self) -> dict:
        return {
            "routing": self.routing,
            "calendar": self.calendar,
            "social_image": self.social_image,
            "video": self.video,
        }
