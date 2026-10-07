import subprocess
import tempfile
import unittest
from pathlib import Path

from golide_engine.vector.align import align_lines, caption_chunks, group_lines

PLAN = {"title": "t", "lines": [
    {"section": "claim", "text": "AI doesn't decide who gets hired.", "emphasis": "AI",
     "visual": "dot_field", "label": "RANDOM"},
    {"section": "claim", "text": "Systems do.", "emphasis": "Systems", "visual": "grid", "label": "DECIDED"},
    {"section": "pattern", "text": "Every check builds momentum.", "emphasis": "check",
     "visual": "checklist", "label": "DAILY"},
    {"section": "pattern", "text": "Every day adds one more.", "emphasis": "day",
     "visual": "checklist", "label": "DAILY"},
]}


def _words(skip: str = "") -> list[dict]:
    words, t = [], 0.3
    for line in PLAN["lines"]:
        for w in line["text"].split():
            if w == skip:
                continue
            words.append({"word": w, "start": round(t, 2), "end": round(t + 0.3, 2)})
            t += 0.36
        t += 0.8
    return words


class AlignmentTests(unittest.TestCase):
    def test_lines_follow_the_recording(self):
        words = _words()
        lines = align_lines(PLAN, words, 12.0)
        self.assertEqual(lines[0].start, 0.0)
        self.assertAlmostEqual(lines[1].start, words[6]["start"], places=2)
        self.assertTrue(all(a.end == b.start for a, b in zip(lines, lines[1:])))
        self.assertEqual(lines[-1].end, 12.0)

    def test_owner_skipping_a_word_does_not_break_timing(self):
        lines = align_lines(PLAN, _words(skip="Systems"), 12.0)
        self.assertTrue(all(b.start > a.start for a, b in zip(lines, lines[1:])))

    def test_same_visual_lines_build_one_animation(self):
        groups = group_lines(align_lines(PLAN, _words(), 12.0))
        # "AI ... hired" names subjects, so it shows them (brain + hire), not dots.
        self.assertEqual([g.visual for g in groups], ["icon_pair", "grid", "checklist"])
        self.assertEqual(groups[0].icons[0], "brain")
        self.assertEqual(len(groups[-1].lines), 2)

    def test_captions_cover_the_spoken_words(self):
        chunks = caption_chunks(align_lines(PLAN, _words(), 12.0))
        spoken = [w.text for c in chunks for w in c.words]
        self.assertEqual(spoken[:2], ["AI", "doesn't"])


class RenderTests(unittest.TestCase):
    def test_video_matches_recording_length_and_size(self):
        from golide_engine.vector.render import VectorRenderer

        with tempfile.TemporaryDirectory() as tmp:
            voice = Path(tmp) / "voice.wav"
            out = Path(tmp) / "video.mp4"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                            "sine=frequency=180:duration=2", str(voice)], check=True)
            VectorRenderer("short", fps=24).render(PLAN, _words()[:4], voice, out, 2.0)
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                 "stream=width,height:format=duration", "-of", "csv=p=0", str(out)],
                capture_output=True, text=True, check=True).stdout.split()
            self.assertEqual(probe[0], "1080,1920")
            self.assertAlmostEqual(float(probe[1]), 2.0, delta=0.15)


class FlowTests(unittest.TestCase):
    def test_a_drawing_in_two_scenes_glides_instead_of_redrawing(self):
        from golide_engine.vector.render import Transition, VectorRenderer

        plan = {"title": "t", "lines": [
            {"section": "claim", "text": "More chips everywhere.", "emphasis": "chips",
             "visual": "icon_grid", "subjects": ["chip"], "label": "A"},
            {"section": "proof", "text": "Water meets the chip.", "emphasis": "Water",
             "visual": "icon_pair", "subjects": ["water drop", "chip"], "label": "B"},
        ]}
        words, t = [], 0.2
        for line in plan["lines"]:
            for w in line["text"].split():
                words.append({"word": w, "start": t, "end": t + 0.3})
                t += 0.4
            t += 0.6
        groups = group_lines(align_lines(plan, words, t + 0.5))
        self.assertEqual(len(groups), 2)
        transition = Transition.between(VectorRenderer("short", fps=24), groups[0], groups[1], 1)
        self.assertEqual(transition.shared, {"cpu"})
        self.assertGreater(len(transition.src), 0)  # the other chips turn into light

    def test_ambient_bed_is_quiet_and_exact_length(self):
        import numpy as np
        from golide_engine.vector.ambient import LEVEL_DB, ambient_bed

        bed = ambient_bed(6.0, "title")
        self.assertEqual(len(bed), 6 * 48000)
        middle = bed[48000 * 2: 48000 * 4]
        level = 20 * np.log10(np.sqrt(np.mean(middle ** 2)))
        self.assertLess(level, LEVEL_DB + 6)
        self.assertLess(abs(bed[0]), 1e-3)  # fades in, no click

    def test_stars_twinkle_and_drift(self):
        import numpy as np
        from golide_engine.vector.render import StarField

        stars = StarField(200, 300)
        a = stars.add(np.zeros((300, 200, 3), np.float32), 0.0)
        b = stars.add(np.zeros((300, 200, 3), np.float32), 1.0)
        self.assertGreater(a.sum(), 0)
        self.assertFalse(np.allclose(a, b))


if __name__ == "__main__":
    unittest.main()


class KeyTermTests(unittest.TestCase):
    def test_key_term_lights_only_its_own_phrase(self):
        from golide_engine.vector.align import key_positions
        words = "Follow the channel, because the feed won't show us".split()
        self.assertEqual(key_positions(words, "Follow the channel"), {0, 1, 2})
        self.assertEqual(key_positions("the cloud and the cloud".split(), "cloud"), {1})
