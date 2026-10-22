import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from golide_engine.orchestration.rebuild import Rebuild, RebuildError
from golide_engine.orchestration.studio_social import StudioSocialPublisher
from golide_engine.storage.database import Database

PLAN = {"title": "t", "lines": [
    {"section": "claim", "text": "Heat is the limit.", "emphasis": "Heat", "visual": "icon_hero",
     "subjects": ["flame"], "label": "A"},
    {"section": "cta", "text": "Watch the heat.", "emphasis": "heat", "visual": "logo_end",
     "subjects": [], "label": ""},
]}
ID = "golide-short-2026-10-05"


class FakeStore:
    def __init__(self):
        self.uploads = []

    def upload_bytes(self, **kwargs):
        self.uploads.append(kwargs)
        return type("U", (), {"media_ref": "r2://temp/x/clip.mp4",
                              "expires_at": datetime.now(timezone.utc) + timedelta(hours=72)})()

    def resolve(self, ref, expires_seconds=3600):
        return f"https://signed.example/{ref[5:]}?ttl={expires_seconds}"


class FakeService:
    """Stands in for ProductionService.run: writes the release package."""

    def __init__(self, root: Path):
        self.root = root
        self.runs = 0

    def run(self, spec_path):
        self.runs += 1
        pkg = self.root / "release-packages" / ID
        pkg.mkdir(parents=True)
        (pkg / "video.mp4").write_bytes(b"video")
        (pkg / "thumbnail.png").write_bytes(b"png")
        (pkg / "upload-metadata.json").write_text(json.dumps({"title": "Cooling", "description": "Why."}))
        (pkg / "package-manifest.json").write_text(json.dumps({
            "release": {"approved": True, "scheduled_at": "2026-10-05T11:00:00Z"},
            "files": {"video": {"file": "video.mp4"}, "thumbnail": {"file": "thumbnail.png"},
                      "metadata": {"file": "upload-metadata.json"}},
        }))


class RebuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "production-queue").mkdir()
        (self.root / "production-queue" / f"{ID}.completed.json").write_text(json.dumps({
            "id": ID, "title": "Cooling", "format": "short",
            "owner_voice_media_ref": "r2://temp/voice.wav"}))
        work = self.root / "productions" / ID
        work.mkdir(parents=True)
        (work / "script.txt").write_text("Heat is the limit.\nWatch the heat.\n")
        (work / "narration-owner.wav").write_bytes(b"wav")
        (work / "timed-words-owner.json").write_text("[]")
        (work / "thumbnail.png").write_bytes(b"png")
        self.db = Database(self.root / "golide.sqlite3")
        self.db.initialize()
        self.db.upsert_production({"id": ID, "format": "short", "title": "Cooling"}, "uploaded")
        for stage in ("script", "owner-voice", "render-vector-v1", "qa", "release"):
            self.db.execute("INSERT INTO stage_runs(production_id, stage, attempt, status, started_at) "
                            "VALUES (?, ?, 1, 'completed', '2026-10-05')", (ID, stage))
        self.plan = self.root / "plan.json"
        self.plan.write_text(json.dumps(PLAN))

    def tearDown(self):
        self.tmp.cleanup()

    def stages(self):
        return {r["stage"] for r in self.db.rows("SELECT stage FROM stage_runs WHERE production_id=?", (ID,))}

    def test_only_render_onward_is_redone_and_voice_is_kept(self):
        redo = Rebuild(self.root, self.db, ID).prepare(self.plan)
        self.assertEqual(redo, ["render-vector-v1", "qa", "release"])
        self.assertEqual(self.stages(), {"script", "owner-voice"})
        self.assertTrue((self.root / "productions" / ID / "narration-owner.wav").exists())

    def test_new_art_redraws_the_thumbnail_retitles_and_funds_the_pictures(self):
        # 22 Oct: the Roadster video is redrawn with real-product art under the owner's title.
        work = self.root / "productions" / ID
        (work / "upload-metadata.json").write_text(json.dumps({"title": "Apple CEO John Ternus"}))
        (work / "visual-plan.json").write_text("{}")
        self.db.execute("INSERT INTO budget_allocations(production_id, provider, month, budget_class, "
                        "allocated_usd, created_at) VALUES (?, 'openai', '2026-10', 'scheduled', 0.9, 'x')", (ID,))
        self.db.execute("INSERT INTO cost_events(production_id, stage, provider, model, cost_usd, created_at) "
                        "VALUES (?, 'illustrations', 'openai', 'img', 0.67, 'x')", (ID,))
        redo = Rebuild(self.root, self.db, ID).prepare(self.plan, new_art=True,
                                                       title="Elon Musk New Flying Car Explained")
        self.assertIn("thumbnail", redo)
        self.assertIn("illustrations-v1", redo)
        self.assertFalse((work / "thumbnail.png").exists())
        self.assertFalse((work / "visual-plan.json").exists())
        self.assertEqual("Elon Musk New Flying Car Explained",
                         json.loads((work / "upload-metadata.json").read_text())["title"])
        spec = json.loads((self.root / "production-queue" / f"{ID}.completed.json").read_text())
        self.assertEqual("Elon Musk New Flying Car Explained", spec["model_title"])
        allocated = self.db.rows("SELECT allocated_usd FROM budget_allocations WHERE production_id=?", (ID,))
        self.assertAlmostEqual(1.47, float(allocated[0]["allocated_usd"]), places=2)

    def test_plan_with_different_words_is_refused(self):
        bad = json.loads(json.dumps(PLAN))
        bad["lines"][0]["text"] = "Cold is the limit."
        self.plan.write_text(json.dumps(bad))
        with self.assertRaises(RebuildError):
            Rebuild(self.root, self.db, ID).prepare(self.plan)

    def test_preview_then_publish(self):
        rebuild = Rebuild(self.root, self.db, ID)
        store, service, emails = FakeStore(), FakeService(self.root), []
        state = rebuild.build(service=service, store=store, notify=lambda **kw: emails.append(kw),
                              scene_plan=self.plan)
        self.assertEqual(state["status"], "awaiting_approval")
        self.assertEqual(store.uploads[0]["content_type"], "video/mp4")
        self.assertIn("signed.example", emails[0]["preview_url"])

        uploads, created = [], []

        class Uploader:
            def upload_private(self, *args):
                uploads.append(args)
                return "NEWVID"

        class Bridge:
            def create_content(self, payload):
                created.append(payload)
                return {"id": payload["id"]}

        class Publisher:
            def run_due(self):
                return [{"post_id": created[-1]["id"], "status": "published"}]

        result = rebuild.publish(uploader=Uploader(), bridge=Bridge(), publisher_factory=Publisher)
        self.assertEqual(result["status"], "published")
        self.assertEqual(result["youtube_video_id"], "NEWVID")
        platforms = {v["platform"]: v for v in created[0]["variants"]}
        self.assertEqual(set(platforms), {"instagram", "facebook", "linkedin", "youtube"})
        self.assertEqual(platforms["youtube"]["parts"], ["youtube:NEWVID"])
        self.assertEqual(created[0]["content_class"], "short")
        self.assertTrue(created[0]["id"].startswith(f"{ID}-reels-2"))
        # A second publish does not upload to YouTube again.
        with self.assertRaises(RebuildError):
            rebuild.publish(uploader=Uploader(), bridge=Bridge(), publisher_factory=Publisher)
        self.assertEqual(len(uploads), 1)


