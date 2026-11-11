import unittest

from golide_engine.edit import pipeline


class StyleChoiceTest(unittest.TestCase):
    def test_owner_choice_wins(self):
        self.assertTrue(pipeline.enabled("long", {"video_style": "goli"}))
        self.assertFalse(pipeline.enabled("short", {"video_style": "illustration"}))

    def test_default_per_format(self):
        self.assertEqual(pipeline.enabled("short", {}), bool(pipeline.settings().get("short")))
        self.assertEqual(pipeline.enabled("long", None), bool(pipeline.settings().get("long")))


if __name__ == "__main__":
    unittest.main()
