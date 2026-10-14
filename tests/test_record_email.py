import os
import unittest
from unittest import mock

from golide_engine.operations.email import build_record_needed, send_record_needed


class RecordEmailTests(unittest.TestCase):
    def test_email_has_script_window_and_link(self):
        message = build_record_needed(
            job_id="golide-short-2026-10-05", title="AI won't replace you. This will.",
            format_name="short", script="AI doesn't decide who gets hired.\nSystems do.",
        )
        self.assertTrue(message["Subject"].startswith("Record today: [Short]"))
        body = message.get_body(("plain",)).get_content()
        self.assertIn("0:30 to 1:30", body)
        self.assertIn("Systems do.", body)
        self.assertIn("#job-golide-short-2026-10-05", body)

    def test_rejection_email_explains_why(self):
        message = build_record_needed(job_id="j", title="t", format_name="long", script="x",
                                      rejection="too long")
        self.assertTrue(message["Subject"].startswith("Re-record: [Long video]"))
        self.assertIn("2:30 to 10:00", message.get_body(("plain",)).get_content())

    def test_missing_secrets_never_breaks_production(self):
        clean = {k: v for k, v in os.environ.items() if not k.startswith("GOLIDE_SMTP")
                 and k != "GOLIDE_NOTIFY_EMAIL"}
        with mock.patch.dict(os.environ, clean, clear=True):
            self.assertFalse(send_record_needed(job_id="j", title="t", format_name="short", script="x"))


if __name__ == "__main__":
    unittest.main()
