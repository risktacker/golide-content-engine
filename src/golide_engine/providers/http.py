from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class JsonResponse:
    status: int
    data: dict[str, Any]


class JsonHttpClient(Protocol):
    def get(self, url: str, *, params: dict[str, Any] | None = None) -> JsonResponse: ...
    def post(self, url: str, *, data: dict[str, Any] | None = None,
             headers: dict[str, str] | None = None) -> JsonResponse: ...


class UrlLibJsonClient:
    """Small stdlib JSON/form client so the distribution core stays lightweight."""

    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout_seconds = timeout_seconds

    def get(self, url: str, *, params: dict[str, Any] | None = None) -> JsonResponse:
        if params:
            query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            url = f"{url}{'&' if '?' in url else '?'}{query}"
        request = urllib.request.Request(url, method="GET")
        return self._send(request)

    def post(
        self,
        url: str,
        *,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> JsonResponse:
        body = urllib.parse.urlencode(
            {k: v for k, v in (data or {}).items() if v is not None}
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded", **(headers or {})},
        )
        return self._send(request)

    def _send(self, request: urllib.request.Request) -> JsonResponse:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                payload = json.loads(raw) if raw else {}
                return JsonResponse(status=response.status, data=payload)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"error": {"message": raw or str(exc)}}
            message = payload.get("error", {}).get("message") or str(exc)
            raise RuntimeError(f"social API request failed: {message}") from exc
