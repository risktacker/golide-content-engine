import unittest

from golide_engine.engine.content_rules import (
    SCRIPT_SCHEMA, VISUAL_CUES, script_instructions, script_text,
)
from golide_engine.vector.primitives import PRIMITIVES


class ScriptRuleTests(unittest.TestCase):
    def test_targets_sit_inside_recording_windows(self):
        short, long = script_instructions("short"), script_instructions("long")
        self.assertIn("150 to 185 spoken words", short)
        self.assertIn("600 to 680 spoken words", long)
        for rules in (short, long):
            self.assertIn("CLAIM", rules)
            self.assertIn("CALL TO ACTION", rules)
            self.assertNotIn("ElevenLabs", rules)

    def test_every_visual_cue_has_a_renderer(self):
        line = SCRIPT_SCHEMA["properties"]["lines"]["items"]
        self.assertEqual(line["properties"]["visual"]["enum"], list(VISUAL_CUES))
        self.assertEqual(set(VISUAL_CUES), set(PRIMITIVES))

    def test_owner_reads_only_spoken_words(self):
        plan = {"title": "t", "lines": [
            {"section": "claim", "text": "AI doesn't decide who gets hired.", "emphasis": "AI",
             "visual": "dot_field", "label": "RANDOM"},
            {"section": "claim", "text": "Systems do.", "emphasis": "Systems",
             "visual": "grid", "label": "DECIDED"},
        ]}
        self.assertEqual(script_text(plan), "AI doesn't decide who gets hired.\nSystems do.")


if __name__ == "__main__":
    unittest.main()
