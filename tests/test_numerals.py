import unittest

from golide_engine.engine.numerals import digits, plan_digits


class NumeralTests(unittest.TestCase):
    """2026-10-27: scripts show numbers as digits; the owner reads them faster."""

    def test_money_dates_and_counts(self):
        self.assertEqual(digits("about sixteen point three billion dollars"), "about 16.3 billion dollars")
        self.assertEqual(digits("on October twenty-sixth, twenty twenty-six,"), "on October 26th, 2026,")
        self.assertEqual(digits("around five hundred eighteen billion dollars"), "around 518 billion dollars")
        self.assertEqual(digits("four tiny robots, fifteen small motors"), "4 tiny robots, 15 small motors")
        self.assertEqual(digits("twenty-five thousand people"), "25,000 people")
        self.assertEqual(digits("a hundred times"), "100 times")

    def test_one_as_a_word_stays(self):
        for text in ("a one-time charge", "One reported figure", "no one knows", "the first half"):
            self.assertEqual(digits(text), text)

    def test_plan_keeps_emphasis_matching(self):
        plan = {"lines": [{"text": "about sixteen point three billion dollars", "emphasis": "sixteen point three"}]}
        line = plan_digits(plan)["lines"][0]
        self.assertEqual(line["text"], "about 16.3 billion dollars")
        self.assertEqual(line["emphasis"], "16.3")


if __name__ == "__main__":
    unittest.main()
