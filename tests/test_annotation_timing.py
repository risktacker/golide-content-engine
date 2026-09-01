import unittest

from golide_engine.orchestration.production import ProductionService


class AnnotationTimingTests(unittest.TestCase):
    def test_annotation_is_clamped_inside_short_narration_beat(self):
        value = ProductionService._fit_annotation(
            {
                "kind": "label",
                "text": "SURGE",
                "start_offset": 1.4,
                "duration": 2.0,
            },
            1.5,
        )
        self.assertGreater(value["duration"], 0)
        self.assertLessEqual(
            value["start_offset"] + value["duration"],
            1.5,
        )

    def test_none_annotation_is_preserved(self):
        self.assertEqual(
            {"kind": "none"},
            ProductionService._fit_annotation({"kind": "none"}, 0.2),
        )


if __name__ == "__main__":
    unittest.main()
