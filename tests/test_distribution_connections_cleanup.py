from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from golide_engine.db import ContentRepository
from golide_engine.db.connections import ConnectionRepository
from golide_engine.db.inbox import InboxRepository
from golide_engine.engine import ContentDraft, PlatformVariant
from golide_engine.engine.connections import Transport
from golide_engine.engine.social import SocialBridge
from golide_engine.jobs import cleanup_temporary_media, publish_due
from golide_engine.providers import MemoryProvider
from golide_engine.storage import Database
from golide_engine.storage.temporary import MemoryMediaStore, TemporaryMediaRepository


class ConnectionsInboxCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "golide.sqlite3")
        self.db.initialize()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_connection_keeps_secret_reference_not_token(self) -> None:
        connections = ConnectionRepository(self.db)
        account_id = connections.upsert(
            platform="Instagram",
            account_label="GOLIDE",
            external_account_id="ig-123",
            transport=Transport.OFFICIAL_API,
            credential_ref="secret://META_ACCESS_TOKEN",
        )
        saved = connections.list()[0]
        self.assertEqual(saved.id, account_id)
        self.assertEqual(saved.credential_ref, "secret://META_ACCESS_TOKEN")
        self.assertEqual(saved.transport, "official_api")

    def test_inbox_normalizes_thread_and_deduplicates_messages(self) -> None:
        connections = ConnectionRepository(self.db)
        account_id = connections.upsert(
            platform="instagram",
            account_label="GOLIDE",
            external_account_id="ig-123",
            transport="official_api",
            credential_ref="secret://META_ACCESS_TOKEN",
        )
        inbox = InboxRepository(self.db)
        thread_id = inbox.upsert_thread(
            platform="instagram",
            external_thread_id="thread-9",
            account_id=account_id,
            participant_ref="@customer",
            subject="Post reply",
        )
        first = inbox.add_message(
            thread_id=thread_id,
            external_message_id="msg-1",
            direction="inbound",
            body="Tell me more",
        )
        second = inbox.add_message(
            thread_id=thread_id,
            external_message_id="msg-1",
            direction="inbound",
            body="Tell me more",
        )
        self.assertEqual(first, second)
        self.assertEqual(len(inbox.open_threads()), 1)
        self.assertEqual(len(inbox.messages(thread_id)), 1)

    def test_confirmed_publish_marks_temp_media_then_cleanup_deletes_it(self) -> None:
        content = ContentRepository(self.db)
        media = TemporaryMediaRepository(self.db)
        object_key = "temp://posts/proof/image.png"
        post_id = content.create(
            ContentDraft.build(
                "Master post",
                [PlatformVariant("instagram", "Instagram copy", media_ref=object_key)],
            ),
            scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        media.register(
            object_key=object_key,
            media_kind="image",
            post_id=post_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )

        bridge = SocialBridge(content, [MemoryProvider("instagram")])
        result = publish_due(content, bridge, media_repository=media)[0]
        self.assertEqual(result.status, "published")

        store = MemoryMediaStore()
        deleted = cleanup_temporary_media(media, store)
        self.assertEqual(deleted, [object_key])
        self.assertEqual(store.deleted, [object_key])
        status = self.db.rows(
            "SELECT status FROM temporary_media WHERE object_key=?",
            (object_key,),
        )[0]["status"]
        self.assertEqual(status, "deleted")

    def test_partial_publish_does_not_delete_media_early(self) -> None:
        content = ContentRepository(self.db)
        media = TemporaryMediaRepository(self.db)
        object_key = "temp://posts/partial/image.png"
        post_id = content.create(
            ContentDraft.build(
                "Master post",
                [
                    PlatformVariant("instagram", "IG", media_ref=object_key),
                    PlatformVariant("linkedin", "LI", media_ref=object_key),
                ],
            ),
            scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        media.register(
            object_key=object_key,
            media_kind="image",
            post_id=post_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        bridge = SocialBridge(content, [MemoryProvider("instagram")])
        result = publish_due(content, bridge, media_repository=media)[0]
        self.assertEqual(result.status, "partial")

        store = MemoryMediaStore()
        self.assertEqual(cleanup_temporary_media(media, store), [])
        self.assertEqual(store.deleted, [])

    def test_expired_media_is_cleaned_even_without_publish_confirmation(self) -> None:
        media = TemporaryMediaRepository(self.db)
        object_key = "temp://expired/audio.wav"
        media.register(
            object_key=object_key,
            media_kind="audio",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        store = MemoryMediaStore()
        self.assertEqual(cleanup_temporary_media(media, store), [object_key])


if __name__ == "__main__":
    unittest.main()
