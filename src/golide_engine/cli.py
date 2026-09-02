import argparse
from datetime import date
import json
import os
from pathlib import Path
import shutil

from .manifest import load_project, validate_assets
from .render import render
from .pipeline import build_plan
from .scoring import score_concept
from .animatic import render_animatic


def _database(path: str):
    from .storage.database import Database
    database = Database(path)
    database.initialize()
    return database


def main() -> int:
    parser = argparse.ArgumentParser(prog="golide")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "render"):
        item = sub.add_parser(command)
        item.add_argument("manifest")
    score_parser = sub.add_parser("score")
    score_parser.add_argument("spec")
    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("spec")
    plan_parser.add_argument("--output", default="build")
    animatic_parser = sub.add_parser("animatic")
    animatic_parser.add_argument("storyboard")
    animatic_parser.add_argument("assets")
    animatic_parser.add_argument("--output", default="build/animatic.mp4")
    db_parser = sub.add_parser("db-init")
    db_parser.add_argument("--database", default="data/golide.sqlite3")
    oauth_parser = sub.add_parser("oauth-bootstrap")
    oauth_parser.add_argument("client_secrets")
    oauth_parser.add_argument("--token", default=".secrets/youtube-token.json")
    verify_parser = sub.add_parser("youtube-verify")
    verify_parser.add_argument("--token", default=".secrets/youtube-token.json")
    analytics_parser = sub.add_parser("analytics-collect")
    analytics_parser.add_argument("--database", default="data/golide.sqlite3")
    analytics_parser.add_argument("--token", default=".secrets/youtube-token.json")
    analytics_parser.add_argument("--start")
    analytics_parser.add_argument("--end")
    analytics_sync_parser = sub.add_parser("analytics-sync-studio")
    analytics_sync_parser.add_argument("--database", default="data/golide.sqlite3")
    analytics_sync_parser.add_argument("--token", default=".secrets/youtube-token.json")
    feedback_parser = sub.add_parser("feedback-recalculate")
    feedback_parser.add_argument("--database", default="data/golide.sqlite3")
    voice_verify_parser = sub.add_parser("voice-verify")
    voice_verify_parser.add_argument("--config", default="config/providers.json")
    production_parser = sub.add_parser("production-run")
    production_parser.add_argument("spec")
    production_parser.add_argument("--database", default="data/golide.sqlite3")
    release_parser = sub.add_parser("release-verify")
    release_parser.add_argument("package_directory")
    upload_parser = sub.add_parser("youtube-upload")
    upload_parser.add_argument("package_directory")
    upload_parser.add_argument("--database", default="data/golide.sqlite3")
    upload_parser.add_argument("--token", default=".secrets/youtube-token.json")
    automation_parser = sub.add_parser("automation-run")
    automation_parser.add_argument("--queue", default="production-queue")
    automation_parser.add_argument("--database", default="data/golide.sqlite3")
    automation_parser.add_argument("--token", default=".secrets/youtube-token.json")
    args = parser.parse_args()

    if args.command == "db-init":
        database = _database(args.database)
        print(database.path)
        return 0

    if args.command == "oauth-bootstrap":
        from .youtube.auth import bootstrap
        print(bootstrap(args.client_secrets, args.token))
        return 0

    if args.command == "youtube-verify":
        from .youtube.auth import assert_channel, credentials, services
        youtube, _ = services(credentials(args.token))
        channel = assert_channel(youtube, "UCqaXVBSBz7iQsRHOupKt-3w")
        print(json.dumps({"channel_id": channel["id"], "title": channel["snippet"]["title"]}, indent=2))
        return 0

    if args.command == "analytics-collect":
        from .youtube.analytics import AnalyticsCollector
        from .youtube.auth import assert_channel, credentials, services
        database = _database(args.database)
        youtube, analytics = services(credentials(args.token))
        assert_channel(youtube, "UCqaXVBSBz7iQsRHOupKt-3w")
        collector = AnalyticsCollector(analytics, database)
        count = collector.collect(date.fromisoformat(args.start), date.fromisoformat(args.end)) if args.start and args.end else collector.collect_daily()
        print(json.dumps({"rows_collected": count}))
        return 0

    if args.command == "analytics-sync-studio":
        from .studio_analytics import build_studio_analytics_payload
        from .studio_bridge import StudioBridge
        from .youtube.auth import assert_channel, credentials, services
        studio_url = os.getenv("GOLIDE_STUDIO_BASE_URL", "").strip()
        if not studio_url:
            raise RuntimeError("GOLIDE_STUDIO_BASE_URL is required")
        database = _database(args.database)
        youtube, _ = services(credentials(args.token))
        channel_id = "UCqaXVBSBz7iQsRHOupKt-3w"
        assert_channel(youtube, channel_id)
        payload = build_studio_analytics_payload(database, youtube, channel_id)
        StudioBridge(studio_url).sync_analytics(payload)
        print(json.dumps({
            "status": "studio_analytics_synced",
            "daily": len(payload["daily"]),
            "videos": len(payload["videos"]),
        }))
        return 0

    if args.command == "feedback-recalculate":
        from .feedback.engine import FeedbackEngine
        print(json.dumps({"factors_updated": FeedbackEngine(_database(args.database)).recalculate()}))
        return 0

    if args.command == "voice-verify":
        from .providers.registry import ProviderRegistry
        result = ProviderRegistry(args.config).voice().validate_voice()
        print(json.dumps({"status": "verified", **result}, indent=2))
        return 0

    if args.command == "production-run":
        from .orchestration.production import ProductionService
        database = _database(args.database)
        print(ProductionService(Path.cwd(), database).run(args.spec))
        return 0

    if args.command == "release-verify":
        from .release.package import ReleasePackager
        failures = ReleasePackager.verify(args.package_directory)
        print(json.dumps({"passed": not failures, "failures": failures}, indent=2))
        return 0 if not failures else 4

    if args.command == "youtube-upload":
        from .youtube.auth import assert_channel, credentials, services
        from .youtube.uploader import YouTubeUploader
        root = Path(args.package_directory)
        package = json.loads((root / "package-manifest.json").read_text(encoding="utf-8"))
        files = package["files"]
        metadata = json.loads((root / files["metadata"]["file"]).read_text(encoding="utf-8"))
        database = _database(args.database)
        youtube, _ = services(credentials(args.token))
        assert_channel(youtube, "UCqaXVBSBz7iQsRHOupKt-3w")
        uploader = YouTubeUploader(youtube, database, "UCqaXVBSBz7iQsRHOupKt-3w")
        release = package["release"]
        video_id = uploader.upload_private(package["production_id"], root / files["video"]["file"], root / files["thumbnail"]["file"], metadata, release)
        if release.get("scheduled_at"):
            uploader.schedule(package["production_id"], video_id, release["scheduled_at"], release)
        print(json.dumps({"youtube_video_id": video_id, "scheduled_at": release.get("scheduled_at")}, indent=2))
        return 0

    if args.command == "automation-run":
        from .orchestration.production import ProductionService
        from .orchestration.queue import due_specs
        from .youtube.auth import assert_channel, credentials, services
        from .youtube.uploader import YouTubeUploader
        database = _database(args.database)
        bridge = None
        studio_url = os.getenv("GOLIDE_STUDIO_BASE_URL", "").strip()
        if studio_url:
            from .studio_bridge import StudioBridge
            bridge = StudioBridge(studio_url)

        from .orchestration.schedule import materialize_due
        created = materialize_due(
            args.queue, "config/automation-schedule.json"
        )
        for created_path in created:
            created_spec = json.loads(created_path.read_text(encoding="utf-8"))
            created_spec["_studio_job_id"] = created_spec["id"]
            created_path.write_text(
                json.dumps(created_spec, indent=2) + "\n", encoding="utf-8"
            )
            if bridge:
                try:
                    bridge.register(created_spec)
                except Exception as exc:
                    print(json.dumps({
                        "status": "studio_telemetry_unavailable",
                        "operation": "register",
                        "error": str(exc),
                    }))

        if bridge:
            try:
                claimed = bridge.claim_next()
            except Exception as exc:
                claimed = None
                print(json.dumps({
                    "status": "studio_telemetry_unavailable",
                    "operation": "claim",
                    "error": str(exc),
                }))
            if claimed:
                queue_root = Path(args.queue)
                queue_root.mkdir(parents=True, exist_ok=True)
                claimed_path = queue_root / f"{claimed['jobId']}.json"
                if not claimed_path.exists():
                    claimed_path.write_text(
                        json.dumps(claimed["spec"], indent=2) + "\n", encoding="utf-8"
                    )
        due = due_specs(args.queue)
        if not due:
            print(json.dumps({"status": "no_due_production"}))
            return 0
        spec_path = due[0]
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        studio_job_id = spec.get("_studio_job_id")
        if bridge and studio_job_id:
            try:
                bridge.register(spec)
            except Exception as exc:
                print(json.dumps({
                    "status": "studio_telemetry_unavailable",
                    "operation": "register-existing",
                    "error": str(exc),
                }))
        youtube, _ = services(credentials(args.token))
        assert_channel(youtube, "UCqaXVBSBz7iQsRHOupKt-3w")
        from .operations.budget import BudgetPaused
        from .youtube.demand import TopicDemandRejected
        service = None

        def report_studio(status: str, stage: str, error: str | None = None) -> None:
            if not bridge or not studio_job_id or service is None:
                return
            voice_rows = database.rows(
                "SELECT COALESCE(SUM(characters), 0) characters FROM cost_events WHERE production_id=? AND provider='elevenlabs'",
                (spec["id"],),
            )
            run_url = None
            if os.getenv("GITHUB_RUN_ID"):
                run_url = (
                    f"{os.getenv('GITHUB_SERVER_URL', 'https://github.com')}/"
                    f"{os.getenv('GITHUB_REPOSITORY', 'risktacker/golide-content-engine')}/"
                    f"actions/runs/{os.getenv('GITHUB_RUN_ID')}"
                )
            try:
                bridge.report(
                    studio_job_id,
                    status=status,
                    stage=stage,
                    actual_cost_usd=service.costs.total(spec["id"]),
                    openai_cost_usd=service.costs.provider_total(spec["id"], "openai"),
                    elevenlabs_cost_usd=service.costs.provider_total(spec["id"], "elevenlabs"),
                    elevenlabs_characters=int(voice_rows[0]["characters"]),
                    run_url=run_url,
                    error=error,
                )
            except Exception as exc:
                print(json.dumps({
                    "status": "studio_telemetry_unavailable",
                    "operation": "report",
                    "error": str(exc),
                }))

        def stage_listener(
            production_id: str, stage_status: str, stage: str, error: str | None
        ) -> None:
            mapped = {
                "running": "running",
                "completed": "running",
                "paused_funds": "paused_funds",
                "failed": "failed",
            }[stage_status]
            report_studio(mapped, stage, error)

        service = ProductionService(
            Path.cwd(), database, youtube=youtube, stage_listener=stage_listener
        )
        report_studio("running", "production-started")
        try:
            service.run(spec_path)
        except BudgetPaused as exc:
            report_studio("paused_funds", "funding-check", str(exc))
            print(json.dumps({
                "status": "paused_funds",
                "production_id": spec["id"],
                "provider": exc.provider,
                "required_usd": exc.required_usd,
                "remaining_usd": exc.remaining_usd,
                "resume": "automatic_from_checkpoint_after_recharge",
            }))
            return 0
        except TopicDemandRejected as exc:
            report_studio("topic_rejected", "platform-demand", str(exc))
            database.execute(
                "UPDATE productions SET status='topic_rejected', updated_at=datetime('now') WHERE production_id=?",
                (spec["id"],),
            )
            rejected = spec_path.with_suffix(".topic-rejected.json")
            spec_path.rename(rejected)
            print(json.dumps({
                "status": "topic_rejected",
                "production_id": spec["id"],
                "reason": str(exc),
                "next_action": "select_next_evidence_valid_trending_candidate",
            }))
            return 0
        except Exception as exc:
            report_studio("failed", "production-failed", str(exc))
            raise
        package_root = Path("release-packages") / spec["id"]
        package = json.loads((package_root / "package-manifest.json").read_text(encoding="utf-8"))
        files = package["files"]
        metadata = json.loads((package_root / files["metadata"]["file"]).read_text(encoding="utf-8"))
        uploader = YouTubeUploader(youtube, database, "UCqaXVBSBz7iQsRHOupKt-3w")
        release = package["release"]
        video_id = uploader.upload_private(spec["id"], package_root / files["video"]["file"], package_root / files["thumbnail"]["file"], metadata, release)
        if release.get("scheduled_at"):
            uploader.schedule(spec["id"], video_id, release["scheduled_at"], release)
        done = spec_path.with_suffix(".completed.json")
        spec_path.rename(done)
        report_studio("scheduled", "youtube-scheduled")
        # A successful private upload and schedule is the durable checkpoint. Remove
        # paid working media so runner caches stay small; paused jobs retain theirs.
        for directory in ("productions", "build", "release-packages"):
            shutil.rmtree(Path(directory) / spec["id"], ignore_errors=True)
        print(json.dumps({"status": "scheduled", "production_id": spec["id"], "youtube_video_id": video_id}))
        return 0

    if args.command == "animatic":
        output = render_animatic(Path(args.storyboard).resolve(), Path(args.assets).resolve(), Path(args.output).resolve())
        print(output)
        return 0

    if args.command in {"score", "plan"}:
        spec_path = Path(args.spec).resolve()
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        if args.command == "score":
            result = score_concept(spec["format"], spec["concept"]["scores"])
            print(json.dumps({"score": result.total, "verdict": result.verdict, "blockers": result.blockers}, indent=2))
            return 0 if result.verdict != "reject" else 3
        plan = build_plan(spec, Path(args.output).resolve())
        print(json.dumps({"score": plan.score, "verdict": plan.verdict, "output": plan.output_directory}, indent=2))
        return 0

    project = load_project(args.manifest)
    missing = validate_assets(project)
    if missing:
        print("Missing assets:")
        for path in missing:
            print(f"- {path}")
        return 2
    if args.command == "validate":
        print(f"Valid: {project.id} ({project.format}, {len(project.scenes)} scenes)")
        return 0
    output = render(project, Path.cwd())
    print(output)
    return 0
