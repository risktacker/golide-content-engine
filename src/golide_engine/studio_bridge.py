from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import quote
from urllib.request import Request, urlopen


Transport = Callable[[str, str, dict[str, str], bytes | None], tuple[int, bytes]]


def _transport(method: str, url: str, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
    request = Request(url, data=body, headers=headers, method=method)
    with urlopen(request, timeout=30) as response:
        return int(response.status), response.read()


class StudioBridge:
    """Two-layer bridge: Sites access token plus repository-bound GitHub OIDC."""

    def __init__(
        self,
        base_url: str,
        *,
        audience: str = "golide-studio-engine",
        transport: Transport = _transport,
        token_provider: Callable[[], str] | None = None,
        sites_token: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.audience = audience
        self.transport = transport
        self.token_provider = token_provider or self._actions_oidc_token
        self.sites_token = sites_token if sites_token is not None else os.getenv(
            "GOLIDE_STUDIO_BYPASS_TOKEN", ""
        ).strip()

    def _actions_oidc_token(self) -> str:
        request_url = os.getenv("ACTIONS_ID_TOKEN_REQUEST_URL")
        request_token = os.getenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
        if not request_url or not request_token:
            raise RuntimeError("GitHub Actions OIDC environment is unavailable")
        separator = "&" if "?" in request_url else "?"
        url = f"{request_url}{separator}audience={quote(self.audience)}"
        status, body = self.transport(
            "GET", url, {"Authorization": f"Bearer {request_token}"}, None
        )
        if status != 200:
            raise RuntimeError(f"GitHub OIDC token request failed with HTTP {status}")
        value = json.loads(body.decode("utf-8")).get("value")
        if not value:
            raise RuntimeError("GitHub OIDC token response was empty")
        return str(value)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, bytes]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Authorization": f"Bearer {self.token_provider()}"}
        if self.sites_token:
            headers["OAI-Sites-Authorization"] = f"Bearer {self.sites_token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        return self.transport(method, f"{self.base_url}{path}", headers, body)

    def claim_next(self, now: datetime | None = None) -> dict[str, Any] | None:
        now = now or datetime.now(timezone.utc)
        status, body = self._request(
            "GET", f"/api/engine/next?now={quote(now.isoformat())}"
        )
        if status == 204:
            return None
        if status != 200:
            raise RuntimeError(f"Studio next-job request failed with HTTP {status}")
        payload = json.loads(body.decode("utf-8"))
        if not payload.get("jobId") or not isinstance(payload.get("spec"), dict):
            raise RuntimeError("Studio returned an invalid production job")
        payload["spec"]["_studio_job_id"] = payload["jobId"]
        return payload

    def register(self, spec: dict[str, Any]) -> None:
        job_id = str(spec["id"])
        status, _ = self._request(
            "POST", "/api/engine/jobs/register", {"jobId": job_id, "spec": spec}
        )
        if status not in {200, 201}:
            raise RuntimeError(f"Studio job registration failed with HTTP {status}")

    def sync_analytics(self, payload: dict[str, Any]) -> None:
        status, _ = self._request("POST", "/api/engine/analytics", payload)
        if status != 200:
            raise RuntimeError(f"Studio analytics sync failed with HTTP {status}")

    def report(
        self,
        job_id: str,
        *,
        status: str,
        stage: str,
        actual_cost_usd: float = 0,
        openai_cost_usd: float = 0,
        elevenlabs_cost_usd: float = 0,
        elevenlabs_characters: int = 0,
        run_url: str | None = None,
        release_url: str | None = None,
        error: str | None = None,
        title: str | None = None,
        script: str | None = None,
        selected_topic: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "status": status,
            "stage": stage,
            "actualCostUsd": actual_cost_usd,
            "providerUsage": {
                "openAiCostUsd": openai_cost_usd,
                "elevenLabsCostUsd": elevenlabs_cost_usd,
                "elevenLabsCharacters": elevenlabs_characters,
            },
        }
        if run_url:
            payload["runUrl"] = run_url
        if release_url:
            payload["releaseUrl"] = release_url
        if error:
            payload["error"] = error[:2000]
        if title:
            payload["title"] = title[:300]
        if script:
            payload["script"] = script[:20000]
        if selected_topic:
            payload["selectedTopic"] = selected_topic[:1000]
        response_status, _ = self._request(
            "POST", f"/api/engine/jobs/{quote(job_id)}/status", payload
        )
        if response_status != 200:
            raise RuntimeError(f"Studio status update failed with HTTP {response_status}")

    def sync_connections(self, connections: list[dict[str, Any]]) -> None:
        response_status, _ = self._request(
            "POST", "/api/engine/connections", {"connections": connections}
        )
        if response_status != 200:
            raise RuntimeError(
                f"Studio connection sync failed with HTTP {response_status}"
            )

    def create_content(self, payload: dict[str, Any]) -> dict[str, Any]:
        status, body = self._request("POST", "/api/engine/posts", payload)
        if status not in {200, 201}:
            raise RuntimeError(f"Studio content creation failed with HTTP {status}")
        return json.loads(body.decode("utf-8"))

    def register_media(self, records: list[dict[str, Any]]) -> None:
        status, _ = self._request(
            "POST", "/api/engine/media/register", {"records": records}
        )
        if status != 200:
            raise RuntimeError(f"Studio media registration failed with HTTP {status}")

    def claim_due_social(self, now: datetime | None = None) -> dict[str, Any] | None:
        now = now or datetime.now(timezone.utc)
        status, body = self._request(
            "GET", f"/api/engine/social/next?now={quote(now.isoformat())}"
        )
        if status == 204:
            return None
        if status != 200:
            raise RuntimeError(f"Studio social claim failed with HTTP {status}")
        return json.loads(body.decode("utf-8"))

    def report_social_variant(
        self,
        post_id: str,
        variant_id: str,
        *,
        status: str,
        remote_id: str | None = None,
        url: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        response_status, body = self._request(
            "POST",
            f"/api/engine/social/{quote(post_id)}/variants/{quote(variant_id)}",
            {
                "status": status,
                "remote_id": remote_id,
                "url": url,
                "error": error,
            },
        )
        if response_status != 200:
            raise RuntimeError(
                f"Studio social result update failed with HTTP {response_status}"
            )
        return json.loads(body.decode("utf-8"))

    def mark_media_deleted(self, refs: list[str]) -> None:
        status, _ = self._request(
            "POST", "/api/engine/media/deleted", {"media_refs": refs}
        )
        if status != 200:
            raise RuntimeError(f"Studio media cleanup sync failed with HTTP {status}")
