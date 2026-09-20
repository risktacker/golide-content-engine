from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from golide_engine.db import ContentRepository
from golide_engine.engine import ContentDraft, PlatformVariant
from golide_engine.engine.social import SocialBridge
from golide_engine.jobs import publish_due, schedule_post
from golide_engine.providers import MemoryProvider
from golide_engine.storage import Database


class DistributionCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "golide.sqlite3")
        self.db.initialize()
        self.repo = ContentRepository(self.db)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def draft(self) -> ContentDraft:
        return ContentDraft.build(
            "One canonical GOLIDE post.",
            [
                PlatformVariant("Instagram", "Instagram-native version", media_ref="temp://image/abc"),
                PlatformVariant("LinkedIn", "LinkedIn-native version"),
            ],
            title="Distribution core proof",
        )

    def test_create_schedule_and_publish_due(self) -> None:
        post_id = self.repo.create(self.draft())
        self.assertEqual(self.repo.get(post_id).status, "draft")

        due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        schedule_post(self.repo, post_id, due_at)

        instagram = MemoryProvider("instagram")
        linkedin = MemoryProvider("linkedin")
        bridge = SocialBridge(self.repo, [instagram, linkedin])
        results = publish_due(self.repo, bridge)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "published")
        self.assertEqual(results[0].published, 2)
        self.assertEqual(self.repo.get(post_id).status, "published")

        variants = self.repo.variants(post_id)
        self.assertTrue(all(item["platform_content_id"] for item in variants))
        self.assertEqual(len(instagram.requests), 1)
        self.assertEqual(len(linkedin.requests), 1)

    def test_future_post_is_not_published(self) -> None:
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        post_id = self.repo.create(self.draft(), scheduled_at=future)
        bridge = SocialBridge(self.repo, [MemoryProvider("instagram"), MemoryProvider("linkedin")])

        self.assertEqual(publish_due(self.repo, bridge), [])
        self.assertEqual(self.repo.get(post_id).status, "scheduled")

    def test_missing_provider_creates_partial_publish_not_silent_success(self) -> None:
        post_id = self.repo.create(
            self.draft(),
            scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        bridge = SocialBridge(self.repo, [MemoryProvider("instagram")])
        result = publish_due(self.repo, bridge)[0]

        self.assertEqual(result.status, "partial")
        variants = {row["platform"]: row for row in self.repo.variants(post_id)}
        self.assertEqual(variants["instagram"]["status"], "published")
        self.assertEqual(variants["linkedin"]["status"], "failed")
        self.assertIn("no connected provider", variants["linkedin"]["last_error"])

    def test_only_lightweight_media_reference_is_persisted(self) -> None:
        post_id = self.repo.create(self.draft())
        variants = self.repo.variants(post_id)
        instagram = next(row for row in variants if row["platform"] == "instagram")
        self.assertEqual(instagram["media_ref"], "temp://image/abc")


if __name__ == "__main__":
    unittest.main()
