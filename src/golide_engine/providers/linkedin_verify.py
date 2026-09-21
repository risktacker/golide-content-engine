from __future__ import annotations

import json
import os
import re

from .json_api import UrlLibJsonApiClient


def main() -> None:
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
    author_urn = os.getenv("GOLIDE_LINKEDIN_AUTHOR_URN", "").strip()
    linkedin_version = os.getenv("GOLIDE_LINKEDIN_VERSION", "").strip()

    if not access_token:
        raise RuntimeError("LINKEDIN_ACCESS_TOKEN is required")
    if not author_urn:
        raise RuntimeError("GOLIDE_LINKEDIN_AUTHOR_URN is required")
    if not re.fullmatch(r"\d{6}", linkedin_version):
        raise RuntimeError("GOLIDE_LINKEDIN_VERSION must use YYYYMM format")
    if not author_urn.startswith("urn:li:person:"):
        raise RuntimeError("current LinkedIn connection must use a member Person URN")

    response = UrlLibJsonApiClient().get(
        "https://api.linkedin.com/v2/userinfo",
        bearer_token=access_token,
    )
    sub = str(response.data.get("sub", "")).strip()
    if not sub:
        raise RuntimeError("LinkedIn userinfo did not return a subject id")

    expected = f"urn:li:person:{sub}"
    if author_urn != expected:
        raise RuntimeError("LinkedIn token identity does not match GOLIDE_LINKEDIN_AUTHOR_URN")

    print(json.dumps({
        "status": "connected",
        "author_type": "person",
        "author_urn_matches_token": True,
        "linkedin_version": linkedin_version,
    }, indent=2))


if __name__ == "__main__":
    main()
