from __future__ import annotations

import base64
import json
import os
from pathlib import Path

SCOPES = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
)


def _imports():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise RuntimeError("install production dependencies: pip install -e '.[production]'") from exc
    return Request, Credentials, InstalledAppFlow


def bootstrap(client_secrets: str | Path, token_path: str | Path = ".secrets/youtube-token.json") -> Path:
    """Open Google's local OAuth consent page; credentials never pass through chat or git."""
    _, _, InstalledAppFlow = _imports()
    token = Path(token_path)
    token.parent.mkdir(parents=True, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
    credentials = flow.run_local_server(host="localhost", port=0, open_browser=True, access_type="offline", prompt="consent")
    token.write_text(credentials.to_json(), encoding="utf-8")
    token.chmod(0o600)
    return token


def credentials(token_path: str | Path = ".secrets/youtube-token.json"):
    Request, Credentials, _ = _imports()
    encoded = os.getenv("YOUTUBE_OAUTH_TOKEN_B64")
    raw = base64.b64decode(encoded).decode() if encoded else Path(token_path).read_text(encoding="utf-8")
    info = json.loads(raw)
    creds = Credentials.from_authorized_user_info(info, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        if not encoded:
            path = Path(token_path)
            path.write_text(creds.to_json(), encoding="utf-8")
            path.chmod(0o600)
    if not creds.valid:
        raise RuntimeError("YouTube OAuth token is invalid; run oauth-bootstrap again")
    return creds


def services(creds=None):
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError("install production dependencies: pip install -e '.[production]'") from exc
    creds = creds or credentials()
    return build("youtube", "v3", credentials=creds, cache_discovery=False), build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)


def assert_channel(youtube, expected_channel_id: str) -> dict:
    response = youtube.channels().list(part="id,snippet", mine=True).execute()
    items = response.get("items", [])
    if len(items) != 1 or items[0]["id"] != expected_channel_id:
        found = [item.get("id") for item in items]
        raise RuntimeError(f"OAuth account does not own expected channel {expected_channel_id}; found={found}")
    return items[0]
