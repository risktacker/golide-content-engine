"""Trend pulse (owner direction 2026-10-17): fresh, rising stories with science underneath win."""

import unittest
from datetime import datetime, timedelta, timezone

from golide_engine.youtube.demand import DemandResult, TopicDemandRejected
from golide_engine.youtube.pulse import HOT_SCORE, attach, choose, hot_first, score_pulse

NOW = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)


class _Call:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class FakeYouTube:
    """Fresh videos: 'tesla' has many fast-rising ones; 'tablet' has few slow ones."""

    def __init__(self):
        self.videos_by_query = {
            "tesla roadster physics": [(f"t{i}", 400_000 + i * 50_000, 10 + i) for i in range(8)],
            "amazon tablet": [("a1", 2_000, 40)],
        }
        self._last = []

    def search(self):
        outer = self

        class S:
            def list(self, **kw):
                outer._last = outer.videos_by_query.get(kw["q"], [])
                return _Call({"items": [{"id": {"videoId": vid}} for vid, _, _ in outer._last]})
        return S()

    def videos(self):
        outer = self

        class V:
            def list(self, **kw):
                items = []
                for vid, views, hours in outer._last:
                    published = (NOW - timedelta(hours=hours)).isoformat().replace("+00:00", "Z")
                    items.append({"id": vid, "statistics": {"viewCount": str(views)},
                                  "snippet": {"publishedAt": published}})
                return _Call({"items": items})
        return V()


class Gate:
    def __init__(self, fail_hot=False):
        self.fail_hot = fail_hot

    def select(self, spec):
        cands = spec["topic_candidates"]
        if self.fail_hot and len(cands) == 1:
            raise TopicDemandRejected("no")
        best = cands[-1]  # the plain demand ranking would pick the last one
        return best, DemandResult(best["query"], 90, "pass", 1, 1, 1, 1, 1, "now")


class PulseTests(unittest.TestCase):
    def setUp(self):
        self.cands = [
            {"title": "Tesla Roadster jets", "query": "tesla roadster physics", "science_angle": "thrust and grip"},
            {"title": "Amazon tablet", "query": "amazon tablet", "science_angle": ""},
        ]
        attach(FakeYouTube(), self.cands, NOW)

    def test_fresh_rising_story_with_science_is_hot(self):
        tesla, tablet = self.cands
        self.assertTrue(tesla["trend_pulse"]["hot"])
        self.assertGreaterEqual(tesla["trend_pulse"]["score"], HOT_SCORE)
        self.assertFalse(tablet["trend_pulse"]["hot"])
        self.assertEqual([c["title"] for c in hot_first(self.cands)], ["Tesla Roadster jets"])

    def test_live_trend_wins_selection(self):
        chosen, _ = choose(Gate(), {"topic_candidates": self.cands, "format": "long"})
        self.assertEqual(chosen["title"], "Tesla Roadster jets")

    def test_falls_back_to_the_usual_ranking(self):
        chosen, _ = choose(Gate(fail_hot=True), {"topic_candidates": self.cands, "format": "long"})
        self.assertEqual(chosen["title"], "Amazon tablet")

    def test_signal_outage_never_blocks(self):
        class Broken:
            def search(self):
                raise RuntimeError("quota")
        cands = [{"title": "x", "query": "x", "science_angle": "y"}]
        attach(Broken(), cands, NOW)
        self.assertNotIn("trend_pulse", cands[0])

    def test_score_shape(self):
        self.assertLess(score_pulse(1, 50, 50, False), score_pulse(8, 20_000, 60_000, True))


class PromptTests(unittest.TestCase):
    def test_schema_asks_for_freshness_and_science(self):
        from golide_engine.orchestration.schemas import TREND_CANDIDATES_SCHEMA

        req = TREND_CANDIDATES_SCHEMA["properties"]["candidates"]["items"]["required"]
        self.assertIn("broke_on", req)
        self.assertIn("science_angle", req)


if __name__ == "__main__":
    unittest.main()
