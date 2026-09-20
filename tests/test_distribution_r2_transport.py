from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from golide_engine.db import ContentRepository
from golide_engine.engine import ContentDraft, PlatformVariant
from golide_engine.engine.social import SocialBridge
from golide_engine.providers import MemoryProvider
from golide_engine.storage import Database
from golide_engine.storage.r2 import R2TemporaryMediaStore
from golide_engine.storage.temporary import TemporaryMediaRepository
from golide_engine.web import StudioService


class FakeDelete:
    def __init__(self):
        self.urls = []

    def delete(self, url: str) -> None:
        self.urls.append(url)


class R2TransportTests(unittest.TestCase):
    def store(self, delete=None) -> R2TemporaryMediaStore:
        return R2TemporaryMediaStore(
            account_id="account123",
            access_key_id="ACCESS123",
            secret_access_key="SECRET456",
            bucket="golide-temp",
            delete_http=delete,
        )

    def test_presigned_upload_keeps_secret_out_of_url(self) -> None:
        now = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)
        prepared = self.store().prepare_upload(
            filename="../../my video.mp4",
            media_kind="video",
            now=now,
        )
        self.assertTrue(prepared.media_ref.startswith("r2://temp/2026/09/20/"))
        self.assertTrue(prepared.media_ref.endswith("-my-video.mp4"))
        parsed = urlparse(prepared.upload_url)
        self.assertEqual(parsed.netloc, "account123.r2.cloudflarestorage.com")
        query = parse_qs(parsed.query)
        self.assertEqual(query["X-Amz-Algorithm"], ["AWS4-HMAC-SHA256"])
        self.assertIn("X-Amz-Signature", query)
        self.assertNotIn("SECRET456", prepared.upload_url)

    def test_resolve_and_delete_use_signed_urls(self) -> None:
        deleted = FakeDelete()
        store = self.store(deleted)
        ref = "r2://temp/2026/09/20/file.png"
        resolved = store.resolve(ref)
        self.assertTrue(resolved.startswith(
            "https://account123.r2.cloudflarestorage.com/golide-temp/temp/"
        ))
        store.delete(ref)
        self.assertEqual(len(deleted.urls), 1)
        self.assertIn("X-Amz-Signature=", deleted.urls[0])

    def test_social_bridge_resolves_r2_but_database_keeps_logical_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "golide.sqlite3")
            db.initialize()
            repo = ContentRepository(db)
            logical = "r2://temp/item.png"
            post_id = repo.create(
                ContentDraft.build(
                    "Master",
                    [PlatformVariant("instagram", "IG", media_ref=logical)],
                ),
                scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            )
            provider = MemoryProvider("instagram")
            store = self.store()
            result = SocialBridge(
                repo,
                [provider],
                media_resolver=store,
            ).publish_post(post_id)
            self.assertEqual(result.status, "published")
            self.assertEqual(repo.variants(post_id)[0]["media_ref"], logical)
            self.assertTrue(provider.requests[0].media_ref.startswith("https://"))

    def test_studio_direct_upload_registers_and_extends_scheduled_retention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "golide.sqlite3")
            db.initialize()
            service = StudioService(db, media_store=self.store())
            prepared = service.prepare_media_upload({
                "filename": "post.png",
                "media_kind": "image",
            })
            before = db.rows(
                "SELECT expires_at, post_id FROM temporary_media WHERE object_key=?",
                (prepared["media_ref"],),
            )[0]
            self.assertIsNone(before["post_id"])
            scheduled = datetime.now(timezone.utc) + timedelta(days=3)
            created = service.create_post({
                "title": "Scheduled media",
                "master_text": "Master",
                "scheduled_at": scheduled.isoformat(),
                "variants": [{
                    "platform": "instagram",
                    "body": "IG",
                    "media_ref": prepared["media_ref"],
                }],
            })
            after = db.rows(
                "SELECT expires_at, post_id FROM temporary_media WHERE object_key=?",
                (prepared["media_ref"],),
            )[0]
            self.assertEqual(after["post_id"], created["id"])
            self.assertGreaterEqual(
                datetime.fromisoformat(after["expires_at"]),
                scheduled + timedelta(hours=24),
            )


if __name__ == "__main__":
    unittest.main()
