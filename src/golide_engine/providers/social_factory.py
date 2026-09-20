from __future__ import annotations

import os

from .base import SocialProvider
from .meta import FacebookPageProvider, InstagramProvider


def providers_from_environment() -> list[SocialProvider]:
    """Create only providers whose required environment settings are complete."""
    api_version = os.getenv("GOLIDE_META_API_VERSION", "").strip()
    page_token = os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
    providers: list[SocialProvider] = []

    if api_version and page_token:
        ig_user_id = os.getenv("GOLIDE_INSTAGRAM_USER_ID", "").strip()
        if ig_user_id:
            providers.append(
                InstagramProvider(
                    api_version=api_version,
                    access_token=page_token,
                    instagram_user_id=ig_user_id,
                )
            )

        page_id = os.getenv("GOLIDE_FACEBOOK_PAGE_ID", "").strip()
        if page_id:
            providers.append(
                FacebookPageProvider(
                    api_version=api_version,
                    page_access_token=page_token,
                    page_id=page_id,
                )
            )

    return providers
