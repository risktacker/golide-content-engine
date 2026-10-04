import unittest
from pathlib import Path

from golide_engine.orchestration.recording import (
    RECORDING_WINDOWS, RecordingLengthError, check_recording_length,
)


class RecordingLengthTests(unittest.TestCase):
    def test_windows_are_locked(self):
        self.assertEqual(RECORDING_WINDOWS["short"], (30.0, 90.0))
        self.assertEqual(RECORDING_WINDOWS["long"], (210.0, 300.0))

    def test_accepts_inside_window(self):
        for fmt, seconds in [("short", 30), ("short", 75), ("short", 90.4),
                             ("long", 210), ("long", 270), ("long", 300)]:
            check_recording_length(fmt, seconds)

    def test_rejects_outside_window_with_rerecord_message(self):
        for fmt, seconds, word in [("short", 29, "too short"), ("short", 91, "too long"),
                                   ("long", 200, "too short"), ("long", 322, "too long")]:
            with self.assertRaises(RecordingLengthError) as info:
                check_recording_length(fmt, seconds)
            self.assertIn(word, str(info.exception))
            self.assertIn("re-record", str(info.exception))

    def test_engine_never_retimes_owner_voice(self):
        source = Path("src/golide_engine/orchestration/production.py").read_text()
        self.assertNotIn("atempo", source)


if __name__ == "__main__":
    unittest.main()
