from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InboxThread:
    id: str
    platform: str
    external_thread_id: str
    account_id: str
    participant_ref: str
    subject: str
    status: str
    last_message_at: str | None


@dataclass(frozen=True)
class InboxMessage:
    id: str
    thread_id: str
    external_message_id: str
    direction: str
    body: str
    created_at: str
