"""Owner direction 2026-10-23: scripts sound like the owner, not a spec sheet; pictures
show what the real product looks like, even a brand-new one."""
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from golide_engine.engine.content_rules import jargon_problems, owner_voice, script_instructions
from golide_engine.orchestration import production

SPEC_SHEET = ["Each uses a camera, LiDAR for distance, and two IMUs,",
              "motion sensors that track movement and rotation, onboard computing, and fifteen motors.",
              "Engineers train it in simulation, export an ONNX model,", "then run it onboard."]
PLAIN = ["Each one has a camera, a laser that measures distance, motion sensors that feel every tilt,",
         "and fifteen small motors.", "Engineers let them practise thousands of times inside a simulation."]
TITLE = "NVIDIA CEO Jensen Huang Reveals Tiny AI Robots at GTC Berlin 2026"


class VoiceTests(unittest.TestCase):
    def test_the_script_writer_hears_the_owner(self):
        voice = owner_voice()
        self.assertIn("That's the fans.", voice)                 # approved Roadster script
        self.assertIn("would you trust one of these in your home", voice)
        for fmt in ("short", "long"):
            self.assertIn("THE OWNER'S VOICE", script_instructions(fmt, "golide-short-2026-10-24"))

    def test_spec_sheet_jargon_is_sent_back(self):
        lines = lambda xs: {"lines": [{"text": x} for x in xs]}  # noqa: E731
        self.assertTrue(jargon_problems(lines(SPEC_SHEET), TITLE, "short"))
        self.assertEqual([], jargon_problems(lines(PLAIN), TITLE, "short"))

    def test_names_in_the_title_and_everyday_acronyms_are_fine(self):
        text = {"lines": [{"text": "NVIDIA showed AI robots to a CEO in the US and the UK on TV."}]}
        self.assertEqual([], jargon_problems(text, TITLE, "short"))

    def test_jargon_check_runs_on_every_script(self):
        self.assertIn("jargon_problems(plan", inspect.getsource(production.ProductionService.run))


class RealLookTests(unittest.TestCase):
    def test_storyboard_gets_the_story_the_source_and_a_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "research.json").write_text(json.dumps({
                "summary": "NVIDIA showed Microduck, a 25 cm two-legged robot.",
                "claims": [{"claim": "Each Microduck has a camera and fifteen motors."}]}))
            spec = {"source_breakout": {"title": "NVIDIA CEO Jensen Huang Shows Off Tiny AI Robots",
                                        "description": "Microduck robots walk on stage"}}
            facts = production.ProductionService._storyboard_facts(spec, work)
        self.assertIn("TRENDING VIDEO THIS MODELS: NVIDIA CEO Jensen Huang Shows Off Tiny AI Robots", facts)
        self.assertIn("STORY: NVIDIA showed Microduck", facts)
        self.assertIn("- Each Microduck has a camera and fifteen motors.", facts)
        self.assertIn("use web search to see what it actually looks like", facts)

    def test_storyboard_may_search_the_web(self):
        source = inspect.getsource(production.ProductionService.run)
        self.assertIn("facts = self._storyboard_facts(spec, work)", source)
        self.assertIn('"visual-plan-search"', source)


if __name__ == "__main__":
    unittest.main()
