import unittest

from golide_engine.thumbnail import validate_thumbnail


class ThumbnailPolicyTests(unittest.TestCase):
    def test_locked_wordless_thumbnail_passes(self):
        self.assertEqual([], validate_thumbnail({
            "text": "", "focal_subject": "paper avatar",
            "topic_object_or_consequence": "one flipped memory bit", "duplicates_title": False,
        }))

    def test_any_thumbnail_words_are_rejected(self):
        problems = validate_thumbnail({
            "text": "HOW?", "focal_subject": "paper avatar",
            "topic_object_or_consequence": "one flipped memory bit",
        })
        self.assertIn("thumbnail must not contain words or typography", problems)


if __name__ == "__main__":
    unittest.main()
