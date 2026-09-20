from __future__ import annotations

import unittest

from golide_engine.engine.research import TopicCandidate, rank_topics, top_topic
from golide_engine.engine.scripts import ScriptBrief, VideoFormat, build_script_instruction
from golide_engine.engine.video import VideoProfile, VisualBeat, WordTiming, validate_timeline


class VideoFoundationTests(unittest.TestCase):
    def candidate(self, topic: str, score: float, evidence: str = "Current source evidence") -> TopicCandidate:
        return TopicCandidate(
            topic=topic,
            source="youtube",
            evidence=evidence,
            relevance=score,
            freshness=score,
            engagement_potential=score,
            audience_fit=score,
            originality_of_angle=score,
            golide_relevance=score,
        )

    def test_topic_ranking_only_promotes_highest_scored_candidate(self) -> None:
        lower = self.candidate("Older angle", 0.4)
        higher = self.candidate("Strong current angle", 0.9)
        self.assertEqual(rank_topics([lower, higher])[0], higher)
        self.assertEqual(top_topic([lower, higher]), higher)

    def test_vertical_and_horizontal_script_instructions_are_not_the_same_script(self) -> None:
        topic = self.candidate("AI workflow change", 0.9, "Verified evidence packet")
        vertical = build_script_instruction(
            ScriptBrief(
                niche="technology and software",
                topic=topic,
                format=VideoFormat.VERTICAL,
                goal="reach",
                duration_seconds=45,
            )
        )
        horizontal = build_script_instruction(
            ScriptBrief(
                niche="technology and software",
                topic=topic,
                format=VideoFormat.HORIZONTAL,
                goal="authority",
                duration_seconds=480,
            )
        )
        self.assertIn("Hook in the first second", vertical)
        self.assertIn("cold open", horizontal)
        self.assertIn("Verified evidence packet", vertical)
        self.assertNotEqual(vertical, horizontal)

    def test_locked_video_profile_enforces_owner_voice_and_one_render(self) -> None:
        profile = VideoProfile.load()
        profile.validate()
        self.assertFalse(profile.raw["voice"]["ai_voice_allowed"])
        self.assertFalse(profile.raw["voice"]["cloned_voice_allowed"])
        self.assertEqual(profile.raw["voice"]["source"], "owner_recording_only")
        self.assertEqual(profile.raw["render"]["final_render_count"], 1)
        self.assertFalse(profile.raw["render"]["intermediate_video_files"])

    def test_reference_motion_vocabulary_is_locked(self) -> None:
        profile = VideoProfile.load()
        expected = {
            "reveal",
            "draw",
            "slide",
            "grow",
            "sweep",
            "tick",
            "cross_out",
            "underline",
            "fill",
            "stack",
            "fan",
            "progress",
        }
        self.assertEqual(profile.allowed_motions, expected)

    def test_visual_anchor_must_track_spoken_word(self) -> None:
        profile = VideoProfile.load()
        words = [
            WordTiming("this", 0.0, 0.2),
            WordTiming("changes", 0.6, 0.9),
        ]
        validate_timeline(
            profile,
            words,
            [VisualBeat(start=0.65, end=1.0, motion="reveal", meaning="show change", anchor_word="changes")],
        )
        with self.assertRaises(ValueError):
            validate_timeline(
                profile,
                words,
                [VisualBeat(start=1.2, end=1.5, motion="reveal", meaning="late reveal", anchor_word="changes")],
            )


if __name__ == "__main__":
    unittest.main()
