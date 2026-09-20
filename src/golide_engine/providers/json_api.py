from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ApiResponse:
    status: int
    data: dict[str, Any]
    headers: dict[str, str]


class JsonApiClient(Protocol):
    def post(
        self,
        url: str,
        *,
        bearer_token: str,
        json_body: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> ApiResponse:
        ...


class UrlLibJsonApiClient:
    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout_seconds = timeout_seconds

    def post(
        self,
        url: str,
        *,
        bearer_token: str,
        json_body: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> ApiResponse:
        request_headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            **(headers or {}),
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(json_body).encode("utf-8"),
            method="POST",
            headers=request_headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                payload = json.loads(raw) if raw else {}
                return ApiResponse(
                    status=response.status,
                    data=payload,
                    headers={key.lower(): value for key, value in response.headers.items()},
                )
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"message": raw or str(exc)}
            message = (
                payload.get("message")
                or payload.get("detail")
                or payload.get("title")
                or str(exc)
            )
            raise RuntimeError(f"social API request failed: {message}") from exc
