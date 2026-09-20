from __future__ import annotations

from uuid import uuid4

from golide_engine.engine.inbox import InboxMessage, InboxThread
from golide_engine.storage import Database
from golide_engine.storage.database import utc_now


class InboxRepository:
    """Normalized conversation records for the Content Engine inbox."""

    def __init__(self, database: Database):
        self.database = database

    def upsert_thread(
        self,
        *,
        platform: str,
        external_thread_id: str,
        account_id: str,
        participant_ref: str,
        subject: str = "",
        status: str = "open",
        last_message_at: str | None = None,
    ) -> str:
        if status not in {"open", "closed"}:
            raise ValueError("unsupported thread status")
        platform = platform.strip().lower()
        external_thread_id = external_thread_id.strip()
        if not platform or not external_thread_id:
            raise ValueError("platform and external thread id are required")
        existing = self.database.rows(
            "SELECT id FROM inbox_threads WHERE platform=? AND external_thread_id=?",
            (platform, external_thread_id),
        )
        thread_id = existing[0]["id"] if existing else str(uuid4())
        now = utc_now()
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO inbox_threads
                   (id, platform, external_thread_id, account_id, participant_ref,
                    subject, status, last_message_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(platform, external_thread_id) DO UPDATE SET
                     participant_ref=excluded.participant_ref,
                     subject=excluded.subject,
                     status=excluded.status,
                     last_message_at=excluded.last_message_at,
                     updated_at=excluded.updated_at""",
                (
                    thread_id,
                    platform,
                    external_thread_id,
                    account_id,
                    participant_ref.strip(),
                    subject.strip(),
                    status,
                    last_message_at,
                    now,
                    now,
                ),
            )
        return thread_id

    def add_message(
        self,
        *,
        thread_id: str,
        external_message_id: str,
        direction: str,
        body: str,
        created_at: str | None = None,
    ) -> str:
        if direction not in {"inbound", "outbound"}:
            raise ValueError("direction must be inbound or outbound")
        body = body.strip()
        if not body:
            raise ValueError("message body is required")
        existing = self.database.rows(
            "SELECT id FROM inbox_messages WHERE thread_id=? AND external_message_id=?",
            (thread_id, external_message_id),
        )
        if existing:
            return existing[0]["id"]
        message_id = str(uuid4())
        self.database.execute(
            """INSERT INTO inbox_messages
               (id, thread_id, external_message_id, direction, body, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (message_id, thread_id, external_message_id, direction, body, created_at or utc_now()),
        )
        return message_id

    def open_threads(self) -> list[InboxThread]:
        rows = self.database.rows(
            """SELECT id, platform, external_thread_id, account_id, participant_ref,
                      subject, status, last_message_at
               FROM inbox_threads WHERE status='open'
               ORDER BY COALESCE(last_message_at, updated_at) DESC"""
        )
        return [InboxThread(**row) for row in rows]

    def messages(self, thread_id: str) -> list[InboxMessage]:
        rows = self.database.rows(
            """SELECT id, thread_id, external_message_id, direction, body, created_at
               FROM inbox_messages WHERE thread_id=?
               ORDER BY created_at ASC""",
            (thread_id,),
        )
        return [InboxMessage(**row) for row in rows]
