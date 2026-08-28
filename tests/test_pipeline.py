import tempfile
import unittest
from pathlib import Path

from golide_engine.pipeline import STAGES, build_plan
from golide_engine.scoring import SHORT_WEIGHTS


class PipelineTests(unittest.TestCase):
    def test_build_plan_creates_all_stage_folders(self):
        spec = {"id": "proof", "format": "short", "concept": {"scores": {key: 8 for key in SHORT_WEIGHTS}}}
        with tempfile.TemporaryDirectory() as directory:
            plan = build_plan(spec, Path(directory))
            self.assertEqual(plan.verdict, "produce")
            self.assertTrue((Path(plan.output_directory) / "plan.json").exists())
            for stage in STAGES:
                if stage not in {"concept_scoring", "human_qa"}:
                    self.assertTrue((Path(plan.output_directory) / stage).is_dir())


if __name__ == "__main__":
    unittest.main()
