import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from golide_engine.storage.database import Database
from golide_engine.youtube.demand import TopicDemandRejected, YouTubeDemandGate


class Call:
    def __init__(self, payload):
        self.payload = payload
    def execute(self):
        return self.payload


class Resource:
    def __init__(self, handler):
        self.handler = handler
    def list(self, **kwargs):
        return Call(self.handler(kwargs))


class YouTube:
    def __init__(self, strong=True):
        self.strong = strong
    def search(self):
        def result(kwargs):
            count = 6 if self.strong else 0
            return {"items": [
                {"id": {"videoId": f"{kwargs['regionCode']}-{i}"},
                 "snippet": {"title": "Quantum battery breakthrough explained"}}
                for i in range(count)
            ]}
        return Resource(result)
    def videos(self):
        def result(kwargs):
            if kwargs.get("chart") == "mostPopular":
                return {"items": []}
            return {"items": [
                {"id": video_id,
                 "statistics": {"viewCount": "250000"},
                 "snippet": {
                     "title": "Quantum battery breakthrough explained",
                     "publishedAt": "2026-08-20T00:00:00Z",
                 }}
                for video_id in kwargs["id"].split(",")
            ]}
        return Resource(result)


class DemandGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "db.sqlite3")
        self.db.initialize()
        self.now = datetime(2026, 9, 1, tzinfo=timezone.utc)

    def tearDown(self):
        self.temp.cleanup()

    def test_strong_platform_signal_passes_and_is_cached(self):
        gate = YouTubeDemandGate(YouTube(True), self.db, now=self.now)
        result = gate.evaluate("quantum battery breakthrough", "short")
        self.assertEqual("pass", result.verdict)
        self.assertEqual(4, result.market_coverage)
        cached = gate.evaluate("quantum battery breakthrough", "short")
        self.assertEqual(result, cached)

    def test_current_popular_seeds_can_supply_transparent_fallback_signal(self):
        gate = YouTubeDemandGate(YouTube(False), self.db, now=self.now)
        seeds = [
            {
                "title": "Quantum battery breakthrough explained",
                "markets": ["US", "GB", "IN", "ZA"],
                "views_per_day": 250000,
            }
            for _ in range(20)
        ]
        seed_result = gate.evaluate_trending_candidate(
            "quantum battery breakthrough", "long", seeds
        )
        self.assertEqual("pass", seed_result.verdict)
        self.assertEqual("youtube-most-popular-seed-proxy", seed_result.signal_type)
        spec = {
            "format": "long",
            "brief": "quantum battery",
            "topic_candidates": [{
                "title": "Quantum battery",
                "query": "quantum battery breakthrough",
                "brief": "quantum battery",
                "evidence_valid": True,
                "platform_seed_demand": seed_result.__dict__,
            }],
        }
        _, selected = gate.select(spec)
        self.assertEqual(seed_result, selected)

    def test_weak_signal_is_rejected(self):
        gate = YouTubeDemandGate(YouTube(False), self.db, now=self.now)
        spec = {
            "format": "long",
            "brief": "unknown event",
            "topic_candidates": [{
                "title": "Unknown event",
                "query": "unknown event",
                "brief": "unknown event",
                "evidence_valid": True,
            }],
        }
        with self.assertRaises(TopicDemandRejected):
            gate.select(spec)

    def test_evidence_gate_runs_before_demand(self):
        gate = YouTubeDemandGate(YouTube(True), self.db, now=self.now)
        with self.assertRaises(TopicDemandRejected):
            gate.select({
                "format": "short",
                "brief": "claim",
                "topic_candidates": [{"title": "claim", "evidence_valid": False}],
            })
