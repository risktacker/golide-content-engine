from golide_engine.operations.email import build_record_needed, send_record_needed


def test_record_needed_email_has_script_window_and_link():
    message = build_record_needed(
        job_id="golide-short-2026-10-05", title="AI won't replace you. This will.",
        format_name="short", script="AI doesn't decide who gets hired.\nSystems do.",
    )
    assert message["Subject"].startswith("Record today: [Short]")
    body = message.get_body(("plain",)).get_content()
    assert "0:30 to 1:30" in body
    assert "Systems do." in body
    assert "#job-golide-short-2026-10-05" in body


def test_rejection_email_explains_why():
    message = build_record_needed(
        job_id="j", title="t", format_name="long", script="x", rejection="too long",
    )
    assert message["Subject"].startswith("Re-record: [Long video]")
    assert "3:30 to 5:00" in message.get_body(("plain",)).get_content()


def test_missing_secrets_never_breaks_production(monkeypatch):
    for key in ("GOLIDE_SMTP_USER", "GOLIDE_SMTP_APP_PASSWORD", "GOLIDE_NOTIFY_EMAIL"):
        monkeypatch.delenv(key, raising=False)
    assert send_record_needed(job_id="j", title="t", format_name="short", script="x") is False
