import json
import unittest
from datetime import datetime, timezone

from golide_engine.studio_bridge import StudioBridge


class StudioBridgeTests(unittest.TestCase):
    def test_claim_and_status_use_repository_oidc_bearer(self):
        calls = []
        def transport(method, url, headers, body):
            calls.append((method, url, headers, body))
            if url.endswith("/api/engine/next?now=2026-09-01T06%3A00%3A00%2B00%3A00"):
                return 200, json.dumps({
                    "jobId": "job-1",
                    "spec": {"id": "job-1", "format": "long"},
                }).encode()
            return 200, b'{"ok":true}'
        bridge = StudioBridge(
            "https://studio.example",
            transport=transport,
            token_provider=lambda: "short-lived-token",
        )
        claimed = bridge.claim_next(datetime(2026, 9, 1, 6, tzinfo=timezone.utc))
        self.assertEqual("job-1", claimed["spec"]["_studio_job_id"])
        bridge.report(
            "job-1", status="paused_funds", stage="asset:earth",
            openai_cost_usd=0.2, error="recharge needed",
        )
        self.assertTrue(all(call[2]["Authorization"] == "Bearer short-lived-token" for call in calls))
        status_payload = json.loads(calls[-1][3])
        self.assertEqual("paused_funds", status_payload["status"])
        self.assertEqual(0.2, status_payload["providerUsage"]["openAiCostUsd"])

    def test_no_content_means_no_due_studio_job(self):
        bridge = StudioBridge(
            "https://studio.example",
            transport=lambda *args: (204, b""),
            token_provider=lambda: "token",
        )
        self.assertIsNone(bridge.claim_next())
