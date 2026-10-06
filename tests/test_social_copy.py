import unittest

from golide_engine.engine.social_copy import X_LIMIT, fit_x, strip_citations, x_length

TODAY = ("Prompting isn't the advantage. Building is.\n\nBasic AI skill demand fell 25%, while hands-on AI "
         "building and workflow automation rose 51% in Workday's latest report. Learn to connect AI to real "
         "work, then test the result. ([newsroom.workday.com](https://newsroom.workday.com/2026-10-05-Workday"
         "-Global-Workforce-Report?utm_source=openai))")


class SocialCopyTests(unittest.TestCase):
    def test_markdown_citations_are_removed(self):
        clean = strip_citations(TODAY)
        self.assertNotIn("](", clean)
        self.assertNotIn("utm_source", clean)
        self.assertTrue(clean.endswith("then test the result."))

    def test_plain_links_survive_without_tracking(self):
        self.assertEqual(strip_citations("Try it https://marketplace.golidee.com/jobsearch?utm_source=openai"),
                         "Try it https://marketplace.golidee.com/jobsearch")

    def test_x_copy_is_fitted_at_a_sentence(self):
        long = strip_citations(TODAY) + " " + "This sentence keeps going to push the post over the limit. " * 3
        fitted = fit_x(long + "\n\nhttps://marketplace.golidee.com/jobsearch")
        self.assertLessEqual(x_length(fitted), X_LIMIT)
        self.assertTrue(fitted.endswith("https://marketplace.golidee.com/jobsearch"))
        self.assertIn("then test the result.", fitted)

    def test_links_count_as_twenty_three(self):
        self.assertEqual(x_length("a https://example.com/" + "x" * 200), 2 + 23)


if __name__ == "__main__":
    unittest.main()
