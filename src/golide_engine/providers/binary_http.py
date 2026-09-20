from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BinaryResponse:
    status: int
    data: bytes
    headers: dict[str, str]


@dataclass(frozen=True)
class MediaProbe:
    size_bytes: int
    content_type: str


class BinaryHttpClient(Protocol):
    def get(self, url: str, *, headers: dict[str, str] | None = None) -> BinaryResponse: ...
    def put(
        self,
        url: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
        headers: dict[str, str] | None = None,
    ) -> BinaryResponse: ...


class UrlLibBinaryHttpClient:
    def __init__(self, timeout_seconds: float = 90.0):
        self.timeout_seconds = timeout_seconds

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> BinaryResponse:
        return self._send("GET", url, headers=headers)

    def put(
        self,
        url: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
        headers: dict[str, str] | None = None,
    ) -> BinaryResponse:
        merged = {"Content-Type": content_type, **(headers or {})}
        return self._send("PUT", url, data=data, headers=merged)

    def _send(
        self,
        method: str,
        url: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> BinaryResponse:
        request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return BinaryResponse(
                    status=response.status,
                    data=response.read(),
                    headers={k.lower(): v for k, v in response.headers.items()},
                )
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"binary media request failed: {exc.code} {body[:500]}") from exc


def probe_media(http: BinaryHttpClient, url: str) -> MediaProbe:
    response = http.get(url, headers={"Range": "bytes=0-0"})
    content_type = response.headers.get("content-type", "application/octet-stream").split(";", 1)[0]
    content_range = response.headers.get("content-range", "")
    if "/" in content_range:
        size_text = content_range.rsplit("/", 1)[-1]
        if size_text.isdigit():
            return MediaProbe(size_bytes=int(size_text), content_type=content_type)
    content_length = response.headers.get("content-length", "")
    if response.status == 200 and content_length.isdigit():
        return MediaProbe(size_bytes=int(content_length), content_type=content_type)
    if response.status == 200:
        return MediaProbe(size_bytes=len(response.data), content_type=content_type)
    raise RuntimeError("media source did not provide a usable size")


def read_range(http: BinaryHttpClient, url: str, first: int, last: int) -> bytes:
    if first < 0 or last < first:
        raise ValueError("invalid media byte range")
    response = http.get(url, headers={"Range": f"bytes={first}-{last}"})
    expected = last - first + 1
    if len(response.data) != expected:
        raise RuntimeError(
            f"media range length mismatch: expected {expected}, got {len(response.data)}"
        )
    return response.data
