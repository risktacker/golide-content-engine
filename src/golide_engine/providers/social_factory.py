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

    # Preferred Instagram path: Instagram Login. It does not require the
    # professional Instagram account to be linked to a Facebook Page.
    instagram_token = os.getenv("INSTAGRAM_USER_ACCESS_TOKEN", "").strip()
    ig_user_id = os.getenv("GOLIDE_INSTAGRAM_USER_ID", "").strip()
    if meta_version and instagram_token and ig_user_id:
        providers.append(
            InstagramProvider(
                api_version=meta_version,
                access_token=instagram_token,
                instagram_user_id=ig_user_id,
                graph_host="graph.instagram.com",
            )
        )

    # Facebook remains independent and uses a Page access token.
    meta_page_token = os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
    page_id = os.getenv("GOLIDE_FACEBOOK_PAGE_ID", "").strip()
    if meta_version and meta_page_token and page_id:
        providers.append(
            FacebookPageProvider(
                api_version=meta_version,
                page_access_token=meta_page_token,
                page_id=page_id,
            )
        )

    # Backward compatibility only: if no direct Instagram Login token exists,
    # the old Facebook-Login/Page-token path can still operate.
    if (
        meta_version
        and not instagram_token
        and meta_page_token
        and ig_user_id
    ):
        providers.append(
            InstagramProvider(
                api_version=meta_version,
                access_token=meta_page_token,
                instagram_user_id=ig_user_id,
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
