from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from .providers.json_api import UrlLibJsonApiClient
from .providers.meta import discover_instagram_identity
from .youtube.auth import assert_channel, credentials, services

YOUTUBE_CHANNEL_ID = "UCqaXVBSBz7iQsRHOupKt-3w"
SUPPORTED_PROVIDERS = ("instagram", "facebook", "linkedin", "youtube")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _result(platform: str, *, connected: bool, status: str, label: str, external_id: str = "", note: str = "") -> dict[str, Any]:
    return {
        "platform": platform,
        "connected": connected,
        "status": status,
        "accountLabel": label,
        "externalAccountId": external_id,
        "verifiedAt": _now(),
        "verificationNote": note,
    }


def _missing(platform: str, label: str, names: list[str]) -> dict[str, Any]:
    return _result(platform, connected=False, status="needs_attention", label=label, note="Missing required execution credential configuration: " + ", ".join(names))


def _failed(platform: str, label: str, external_id: str = "") -> dict[str, Any]:
    return _result(platform, connected=False, status="connection_failed", label=label, external_id=external_id, note="Credential verification failed. Reconnect or replace the provider credential.")


def verify_instagram() -> dict[str, Any]:
    version = os.getenv("GOLIDE_META_API_VERSION", "").strip()
    token = os.getenv("INSTAGRAM_USER_ACCESS_TOKEN", "").strip()
    missing = [name for name, value in (("GOLIDE_META_API_VERSION", version), ("INSTAGRAM_USER_ACCESS_TOKEN", token)) if not value]
    if missing:
        return _missing("instagram", "Instagram", missing)
    try:
        identity = discover_instagram_identity(api_version=version, instagram_access_token=token)
    except Exception:
        return _failed("instagram", "Instagram")
    return _result("instagram", connected=True, status="connected", label=f"@{identity.username}" if identity.username else "Instagram", external_id=identity.id, note="Instagram identity verified.")


def verify_facebook() -> dict[str, Any]:
    version = os.getenv("GOLIDE_META_API_VERSION", "").strip()
    token = os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
    page_id = os.getenv("GOLIDE_FACEBOOK_PAGE_ID", "").strip()
    missing = [name for name, value in (("GOLIDE_META_API_VERSION", version), ("META_PAGE_ACCESS_TOKEN", token), ("GOLIDE_FACEBOOK_PAGE_ID", page_id)) if not value]
    if missing:
        return _missing("facebook", "Facebook Page", missing)
    params = urllib.parse.urlencode({"fields": "id,name", "access_token": token})
    try:
        with urllib.request.urlopen(f"https://graph.facebook.com/{version}/{page_id}?{params}", timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        resolved_id = str(payload.get("id", "")).strip()
        if resolved_id != page_id:
            raise RuntimeError("page identity mismatch")
    except Exception:
        return _failed("facebook", "Facebook Page", page_id)
    return _result("facebook", connected=True, status="connected", label=str(payload.get("name") or "Facebook Page"), external_id=resolved_id, note="Facebook Page identity verified.")


def verify_linkedin() -> dict[str, Any]:
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
    author_urn = os.getenv("GOLIDE_LINKEDIN_AUTHOR_URN", "").strip()
    version = os.getenv("GOLIDE_LINKEDIN_VERSION", "").strip()
    missing = [name for name, value in (("LINKEDIN_ACCESS_TOKEN", token), ("GOLIDE_LINKEDIN_AUTHOR_URN", author_urn), ("GOLIDE_LINKEDIN_VERSION", version)) if not value]
    if missing:
        return _missing("linkedin", "LinkedIn", missing)
    if not re.fullmatch(r"\d{6}", version) or not author_urn.startswith("urn:li:person:"):
        return _result("linkedin", connected=False, status="needs_attention", label="LinkedIn", external_id=author_urn, note="LinkedIn author or API-version configuration needs attention.")
    try:
        response = UrlLibJsonApiClient().get("https://api.linkedin.com/v2/userinfo", bearer_token=token)
        sub = str(response.data.get("sub", "")).strip()
        if not sub or author_urn != f"urn:li:person:{sub}":
            raise RuntimeError("identity mismatch")
        label = str(response.data.get("name") or response.data.get("preferred_username") or "LinkedIn member")
    except Exception:
        return _failed("linkedin", "LinkedIn", author_urn)
    return _result("linkedin", connected=True, status="connected", label=label, external_id=author_urn, note="LinkedIn member identity verified.")


def verify_youtube() -> dict[str, Any]:
    if not os.getenv("YOUTUBE_OAUTH_TOKEN_B64", "").strip():
        return _missing("youtube", "YouTube", ["YOUTUBE_OAUTH_TOKEN_B64"])
    try:
        youtube, _ = services(credentials())
        channel = assert_channel(youtube, YOUTUBE_CHANNEL_ID)
        label = str(channel.get("snippet", {}).get("title") or "YouTube")
    except Exception:
        return _failed("youtube", "YouTube", YOUTUBE_CHANNEL_ID)
    return _result("youtube", connected=True, status="connected", label=label, external_id=YOUTUBE_CHANNEL_ID, note="YouTube channel ownership verified.")


def verify_provider(platform: str) -> dict[str, Any]:
    functions = {"instagram": verify_instagram, "facebook": verify_facebook, "linkedin": verify_linkedin, "youtube": verify_youtube}
    key = platform.strip().lower()
    if key not in functions:
        raise ValueError(f"unsupported provider: {key}")
    return functions[key]()


def verify_all() -> list[dict[str, Any]]:
    return [verify_provider(platform) for platform in SUPPORTED_PROVIDERS]
