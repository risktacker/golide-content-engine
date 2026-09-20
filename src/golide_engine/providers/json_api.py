from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ApiResponse:
    status: int
    data: dict[str, Any]
    headers: dict[str, str]


class JsonApiClient(Protocol):
    def get(
        self,
        url: str,
        *,
        bearer_token: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> ApiResponse: ...

    def post(
        self,
        url: str,
        *,
        bearer_token: str,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> ApiResponse: ...


class UrlLibJsonApiClient:
    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout_seconds = timeout_seconds

    def get(
        self,
        url: str,
        *,
        bearer_token: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> ApiResponse:
        if params:
            query = urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None}
            )
            url = f"{url}{'&' if '?' in url else '?'}{query}"
        request = urllib.request.Request(
            url,
            method="GET",
            headers={"Authorization": f"Bearer {bearer_token}", **(headers or {})},
        )
        return self._send(request)

    def post(
        self,
        url: str,
        *,
        bearer_token: str,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> ApiResponse:
        request_headers = {
            "Authorization": f"Bearer {bearer_token}",
            **(headers or {}),
        }
        data = None
        if json_body is not None:
            request_headers["Content-Type"] = "application/json"
            data = json.dumps(json_body).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers=request_headers,
        )
        return self._send(request)

    def _send(self, request: urllib.request.Request) -> ApiResponse:
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
