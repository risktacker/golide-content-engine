from __future__ import annotations

import os

from .base import SocialProvider
from .linkedin import LinkedInProvider
from .meta import FacebookPageProvider, InstagramProvider
from .x import XProvider


def providers_from_environment() -> list[SocialProvider]:
    """Create only providers whose required environment settings are complete."""
    providers: list[SocialProvider] = []

    meta_version = os.getenv("GOLIDE_META_API_VERSION", "").strip()
    meta_page_token = os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
    if meta_version and meta_page_token:
        ig_user_id = os.getenv("GOLIDE_INSTAGRAM_USER_ID", "").strip()
        if ig_user_id:
            providers.append(
                InstagramProvider(
                    api_version=meta_version,
                    access_token=meta_page_token,
                    instagram_user_id=ig_user_id,
                )
            )

        page_id = os.getenv("GOLIDE_FACEBOOK_PAGE_ID", "").strip()
        if page_id:
            providers.append(
                FacebookPageProvider(
                    api_version=meta_version,
                    page_access_token=meta_page_token,
                    page_id=page_id,
                )
            )

    linkedin_token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
    linkedin_author = os.getenv("GOLIDE_LINKEDIN_AUTHOR_URN", "").strip()
    linkedin_version = os.getenv("GOLIDE_LINKEDIN_VERSION", "").strip()
    if linkedin_token and linkedin_author and linkedin_version:
        providers.append(
            LinkedInProvider(
                access_token=linkedin_token,
                author_urn=linkedin_author,
                linkedin_version=linkedin_version,
            )
        )

    x_token = os.getenv("X_USER_ACCESS_TOKEN", "").strip()
    if x_token:
        providers.append(XProvider(user_access_token=x_token))

    return providers
