from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from golide_engine.db.connections import ConnectionRepository
from golide_engine.db.inbox import InboxRepository
from golide_engine.engine.connections import Transport
from golide_engine.storage import Database
from golide_engine.web import StudioService


class StudioServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "golide.sqlite3")
        self.db.initialize()
        self.service = StudioService(self.db)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_create_and_overview_with_locked_static_route(self) -> None:
        scheduled = datetime.now(timezone.utc) + timedelta(hours=1)
        units = [
            "Make the problem visible.",
            "Give the reader useful value.",
            "Close with a practical next step.",
        ]
        created = self.service.create_post({
            "content_class": "post",
            "content_lane": "authority",
            "weekly_theme": "Workflow clarity",
            "title": "Proof post",
            "master_text": "\n\n".join(units),
            "value_units": units,
            "media_approved": True,
            "release_approved": True,
            "scheduled_at": scheduled.isoformat(),
            "variants": [
                {"platform": "instagram", "body": "IG version", "media_ref": "r2://meta.jpg"},
                {"platform": "facebook", "body": "FB version", "media_ref": "r2://meta.jpg"},
                {"platform": "linkedin", "body": "LinkedIn version", "media_ref": "r2://square.jpg"},
                {"platform": "x", "body": "X version", "media_ref": "r2://square.jpg"},
            ],
        })
        self.assertEqual(created["status"], "scheduled")
        self.assertEqual(created["content_class"], "post")
        overview = self.service.overview()
        self.assertEqual(overview["scheduled"], 1)
        posts = self.service.posts("scheduled")
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["content_class"], "post")
        self.assertEqual(len(posts[0]["variants"]), 4)
        self.assertEqual(posts[0]["value_units"], units)

    def test_policy_snapshot_exposes_locked_calendar(self) -> None:
        snapshot = self.service.policy_snapshot()
        self.assertEqual(snapshot["calendar"]["weekly_totals"]["core_posts"], 14)
        self.assertEqual(snapshot["routing"]["content_types"]["long_video"]["platforms"], ["youtube"])

    def test_connections_and_inbox_are_normalized_for_ui(self) -> None:
        connections = ConnectionRepository(self.db)
        account_id = connections.upsert(
            platform="instagram",
            account_label="GOLIDE",
            external_account_id="ig-1",
            transport=Transport.OFFICIAL_API,
            credential_ref="secret://meta",
        )
        inbox = InboxRepository(self.db)
        thread_id = inbox.upsert_thread(
            platform="instagram",
            external_thread_id="thread-1",
            account_id=account_id,
            participant_ref="@viewer",
            subject="Interested",
        )
        inbox.add_message(
            thread_id=thread_id,
            external_message_id="message-1",
            direction="inbound",
            body="How does this work?",
        )
        self.assertEqual(self.service.overview()["connected_platforms"], 1)
        self.assertEqual(self.service.overview()["open_responses"], 1)
        self.assertEqual(self.service.connection_rows()[0]["platform"], "instagram")
        self.assertEqual(
            self.service.inbox_rows()[0]["messages"][0]["body"],
            "How does this work?",
        )


if __name__ == "__main__":
    unittest.main()