class ShortYouTubeLegTests(unittest.TestCase):
    def test_youtube_variant_is_recorded_from_its_video_id(self):
        reports = []

        class Bridge:
            def __init__(self):
                self.posts = [{"id": "p1", "status": "publishing", "variants": [
                    {"id": "v1", "platform": "youtube", "media_ref": "", "parts": ["youtube:ABC"]}]}]

            def social_credentials(self, platform):
                raise RuntimeError("not connected")

            def claim_due_social(self, now):
                return self.posts.pop(0) if self.posts else None

            def report_social_variant(self, post_id, variant_id, **kw):
                reports.append(kw)
                return {"status": "published"}

        import golide_engine.orchestration.studio_social as module
        original = module.r2_store_from_environment
        module.r2_store_from_environment = lambda: object()
        try:
            results = StudioSocialPublisher(bridge=Bridge()).run_due()
        finally:
            module.r2_store_from_environment = original
        self.assertEqual(reports[0]["remote_id"], "ABC")
        self.assertEqual(reports[0]["status"], "published")
        self.assertEqual(results[0]["status"], "published")


if __name__ == "__main__":
    unittest.main()


class CoverTests(unittest.TestCase):
    def test_cover_is_a_drawn_frame_not_the_black_start(self):
        import subprocess
        from PIL import Image
        from golide_engine.orchestration.reels import pick_cover

        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "v.mp4"
            # black for 2 s, then a white box (the "drawing") until 6 s
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:s=270x480:d=6:r=10",
                            "-vf", "drawbox=x=60:y=80:w=150:h=150:color=white:t=fill:enable='gte(t,2)'",
                            "-pix_fmt", "yuv420p", str(video)], check=True)
            cover = pick_cover(video, Path(tmp) / "cover.jpg")
            pixels = Image.open(cover).convert("L")
            self.assertGreater(pixels.getpixel((135, 155)), 200)

    def test_instagram_reel_carries_the_cover(self):
        import os
        from unittest.mock import patch
        from golide_engine.providers.base import PublishRequest
        from golide_engine.providers.http import JsonResponse
        from golide_engine.providers.meta import InstagramProvider

        calls = []

        class Http:
            def post(self, url, *, data=None, headers=None):
                calls.append(data)
                return JsonResponse(200, {"id": "c1"} if len(calls) == 1 else {"id": "m1"})

            def get(self, url, *, params=None):
                return JsonResponse(200, {"status_code": "FINISHED"})

        provider = InstagramProvider(api_version="v1", access_token="t", instagram_user_id="ig", http=Http())
        with patch.dict(os.environ, {"GOLIDE_ENABLE_SOCIAL_PUBLISH": "1"}):
            provider.publish(PublishRequest("p", "v", "instagram", "body",
                                            media_ref="https://x/clip.mp4", cover_url="https://x/cover.jpg"))
        self.assertEqual(calls[0]["cover_url"], "https://x/cover.jpg")
        self.assertEqual(calls[0]["media_type"], "REELS")
