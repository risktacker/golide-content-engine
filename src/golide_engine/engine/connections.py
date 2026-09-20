from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Transport(StrEnum):
    OFFICIAL_API = "official_api"
    SELF_HOSTED = "self_hosted"
    UNIFIED_CONNECTOR = "unified_connector"
    BROWSER_SESSION = "browser_session"
    ASSISTED_SEND = "assisted_send"


@dataclass(frozen=True)
class SocialConnection:
    id: str
    platform: str
    account_label: str
    external_account_id: str
    transport: str
    credential_ref: str
    status: str
