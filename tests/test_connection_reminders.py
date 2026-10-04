import unittest
from datetime import datetime, timedelta, timezone

from golide_engine.operations.email import build_reconnect_reminder
from golide_engine.operations.reminders import due_reminders


class ConnectionReminderTests(unittest.TestCase):
    def _at(self, hour, days_ahead):
        now = datetime(2026, 10, 4, hour, 30, tzinfo=timezone.utc)
        expiry = (now + timedelta(days=days_ahead, hours=2)).isoformat()
        return now, [{"platform": "linkedin", "expires_at": expiry, "account": "Esiah"}]

    def test_reminds_seven_three_one_days_before(self):
        for days in (7, 3, 1):
            now, rows = self._at(6, days)
            self.assertEqual(due_reminders(rows, now)[0]["days_left"], days)

    def test_quiet_on_other_days_and_on_evening_run(self):
        now, rows = self._at(6, 5)
        self.assertEqual(due_reminders(rows, now), [])
        now, rows = self._at(15, 7)
        self.assertEqual(due_reminders(rows, now), [])

    def test_email_points_to_connections(self):
        message = build_reconnect_reminder(platform="linkedin", days_left=7)
        self.assertIn("in 7 days", message["Subject"])
        self.assertIn("#connections", message.get_content())


if __name__ == "__main__":
    unittest.main()
