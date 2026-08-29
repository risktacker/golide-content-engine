import unittest

from golide_engine.animatic import ALIASES


class AnimaticTests(unittest.TestCase):
    def test_aliases_point_to_reusable_master_assets(self):
        self.assertEqual(ALIASES["bit-cell"], "healthy-chip-wrong-data")
        self.assertEqual(ALIASES["chip-cutaway"], "charge-bloom")


if __name__ == "__main__":
    unittest.main()
