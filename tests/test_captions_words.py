import unittest

from golide_engine.captions import words_to_beats, words_to_srt


class WordCaptionTests(unittest.TestCase):
    def test_groups_words_and_preserves_word_times(self):
        words = [
            {"word": "How", "start": 0.0, "end": 0.2},
            {"word": "can", "start": 0.21, "end": 0.4},
            {"word": "this?", "start": 0.41, "end": 0.8},
            {"word": "One", "start": 0.9, "end": 1.1},
            {"word": "particle", "start": 1.11, "end": 1.6},
        ]
        result = words_to_srt(words, min_words=2, max_words=3)
        self.assertIn("How can this?", result)
        self.assertIn("00:00:00,000 --> 00:00:00,800", result)
        self.assertIn("One particle", result)

    def test_editorial_beats_follow_authoritative_word_timing(self):
        words = [
            {"word": "One", "start": 0.2, "end": 0.5},
            {"word": "particle.", "start": 0.51, "end": 1.2},
            {"word": "One", "start": 1.4, "end": 1.6},
            {"word": "bit.", "start": 1.61, "end": 2.1},
        ]
        beats = words_to_beats(words, max_seconds=3.2, min_seconds=0.8)
        self.assertEqual(["beat-001", "beat-002"], [item["id"] for item in beats])
        self.assertEqual(0.0, beats[0]["start"])
        self.assertEqual(beats[0]["end"], beats[1]["start"])
        self.assertEqual("One particle.", beats[0]["text"])

    def test_rejects_invalid_timestamp(self):
        with self.assertRaises(ValueError):
            words_to_srt([{"word": "bad", "start": 1, "end": 1}])
