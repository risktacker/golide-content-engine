import json
import tempfile
import unittest
from pathlib import Path

from golide_engine.feedback.engine import FeedbackEngine
from golide_engine.storage.database import Database, utc_now


class FeedbackTests(unittest.TestCase):
    def test_recalculates_only_after_minimum_sample(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Database(Path(temp) / "db.sqlite3")
            database.initialize()
            for index, views in enumerate((100, 120, 140), 1):
                spec = {"id": f"p{index}", "format": "short", "title": "x", "concept": {"family": "science"}, "generation_parameters": {"hook_type": "question"}, "release": {}}
                database.upsert_production(spec)
                database.execute("UPDATE productions SET youtube_video_id=? WHERE production_id=?", (f"v{index}", f"p{index}"))
                database.execute(
                    """INSERT INTO analytics_daily(day,youtube_video_id,production_id,views,engaged_views,likes,comments,shares,subscribers_gained,subscribers_lost,average_view_duration,average_view_percentage,estimated_revenue,raw_json,collected_at)
                       VALUES ('2026-09-08',?,?,?,?,0,0,0,1,0,30,80,0.1,'{}',?)""",
                    (f"v{index}", f"p{index}", views, views // 2, utc_now()),
                )
            engine = FeedbackEngine(database, minimum_sample=3)
            self.assertEqual(1, engine.recalculate())
            self.assertGreaterEqual(engine.adjustment("short", {"hook_type": "question"}), -1)
