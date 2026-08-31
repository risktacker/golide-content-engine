import json
import unittest
from pathlib import Path

from golide_engine.models import Annotation, ManifestError, Motion
from golide_engine.motion import scene_filter, transition_for
from golide_engine.quality.editorial import check_editorial


class MotionGrammarTests(unittest.TestCase):
    def test_camera_filter_uses_eased_zoompan_and_annotation(self):
        motion = Motion(
            type="reframe", intensity="strong", transition="paper-wipe",
            easing="ease-in-out", emphasis="reveal", audio_cue="impact",
        )
        annotation = Annotation(
            kind="number", text="99.9%", start_offset=0.2,
            duration=0.8, position="center", color_token="golide-gold",
        )
        result = scene_filter(motion, annotation, 1080, 1920, 30, 1.4)
        self.assertIn("zoompan=", result)
        self.assertIn("drawtext=", result)
        self.assertIn("99.9", result)
        self.assertEqual("wipeleft", transition_for(motion, 30).name)

    def test_invalid_annotation_timing_is_rejected(self):
        with self.assertRaises(ManifestError):
            Annotation.from_dict({
                "kind": "label", "text": "late", "start_offset": 1.8,
                "duration": 1.0, "position": "top", "color_token": "neon-blue",
            }, 2.0)


class EditorialQualityTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(Path("config/qa-policy.json").read_text(encoding="utf-8"))

    @staticmethod
    def _scene(index, motion, transition="cut", audio="none"):
        start = float(index)
        return {
            "id": f"beat-{index + 1:03d}",
            "start": start,
            "end": start + 1,
            "duration": 1,
            "visual_caption": "",
            "motion": {
                "type": motion,
                "intensity": "medium",
                "transition": transition,
                "easing": "ease-in-out",
                "emphasis": "",
                "audio_cue": audio,
                "annotation": {
                    "kind": "none", "text": "", "start_offset": 0,
                    "duration": 0, "position": "center", "color_token": "golide-gold",
                },
            },
        }

    def test_varied_timing_bound_edit_passes(self):
        storyboard = {"scenes": [
            self._scene(0, "push-in"),
            self._scene(1, "pan-left"),
            self._scene(2, "layer-reveal", audio="soft-trace"),
            self._scene(3, "reframe"),
        ]}
        failures, metrics = check_editorial(storyboard, "short", self.policy)
        self.assertEqual([], failures)
        self.assertEqual(4, metrics["beats"])
        self.assertEqual(4, metrics["unique_motion_recipes"])

    def test_repetitive_motion_and_transition_spam_fail(self):
        storyboard = {"scenes": [
            self._scene(i, "push-in", transition="paper-wipe")
            for i in range(5)
        ]}
        failures, _ = check_editorial(storyboard, "short", self.policy)
        self.assertTrue(any("repeats" in item for item in failures))
        self.assertTrue(any("transition density" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
