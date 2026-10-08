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

    def _row(row: str) -> str:
        text = row.strip()
        if text.startswith("[") and text.endswith("]"):  # chapter heading, not read aloud
            return (f'<p style="margin:18px 0 6px;color:#9a6f12;font-size:12px;letter-spacing:2px;font-weight:600">'
                    f'{html.escape(text[1:-1])}</p>')
        return f'<p style="margin:0 0 10px;font-size:17px;line-height:1.55;color:#1b1d22">{html.escape(text)}</p>'

    script_html = "".join(_row(row) for row in script.strip().splitlines() if row.strip())
    if "\n[" in "\n" + script:
        script_html = ('<p style="margin:0 0 14px;color:#5f6470;font-size:14px">Gold headings are not read aloud. '
                       'Pause briefly at each one.</p>' + script_html)
    rejected_html = (
        f'<p style="color:#b4413b;margin:0 0 16px">Your last upload was rejected: {html.escape(rejection)}</p>'
        if rejection else ""
    )
    message.add_alternative(
        _frame(f"""<div style="color:#1b1d22;font-family:Arial,sans-serif">
  <p style="color:#9a6f12;letter-spacing:2px;font-size:12px;margin:0 0 8px;font-weight:600">{label.upper()} &middot; RECORD {window}</p>
  <h2 style="margin:0 0 16px;font-weight:600;color:#1b1d22;font-size:22px;line-height:1.3">{html.escape(title)}</h2>
  {rejected_html}
  <div style="border-left:3px solid #e9c46a;padding:2px 0 2px 18px;margin:0 0 24px">{script_html}</div>
  <a href="{link}" style="display:inline-block;background:#0b0c10;color:#ffffff;padding:13px 24px;border-radius:999px;font-weight:600;text-decoration:none">Upload recording</a>
</div>"""),
        subtype="html",
    )
    return message


def build_reconnect_reminder(*, platform: str, days_left: int, account: str = "") -> EmailMessage:
    name = {"linkedin": "LinkedIn"}.get(platform, platform.title())
    link = f"{STUDIO_URL}/#connections"
    when = "today" if days_left == 0 else ("tomorrow" if days_left == 1 else f"in {days_left} days")
    message = EmailMessage()
    if days_left < 0:
        message["Subject"] = f"Reconnect {name}: access has expired, posts are stopped"
        intro = (f"{name}{' (' + account + ')' if account else ''} access has expired, so {name} "
                 f"posts are not going out until you reconnect.\n\n")
    else:
        message["Subject"] = f"Reconnect {name}: access expires {when}"
        intro = (f"{name}{' (' + account + ')' if account else ''} only allows 60-day access, "
                 f"and it runs out {when}. After that, {name} posts stop until you reconnect.\n\n")
    message.set_content(
        intro +
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
        _frame(f"""<div style="color:#1b1d22;font-family:Arial,sans-serif">
  <p style="color:#9a6f12;letter-spacing:2px;font-size:12px;margin:0 0 8px;font-weight:600">PREVIEW &middot; NOT PUBLISHED YET</p>
  <h2 style="margin:0 0 16px;font-weight:600;color:#1b1d22;font-size:22px;line-height:1.3">{html.escape(title)}</h2>
  <p style="margin:0 0 24px;line-height:1.6;color:#1b1d22">Watch it with sound. If it is good, tell Claude to publish it to YouTube, Instagram and Facebook.</p>
  <a href="{html.escape(preview_url)}" style="display:inline-block;background:#0b0c10;color:#ffffff;padding:13px 24px;border-radius:999px;font-weight:600;text-decoration:none">Watch preview</a>
  <p style="color:#5f6470;font-size:12px;margin:24px 0 0">Link works for 48 hours. Job {html.escape(production_id)}</p>
</div>"""),
        subtype="html",
    )
    return message


def send_rebuild_preview(**kwargs) -> bool:
    return _send(build_rebuild_preview(**kwargs))


def _frame(inner: str) -> str:
    """The GOLIDE email shell, identical to Studio's (worker/mail.js brandShell):
    dark branded header with the logo, gold rule, white body with dark readable
    text, GOLIDE signature and footer. Tables + bgcolor so every app keeps it."""
    logo = "https://golidee.com/brand/wordmark.png"
    mark = "https://golidee.com/brand/favicon.png"
    return (
        '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light"></head>'
        '<body style="margin:0;padding:0;background:#f2f2ef" bgcolor="#f2f2ef">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f2f2ef" style="background:#f2f2ef"><tr><td align="center" style="padding:28px 12px">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;border-radius:14px;overflow:hidden;border:1px solid #e3e2dc">'
        f'<tr><td bgcolor="#0b0c10" style="background:#0b0c10;padding:22px 30px"><a href="https://golidee.com" style="text-decoration:none">'
        f'<img src="{logo}" width="132" alt="GOLIDE" style="display:block;border:0;height:auto;width:132px;color:#ecedef;font:600 18px Arial,sans-serif;letter-spacing:4px"></a></td></tr>'
        '<tr><td bgcolor="#e9c46a" style="background:#e9c46a;height:3px;line-height:3px;font-size:0">&nbsp;</td></tr>'
        f'<tr><td bgcolor="#ffffff" style="background:#ffffff;padding:32px 30px 8px;font-family:Arial,Helvetica,sans-serif;color:#1b1d22">{inner}</td></tr>'
        '<tr><td bgcolor="#ffffff" style="background:#ffffff;padding:8px 30px 28px;font-family:Arial,Helvetica,sans-serif">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid #ecebe6;width:100%"><tr>'
        f'<td width="44" valign="top" style="padding-top:18px"><img src="{mark}" width="36" height="36" alt="" style="display:block;border:0;border-radius:9px"></td>'
        '<td valign="top" style="padding:18px 0 0 12px;font-size:14px;line-height:1.45;color:#1b1d22"><strong style="font-weight:600">GOLIDE</strong><br>'
        '<span style="color:#5f6470">Software, markets and research &middot; Lusaka</span><br>'
        '<a href="https://golidee.com" style="color:#9a6f12;text-decoration:none">golidee.com</a></td></tr></table></td></tr>'
        '<tr><td bgcolor="#f7f7f4" style="background:#f7f7f4;padding:16px 30px;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.5;color:#8a8e98">'
        'Sent by GOLIDE Studio from hello@golidee.com.</td></tr>'
        '</table></td></tr></table></body></html>'
    )


GOLIDE_FROM = "GOLIDE <hello@golidee.com>"


def _send_resend(message: EmailMessage, key: str, to: str) -> bool:
    """Send from GOLIDE <hello@golidee.com> through Resend."""
    import json
    import urllib.request

    text = html_body = ""
    for part in message.walk():
        if part.get_content_type() == "text/plain" and not text:
            text = part.get_content()
        elif part.get_content_type() == "text/html" and not html_body:
            html_body = part.get_content()
    payload = {"from": GOLIDE_FROM, "to": [to], "subject": str(message["Subject"]), "text": text}
    if html_body:
        payload["html"] = html_body
    request = urllib.request.Request(
        "https://api.resend.com/emails", data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return 200 <= response.status < 300
    except Exception as exc:  # an email must never break production
        print(f'{{"status": "email_failed", "via": "resend", "error": {str(exc)!r}}}')
        return False


def _send(message: EmailMessage) -> bool:
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    notify = os.getenv("GOLIDE_NOTIFY_EMAIL", "").strip() or os.getenv("GOLIDE_SMTP_USER", "").strip()
    if resend_key and notify:
        if _send_resend(message, resend_key, notify):
            return True
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
