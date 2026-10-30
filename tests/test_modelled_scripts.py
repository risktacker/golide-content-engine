"""2026-10-29: scripts model what successful videos say; the humanizer is the last pass."""

import json
import unittest
from unittest import mock

from golide_engine.engine.content_rules import follow_problems, script_instructions, spoken_pass_instructions
from golide_engine.operations.email import spoken_pass_line
from golide_engine.youtube import transcripts


def _plan(follow_at=(10,), text="Follow the channel so you see the next one."):
    lines = [{"text": f"line {i} about the hinge", "follow": i in follow_at} for i in range(12)]
    for i in follow_at:
        lines[i]["text"] = text
    return {"lines": lines}


class ModelledScriptTests(unittest.TestCase):
    def test_writer_models_the_videos_and_keeps_only_format_rules(self):
        for fmt, words in (("short", "150 to 185 spoken words"), ("long", "1300 to 1450 spoken words")):
            text = script_instructions(fmt)
            self.assertIn(words, text)
            self.assertIn("MODEL SCRIPTS", text)
            self.assertIn("who they are talking to", text)
            self.assertIn("digits", text)
            for old in ("CLAIM: open straight", "THE QUESTION THAT STARTS THE COMMENTS", "TEACHING STYLE"):
                self.assertNotIn(old, text)
        self.assertIn("Intro", script_instructions("long"))

    def test_follow_line_rules_are_only_the_hard_ones(self):
        self.assertEqual(follow_problems(_plan(follow_at=(3,)), "short"), [])        # anywhere it fits
        self.assertTrue(follow_problems(_plan(follow_at=()), "short"))
        self.assertTrue(follow_problems(_plan(text="Follow GOLIDE now."), "short"))
        self.assertTrue(follow_problems(_plan(text="Follow and comment AI below."), "short"))

    def test_humanizer_is_the_last_pass_with_the_owner_as_voice_sample(self):
        text = spoken_pass_instructions("short")
        self.assertIn("HUMANIZER GUIDE", text)
        self.assertIn("Staging instead of stating", text)
        self.assertIn("VOICE SAMPLE", text)
        self.assertIn("same number of lines", text)
        self.assertIn("Humanizer pass: applied", spoken_pass_line({"status": "applied"}))


class LineBeatTests(unittest.TestCase):
    """2026-10-30: 19 lines of 70 words made an 8-minute video with slow, few blocks."""

    def test_lines_stay_breath_sized(self):
        from golide_engine.engine.content_rules import line_problems
        self.assertIn("breath-sized phrase of 4 to 14 words", script_instructions("long"))
        self.assertIn("SUBJECTS", script_instructions("short"))
        self.assertEqual(line_problems({"lines": [{"text": "a short line of words"}]}), [])
        self.assertTrue(line_problems({"lines": [{"text": " ".join(["word"] * 70)}]}))


class TranscriptTests(unittest.TestCase):
    def test_video_ids_and_trimming(self):
        self.assertEqual(transcripts.video_id("https://www.youtube.com/watch?v=mhFozOsKZLU"), "mhFozOsKZLU")
        self.assertEqual(transcripts.video_id("https://youtube.com/shorts/VPOC47eTE-E"), "VPOC47eTE-E")
        long = transcripts.trim(" ".join(f"w{i}" for i in range(4000)), "long")
        self.assertIn("[...]", long)
        self.assertTrue(long.endswith("w3999"))

    def test_models_pick_source_first_one_per_channel_and_skip_missing(self):
        source = {"url": "https://www.youtube.com/watch?v=AAAAAAAAAAA", "channel": "A", "title": "src"}
        breakouts = [{"url": "https://www.youtube.com/watch?v=BBBBBBBBBBB", "channel": "A", "score": 90, "format": "short"},
                     {"url": "https://www.youtube.com/watch?v=CCCCCCCCCCC", "channel": "C", "score": 80, "format": "short"},
                     {"url": "https://www.youtube.com/watch?v=DDDDDDDDDDD", "channel": "D", "score": 70, "format": "short"},
                     {"url": "https://www.youtube.com/watch?v=EEEEEEEEEEE", "channel": "E", "score": 60, "format": "short"}]
        words = " ".join(["word"] * 80)
        with mock.patch.object(transcripts, "fetch", side_effect=lambda u: "" if "DDD" in u else words), \
                mock.patch.object(transcripts, "owner_picks", return_value=[]):
            chosen = transcripts.choose_models(source, breakouts, "short")
        self.assertEqual([c["url"][-11:] for c in chosen], ["AAAAAAAAAAA", "CCCCCCCCCCC", "EEEEEEEEEEE"])

    def test_supadata_job_and_list_content(self):
        responses = [{"jobId": "j1"}, {"content": [{"text": "hello there"}, {"text": "[Music] friend"}]}]

        class R:
            def __init__(self, body): self.body = body
            def read(self): return json.dumps(self.body).encode()
            def __enter__(self): return self
            def __exit__(self, *a): return False

        with mock.patch("urllib.request.urlopen", side_effect=lambda *a, **k: R(responses.pop(0))), \
                mock.patch("time.sleep"):
            self.assertEqual(transcripts._supadata("https://www.youtube.com/watch?v=AAAAAAAAAAA", "k"),
                             "hello there friend")


if __name__ == "__main__":
    unittest.main()


class SpokenFlowTests(unittest.TestCase):
    """2026-10-30: "What kind of human speaks like this?" """

    ROBOT = ["Touching a laptop screen feels wrong for about 3rd.", "Then your finger swipes between desktops.",
             "Scroll a page, pinch a photo, or drag a window.", "The touchscreen MacBook Pro handles all 3.",
             "But does touch make work faster?", "Run the same jobs with touch.", "Zooming feels immediate.",
             "The maker is adding touch to creative apps."]

    def test_a_list_of_short_sentences_is_sent_back(self):
        from golide_engine.engine.content_rules import line_problems
        self.assertTrue(any("bullet points" in p for p in line_problems({"lines": [{"text": t} for t in self.ROBOT]})))
        talk = ["Touching a laptop screen feels wrong for about a third of a second,",
                "and then your finger swipes between desktops and it just works,",
                "which is exactly what Apple wants you to feel the first time",
                "you pick up the new MacBook Pro in a store."] * 2
        self.assertEqual(line_problems({"lines": [{"text": t} for t in talk]}), [])

    def test_no_fake_tests_and_fractions_stay_words(self):
        from golide_engine.engine.numerals import digits
        text = script_instructions("short")
        self.assertIn("WE EXPLAIN, WE DID NOT TEST", text)
        self.assertIn("a third of a second", text)
        self.assertEqual(digits("two thirds of owners"), "two thirds of owners")
        self.assertIn("one short sentence per line", spoken_pass_instructions("short"))
