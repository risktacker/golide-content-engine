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
        units = (
            "The problem is visible.",
            "Here is the useful mechanism.",
            "Close with the practical next step.",
        )
        return ContentDraft.build(
            "\n\n".join(units),
            [
                PlatformVariant("Instagram", "\n\n".join(units), media_ref="temp://image/meta"),
                PlatformVariant("Facebook", "\n\n".join(units), media_ref="temp://image/meta"),
                PlatformVariant("LinkedIn", "\n\n".join(units), media_ref="temp://image/square"),
                PlatformVariant("X", "\n\n".join(units), media_ref="temp://image/square", parts=units),
            ],
            title="Distribution core proof",
            content_class="post",
            weekly_theme="Useful systems",
            content_lane="authority",
            value_units=units,
            media_approved=True,
            release_approved=True,
        )

    def test_create_schedule_and_publish_due(self) -> None:
        post_id = self.repo.create(self.draft())
        self.assertEqual(self.repo.get(post_id).status, "draft")

        due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        schedule_post(self.repo, post_id, due_at)

        providers = [MemoryProvider(platform) for platform in ("instagram", "facebook", "linkedin", "x")]
        bridge = SocialBridge(self.repo, providers)
        results = publish_due(self.repo, bridge)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "published")
        self.assertEqual(results[0].published, 4)
        self.assertEqual(self.repo.get(post_id).status, "published")
        self.assertTrue(all(item["platform_content_id"] for item in self.repo.variants(post_id)))
        self.assertTrue(all(len(provider.requests) == 1 for provider in providers))

    def test_future_post_is_not_published(self) -> None:
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        post_id = self.repo.create(self.draft(), scheduled_at=future)
        bridge = SocialBridge(
            self.repo,
            [MemoryProvider(platform) for platform in ("instagram", "facebook", "linkedin", "x")],
        )
        self.assertEqual(publish_due(self.repo, bridge), [])
        self.assertEqual(self.repo.get(post_id).status, "scheduled")

    def test_missing_provider_creates_partial_publish_not_silent_success(self) -> None:
        post_id = self.repo.create(
            self.draft(),
            scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        bridge = SocialBridge(
            self.repo,
            [MemoryProvider(platform) for platform in ("instagram", "facebook", "linkedin")],
        )
        result = publish_due(self.repo, bridge)[0]

        self.assertEqual(result.status, "partial")
        variants = {row["platform"]: row for row in self.repo.variants(post_id)}
        self.assertEqual(variants["instagram"]["status"], "published")
        self.assertEqual(variants["facebook"]["status"], "published")
        self.assertEqual(variants["linkedin"]["status"], "published")
        self.assertEqual(variants["x"]["status"], "failed")
        self.assertIn("no connected provider", variants["x"]["last_error"])

    def test_only_lightweight_media_reference_is_persisted(self) -> None:
        post_id = self.repo.create(self.draft())
        variants = {row["platform"]: row for row in self.repo.variants(post_id)}
        self.assertEqual(variants["instagram"]["media_ref"], "temp://image/meta")
        self.assertEqual(variants["x"]["media_ref"], "temp://image/square")
        self.assertEqual(len(variants["x"]["parts"]), 3)


if __name__ == "__main__":
    unittest.main()
