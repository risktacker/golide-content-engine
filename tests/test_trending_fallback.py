import inspect
import unittest

from golide_engine.orchestration import production
from golide_engine.orchestration.schemas import TREND_CANDIDATES_SCHEMA


class TrendingFallbackContractTests(unittest.TestCase):
    def test_candidate_schema_requires_authoritative_source(self):
        candidate = TREND_CANDIDATES_SCHEMA["properties"]["candidates"]["items"]
        self.assertIn("authoritative_source_url", candidate["required"])
        self.assertEqual(3, TREND_CANDIDATES_SCHEMA["properties"]["candidates"]["minItems"])

    def test_production_fallback_is_budgeted_checkpointed_and_original(self):
        source = inspect.getsource(production.ProductionService.run)
        self.assertIn('self.runner.run(\n                    production_id, "trend-candidates"', source)
        self.assertIn('stage="trend-candidates"', source)
        # 2026-10-21: YouTube decides the topic; titles are modelled on the breakout.
        self.assertIn("find_breakouts(self.youtube, fmt)", source)
        self.assertIn("BREAKOUT_RULES", source)
        self.assertIn("candidate, demand = gate.select(spec)", source)
        self.assertIn('"platform_seed_demand" not in item', source)


class BreakoutTests(unittest.TestCase):
    """2026-10-21: the topic comes from YouTube videos taking numbers right now."""

    def _youtube(self):
        from types import SimpleNamespace as NS

        now = "2026-10-21T00:00:00Z"
        videos = {
            "a": {"id": "a", "snippet": {"title": "The NEW Tesla Roadster: My Honest Reaction", "channelId": "big",
                                         "channelTitle": "Big", "publishedAt": now, "categoryId": "28"},
                  "statistics": {"viewCount": "1100000"}, "contentDetails": {"duration": "PT12M"}},
            "b": {"id": "b", "snippet": {"title": "Tiny Vehicles Smarter Than Your Bike", "channelId": "small",
                                         "channelTitle": "Small", "publishedAt": now, "categoryId": "28"},
                  "statistics": {"viewCount": "170000"}, "contentDetails": {"duration": "PT8M30S"}},
            "c": {"id": "c", "snippet": {"title": "Top 10 songs", "channelId": "big", "channelTitle": "Big",
                                         "publishedAt": now, "categoryId": "10"}, "statistics": {"viewCount": "9000000"},
                  "contentDetails": {"duration": "PT3M"}},
        }
        channels = {"big": {"id": "big", "statistics": {"viewCount": "5000000000", "videoCount": "1000",
                                                        "subscriberCount": "20000000"}},
                    "small": {"id": "small", "statistics": {"viewCount": "100000", "videoCount": "50",
                                                            "subscriberCount": "2700"}}}
        run = lambda value: NS(execute=lambda: value)  # noqa: E731
        return NS(
            search=lambda: NS(list=lambda **kw: run({"items": [{"id": {"videoId": k}} for k in videos]})),
            videos=lambda: NS(list=lambda id, **kw: run({"items": [videos[i] for i in id.split(",")]})),
            channels=lambda: NS(list=lambda id, **kw: run({"items": [channels[i] for i in id.split(",")]})),
        )

    def test_breakouts_rank_momentum_and_small_channel_hits_and_skip_music(self):
        from datetime import datetime, timezone

        from golide_engine.youtube.breakouts import find_breakouts

        found = find_breakouts(self._youtube(), now=datetime(2026, 10, 21, 10, tzinfo=timezone.utc),
                               queries=("tesla",))
        titles = [b["title"] for b in found]
        self.assertNotIn("Top 10 songs", titles)
        small = next(b for b in found if b["channel"] == "Small")
        self.assertGreater(small["breakout"], 50)           # 170k against a 2k average

    def test_a_breakout_candidate_wins_and_carries_its_title(self):
        from golide_engine.youtube.pulse import choose

        spec = {"format": "long", "topic_candidates": [
            {"title": "News story", "evidence_valid": True, "query": "news"},
            {"title": "Tesla Roadster", "model_title": "The NEW Tesla Roadster: How It Actually Flies",
             "evidence_valid": True, "query": "tesla roadster",
             "breakout": {"title": "The NEW Tesla Roadster: My Honest Reaction", "score": 80, "views_per_hour": 100000}},
        ]}
        candidate, demand = choose(gate=None, spec=spec)
        self.assertEqual("The NEW Tesla Roadster: How It Actually Flies", candidate["model_title"])
        self.assertEqual("pass", demand.verdict)
        self.assertEqual("youtube-breakout-v1", demand.signal_type)
