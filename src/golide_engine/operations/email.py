"""Owner email alerts.

Sends the "record needed" email when a video script is ready (or when a
recording was rejected for its length). Transport today is Gmail SMTP with an
app password, run from GitHub Actions. When Studio moves to Cloudflare this
can switch to Cloudflare's email sending without changing the message.

Required environment (GitHub secrets):
    GOLIDE_SMTP_USER          the Gmail address that sends
    GOLIDE_SMTP_APP_PASSWORD  a Gmail app password (not the account password)
    GOLIDE_NOTIFY_EMAIL       where alerts go (defaults to GOLIDE_SMTP_USER)

If these are missing the alert is skipped and logged; production never fails
because an email could not be sent.
"""

from __future__ import annotations

import html
import os
import smtplib
from email.message import EmailMessage

from golide_engine.orchestration.recording import RECORDING_WINDOWS

STUDIO_URL = os.getenv("GOLIDE_STUDIO_BASE_URL", "https://studio.golidee.com").rstrip("/")


def _clock(seconds: float) -> str:
    whole = int(round(seconds))
    return f"{whole // 60}:{whole % 60:02d}"


def build_record_needed(
    *,
    job_id: str,
    title: str,
    format_name: str,
    script: str,
    rejection: str = "",
) -> EmailMessage:
    low, high = RECORDING_WINDOWS.get(format_name, RECORDING_WINDOWS["short"])
    label = "Short" if format_name == "short" else "Long video"
    window = f"{_clock(low)} to {_clock(high)}"
    link = f"{STUDIO_URL}/#job-{job_id}"
    subject_prefix = "Re-record" if rejection else "Record today"
    message = EmailMessage()
    message["Subject"] = f"{subject_prefix}: [{label}] {title}"[:180]

    lines = [script.strip()]
    plain = (
        (f"Your last upload was rejected: {rejection}\n\n" if rejection else "")
        + f"{label} script ready. Record it in your own voice, {window}.\n\n"
        + "\n".join(lines)
        + f"\n\nUpload your recording: {link}\n"
    )
    message.set_content(plain)

    script_html = "".join(
        f'<p style="margin:0 0 10px;font-size:17px;line-height:1.5">{html.escape(row)}</p>'
        for row in script.strip().splitlines() if row.strip()
    )
    rejected_html = (
        f'<p style="color:#d0605e;margin:0 0 16px">Your last upload was rejected: {html.escape(rejection)}</p>'
        if rejection else ""
    )
    message.add_alternative(
        f"""<div style="background:#0b0b0e;color:#f4f4f5;font-family:Arial,sans-serif;padding:24px">
  <p style="color:#e9c46a;letter-spacing:2px;font-size:12px;margin:0 0 8px">{label.upper()} &middot; RECORD {window}</p>
  <h2 style="margin:0 0 16px;font-weight:600">{html.escape(title)}</h2>
  {rejected_html}
  <div style="border-left:3px solid #e9c46a;padding:4px 0 4px 16px;margin:0 0 24px">{script_html}</div>
  <a href="{link}" style="display:inline-block;background:#e9c46a;color:#0b0b0e;padding:12px 22px;border-radius:999px;font-weight:700;text-decoration:none">Upload recording</a>
</div>""",
        subtype="html",
    )
    return message


def build_reconnect_reminder(*, platform: str, days_left: int, account: str = "") -> EmailMessage:
    name = {"linkedin": "LinkedIn"}.get(platform, platform.title())
    link = f"{STUDIO_URL}/#connections"
    when = "today" if days_left <= 0 else ("tomorrow" if days_left == 1 else f"in {days_left} days")
    message = EmailMessage()
    message["Subject"] = f"Reconnect {name}: access expires {when}"
    message.set_content(
        f"{name}{' (' + account + ')' if account else ''} only allows 60-day access, "
        f"and it runs out {when}. After that, {name} posts stop until you reconnect.\n\n"
        f"Takes 20 seconds: open Studio, Connections, Reconnect {name}, Allow.\n\n{link}\n"
    )
    return message


def build_rebuild_preview(*, title: str, preview_url: str, production_id: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = f"Preview ready: {title}"[:180]
    message.set_content(
        f"The rebuilt video for \"{title}\" is ready. Nothing has been published yet.\n\n"
        f"Watch it (link works for 48 hours):\n{preview_url}\n\n"
        "If it is good, tell Claude to publish it. It will go to YouTube as a new video and to "
        "Instagram and Facebook as Reels. Delete the old YouTube video yourself afterwards.\n\n"
        f"Job: {production_id}\n"
    )
    message.add_alternative(
        f"""<div style="background:#0b0b0e;color:#f4f4f5;font-family:Arial,sans-serif;padding:24px">
  <p style="color:#e9c46a;letter-spacing:2px;font-size:12px;margin:0 0 8px">PREVIEW &middot; NOT PUBLISHED YET</p>
  <h2 style="margin:0 0 16px;font-weight:600">{html.escape(title)}</h2>
  <p style="margin:0 0 24px;line-height:1.5">Watch it with sound. If it is good, tell Claude to publish it to YouTube, Instagram and Facebook.</p>
  <a href="{html.escape(preview_url)}" style="display:inline-block;background:#e9c46a;color:#0b0b0e;padding:12px 22px;border-radius:999px;font-weight:700;text-decoration:none">Watch preview</a>
  <p style="color:#7a7a84;font-size:12px;margin:24px 0 0">Link works for 48 hours. Job {html.escape(production_id)}</p>
</div>""",
        subtype="html",
    )
    return message


def send_rebuild_preview(**kwargs) -> bool:
    return _send(build_rebuild_preview(**kwargs))


def _send(message: EmailMessage) -> bool:
    user = os.getenv("GOLIDE_SMTP_USER", "").strip()
    password = os.getenv("GOLIDE_SMTP_APP_PASSWORD", "").strip()
    to = os.getenv("GOLIDE_NOTIFY_EMAIL", "").strip() or user
    if not user or not password or not to:
        print('{"status": "email_skipped", "reason": "SMTP secrets are not configured"}')
        return False
    message["From"] = f"GOLIDE Engine <{user}>"
    message["To"] = to
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login(user, password)
            smtp.send_message(message)
    except Exception as exc:  # an email must never break production
        print(f'{{"status": "email_failed", "error": {str(exc)!r}}}')
        return False
    return True


def send_record_needed(**kwargs) -> bool:
    return _send(build_record_needed(**kwargs))


def send_reconnect_reminder(**kwargs) -> bool:
    return _send(build_reconnect_reminder(**kwargs))
