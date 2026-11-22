import unittest
from datetime import datetime, timezone


class FakeBridge:
    def __init__(self, slots):
        self.slots, self.sent = slots, {}

    def link_slots(self):
        return self.slots

    def suggest(self, job_id, pick):
        self.sent[job_id] = pick
        return True


class MorningPickTests(unittest.TestCase):
    def test_each_waiting_slot_gets_a_different_unmodelled_video(self):
        from unittest import mock
        from golide_engine.orchestration import pick
        videos = [{"url": "https://www.youtube.com/watch?v=AAAAAAAAAAA", "title": "One", "style": "goli"},
                  {"url": "https://www.youtube.com/watch?v=BBBBBBBBBBB", "title": "Two", "style": "stickman_goli"}]
        bridge = FakeBridge([{"job_id": "a", "format": "long", "scheduled_at": "1"},
                             {"job_id": "b", "format": "long", "scheduled_at": "2"},
                             {"job_id": "c", "format": "long", "suggested_model": {"url": videos[0]["url"]}}])
        with mock.patch("golide_engine.youtube.breakouts.find_breakouts", return_value=videos), \
                mock.patch("golide_engine.orchestration.history.used_source_videos", return_value=set()):
            pick.run(bridge, None, datetime(2026, 11, 23, tzinfo=timezone.utc))
        self.assertEqual(bridge.sent["a"]["url"], videos[1]["url"])   # the first is already shown on slot c
        self.assertNotIn("b", bridge.sent)                              # nothing left that is not taken
        self.assertNotIn("c", bridge.sent)
