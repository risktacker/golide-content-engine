from __future__ import annotations

from uuid import uuid4

from golide_engine.engine.connections import SocialConnection, Transport
from golide_engine.storage import Database
from golide_engine.storage.database import utc_now


class ConnectionRepository:
    """Stores account metadata and secret references, never raw tokens."""

    def __init__(self, database: Database):
        self.database = database

    def upsert(
        self,
        *,
        platform: str,
        account_label: str,
        external_account_id: str,
        transport: Transport | str,
        credential_ref: str,
        status: str = "connected",
    ) -> str:
        platform = platform.strip().lower()
        external_account_id = external_account_id.strip()
        credential_ref = credential_ref.strip()
        if not platform or not external_account_id or not credential_ref:
            raise ValueError("platform, external account id and credential reference are required")
        transport_value = transport.value if isinstance(transport, Transport) else Transport(transport).value
        if status not in {"connected", "disconnected", "error"}:
            raise ValueError("unsupported connection status")
        now = utc_now()
        existing = self.database.rows(
            "SELECT id FROM social_accounts WHERE platform=? AND external_account_id=?",
            (platform, external_account_id),
        )
        account_id = existing[0]["id"] if existing else str(uuid4())
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO social_accounts
                   (id, platform, account_label, external_account_id, transport,
                    credential_ref, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(platform, external_account_id) DO UPDATE SET
                     account_label=excluded.account_label,
                     transport=excluded.transport,
                     credential_ref=excluded.credential_ref,
                     status=excluded.status,
                     updated_at=excluded.updated_at""",
                (
                    account_id,
                    platform,
                    account_label.strip(),
                    external_account_id,
                    transport_value,
                    credential_ref,
                    status,
                    now,
                    now,
                ),
            )
        return account_id

    def list(self) -> list[SocialConnection]:
        rows = self.database.rows(
            """SELECT id, platform, account_label, external_account_id,
                      transport, credential_ref, status
               FROM social_accounts ORDER BY platform, account_label"""
        )
        return [SocialConnection(**row) for row in rows]
