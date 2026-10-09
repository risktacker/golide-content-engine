import argparse
from datetime import date
import json
import os
from pathlib import Path

from .manifest import load_project, validate_assets
from .render import render
from .pipeline import build_plan
from .scoring import score_concept
from .animatic import render_animatic



# Long videos reach Facebook and LinkedIn from this generate date on (owner, 2026-10-06);
# the 6 Oct video runs unattended on the YouTube-only path it was started with.
LONG_SOCIAL_FROM = "2026-10-07"

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
    retention_parser = sub.add_parser("retention-cleanup")
    retention_parser.add_argument("--database", default="data/golide.sqlite3")
    meta_parser = sub.add_parser("meta-discover")
    meta_parser.add_argument("--api-version", default=os.getenv("GOLIDE_META_API_VERSION", ""))
    meta_parser.add_argument("--token-env", default="META_USER_ACCESS_TOKEN")
    social_status_parser = sub.add_parser("social-status")
    social_status_parser.add_argument("--database", default="data/golide.sqlite3")
    social_publish_parser = sub.add_parser("social-publish-due")
    social_publish_parser.add_argument("--database", default="data/golide.sqlite3")
    social_cleanup_parser = sub.add_parser("social-media-cleanup")
    social_cleanup_parser.add_argument("--database", default="data/golide.sqlite3")
    connection_sync_parser = sub.add_parser("connections-sync-studio")
    connection_sync_parser.add_argument(
        "--platform",
        action="append",
        choices=("instagram", "facebook", "linkedin", "youtube"),
        help="Verify and sync only the selected provider. May be repeated.",
    )
    connection_sync_parser.add_argument(
        "--require-connected",
        action="store_true",
        help="Return a failure exit code when any selected provider is not connected.",
    )
    rebuild_parser = sub.add_parser("rebuild-video")
    rebuild_parser.add_argument("--id", required=True)
    rebuild_parser.add_argument("--step", choices=("preview", "publish"), required=True)
    rebuild_parser.add_argument("--scene-plan", default="")
    rebuild_parser.add_argument("--new-art", action="store_true",
                                help="re-plan the scenes and draw new illustrations (small image cost)")
    rebuild_parser.add_argument("--database", default="data/golide.sqlite3")
    rebuild_parser.add_argument("--token", default=".secrets/youtube-token.json")
    sub.add_parser("static-automation-run")
    sub.add_parser("connection-reminders")
    sub.add_parser("studio-social-publish")
    studio_parser = sub.add_parser("studio-serve")
    studio_parser.add_argument("--database", default="data/golide.sqlite3")
    studio_parser.add_argument("--app-dir", default="app")
    studio_parser.add_argument("--host", default="127.0.0.1")
    studio_parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    if args.command == "db-init":
        database = _database(args.database)
        print(database.path)
        return 0

    if args.command == "meta-discover":
        from .providers.meta import discover_managed_accounts
        api_version = args.api_version.strip()
        token = os.getenv(args.token_env, "").strip()
        if not api_version:
            raise RuntimeError("GOLIDE_META_API_VERSION or --api-version is required")
        if not token:
            raise RuntimeError(f"{args.token_env} is required")
        accounts = discover_managed_accounts(
            api_version=api_version,
            user_access_token=token,
        )
        print(json.dumps({
            "accounts": [
                {
                    "page_id": item.page_id,
                    "page_name": item.page_name,
                    "instagram_user_id": item.instagram_user_id,
                    "tasks": list(item.tasks),
                }
                for item in accounts
            ]
        }, indent=2))
        return 0

    if args.command == "social-status":
        from .db.connections import ConnectionRepository
        from .providers.meta import social_publish_enabled
        database = _database(args.database)
        connections = ConnectionRepository(database).list()
        print(json.dumps({
            "live_publish_enabled": social_publish_enabled(),
            "meta_api_version_configured": bool(os.getenv("GOLIDE_META_API_VERSION", "").strip()),
            "meta_page_token_configured": bool(os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()),
            "instagram_login_token_configured": bool(os.getenv("INSTAGRAM_USER_ACCESS_TOKEN", "").strip()),
            "instagram_id_configured": bool(os.getenv("GOLIDE_INSTAGRAM_USER_ID", "").strip()),
            "facebook_page_id_configured": bool(os.getenv("GOLIDE_FACEBOOK_PAGE_ID", "").strip()),
            "linkedin_token_configured": bool(os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()),
            "linkedin_author_configured": bool(os.getenv("GOLIDE_LINKEDIN_AUTHOR_URN", "").strip()),
            "linkedin_version_configured": bool(os.getenv("GOLIDE_LINKEDIN_VERSION", "").strip()),
            "x_token_configured": bool(os.getenv("X_USER_ACCESS_TOKEN", "").strip()),
            "r2_configured": all(bool(os.getenv(name, "").strip()) for name in (
                "R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"
            )),
            "connections": [
                {
                    "platform": item.platform,
                    "account_label": item.account_label,
                    "external_account_id": item.external_account_id,
                    "transport": item.transport,
                    "status": item.status,
                }
                for item in connections
            ],
        }, indent=2))
        return 0

    if args.command == "social-publish-due":
        from .db import ContentRepository
        from .engine.social import SocialBridge
        from .jobs import cleanup_temporary_media, publish_due
        from .providers.social_factory import providers_from_environment
        from .storage.r2 import r2_store_from_environment
        from .storage.temporary import TemporaryMediaRepository
        database = _database(args.database)
        providers = providers_from_environment()
        if not providers:
            raise RuntimeError("no real social providers are fully configured")
        content = ContentRepository(database)
        media = TemporaryMediaRepository(database)
        store = r2_store_from_environment()
        summaries = publish_due(
            content,
            SocialBridge(
                content,
                providers,
                media_resolver=store if store is not None else None,
            ),
            media_repository=media,
        )
        purged = cleanup_temporary_media(media, store) if store is not None else []
        print(json.dumps({
            "published_due": [
                {
                    "post_id": item.post_id,
                    "status": item.status,
                    "published": item.published,
                    "failed": item.failed,
                }
                for item in summaries
            ],
            "temporary_media_deleted": purged,
        }, indent=2))
        return 0

    if args.command == "connection-reminders":
        from datetime import datetime, timezone
        from .operations.email import send_reconnect_reminder
        from .operations.reminders import due_reminders
        from .studio_bridge import StudioBridge
        studio = StudioBridge(os.getenv("GOLIDE_STUDIO_BASE_URL", "https://studio.golidee.com"))
        due = due_reminders(studio.connection_expiry(), datetime.now(timezone.utc))
        sent = [item for item in due if send_reconnect_reminder(**item)]
        print(json.dumps({"status": "connection_reminders", "due": due, "sent": len(sent)}, indent=2))
        return 0

    if args.command == "rebuild-video":
        from .orchestration.rebuild import Rebuild
        from .storage.r2 import r2_store_from_environment
        from .studio_bridge import StudioBridge

        database = _database(args.database)
        rebuild = Rebuild(Path.cwd(), database, args.id)
        bridge = StudioBridge(os.getenv("GOLIDE_STUDIO_BASE_URL", "https://studio.golidee.com"))
        if args.step == "preview":
            from .operations.email import send_rebuild_preview
            from .orchestration.production import ProductionService

            store = r2_store_from_environment()
            if store is None:
                raise RuntimeError("R2 is required to hold the preview")
            # youtube=None: the topic was validated when the job first ran;
            # a rebuild must not re-run (or fail) demand checks.
            service = ProductionService(Path.cwd(), database, youtube=None)
            state = rebuild.build(
                service=service, store=store, bridge=bridge, notify=send_rebuild_preview,
                scene_plan=Path(args.scene_plan) if args.scene_plan else None,
                new_art=args.new_art,
            )
            state.pop("preview_url", None)  # never print a signed link into run logs
            print(json.dumps({"status": "rebuild_preview_ready", **state}, indent=2))
            return 0
        from .orchestration.studio_social import StudioSocialPublisher
        from .storage.retention import register_successful_upload
        from .youtube.auth import assert_channel, credentials, services
        from .youtube.uploader import YouTubeUploader

        youtube, _ = services(credentials(args.token))
        assert_channel(youtube, "UCqaXVBSBz7iQsRHOupKt-3w")
        state = rebuild.publish(
            uploader=YouTubeUploader(youtube, database, "UCqaXVBSBz7iQsRHOupKt-3w"),
            bridge=bridge,
            publisher_factory=lambda: StudioSocialPublisher(bridge=bridge),
            store=r2_store_from_environment(),
            register_upload=lambda video_id: register_successful_upload(Path.cwd(), database, args.id, video_id),
        )
        print(json.dumps({"status": "rebuild_published", **state}, indent=2))
        return 0 if state.get("status") == "published" else 1

    if args.command == "static-automation-run":
        from .orchestration.static_automation import StaticAutomation
        results = StaticAutomation().run_due()
        print(json.dumps({"status": "static_automation", "results": results}, indent=2))
        return 0

    if args.command == "studio-social-publish":
        from .orchestration.studio_social import StudioSocialPublisher
        results = StudioSocialPublisher().run_due()
        print(json.dumps({"status": "studio_social_publish", "results": results}, indent=2))
        return 0

    if args.command == "connections-sync-studio":
        from .connection_status import SUPPORTED_PROVIDERS, verify_provider
        from .studio_bridge import StudioBridge

        studio_url = os.getenv("GOLIDE_STUDIO_BASE_URL", "").strip()
        if not studio_url:
            raise RuntimeError("GOLIDE_STUDIO_BASE_URL is required")

        selected = tuple(dict.fromkeys(args.platform or SUPPORTED_PROVIDERS))
        connections = [verify_provider(platform) for platform in selected]
        StudioBridge(studio_url).sync_connections(connections)

        print(json.dumps({
            "status": "studio_connections_synced",
            "connections": connections,
        }, indent=2))
        if args.require_connected and any(not item["connected"] for item in connections):
            return 1
        return 0

    if args.command == "social-media-cleanup":
        from .jobs import cleanup_temporary_media
        from .storage.r2 import r2_store_from_environment
        from .storage.temporary import TemporaryMediaRepository
        database = _database(args.database)
        store = r2_store_from_environment()
        if store is None:
            raise RuntimeError("R2 temporary storage is not configured")
        purged = cleanup_temporary_media(
            TemporaryMediaRepository(database),
            store,
        )
        print(json.dumps({
            "status": "temporary_media_cleanup",
            "deleted": purged,
        }, indent=2))
        return 0

    if args.command == "studio-serve":
        from .web.server import serve
        serve(
            database_path=args.database,
            app_dir=args.app_dir,
            host=args.host,
            port=args.port,
        )
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
        voice = ProviderRegistry(args.config).config.get("voice", {})
        if voice.get("provider") != "owner_recording":
            raise RuntimeError("voice policy drifted from owner_recording")
        if voice.get("ai_voice_allowed") or voice.get("cloned_voice_allowed"):
            raise RuntimeError("AI or cloned narration must remain disabled")
        print(json.dumps({
            "status": "locked",
            "provider": "owner_recording",
            "required_spec_field": voice.get("required_spec_field", "owner_voice_media_ref"),
        }, indent=2))
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
        from .storage.retention import register_successful_upload
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
        retention = register_successful_upload(Path.cwd(), database, package["production_id"], video_id)
        print(json.dumps({"youtube_video_id": video_id, "scheduled_at": release.get("scheduled_at"), "retention": retention}, indent=2))
        return 0

    if args.command == "retention-cleanup":
        from .storage.retention import cleanup_expired_media
        database = _database(args.database)
        purged = cleanup_expired_media(Path.cwd(), database)
        print(json.dumps({"status": "retention_cleanup", "purged": purged}, indent=2))
        return 0

    if args.command == "automation-run":
        from .orchestration.production import ProductionService
        from .orchestration.queue import due_specs
        from .storage.retention import register_successful_upload
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
                claimed_spec = dict(claimed["spec"])
                if claimed_path.exists():
                    existing_spec = json.loads(claimed_path.read_text(encoding="utf-8"))
                    existing_spec.update({
                        key: value
                        for key, value in claimed_spec.items()
                        if value not in (None, "", [], {})
                    })
                    claimed_spec = existing_spec
                claimed_path.write_text(
                    json.dumps(claimed_spec, indent=2) + "\n", encoding="utf-8"
                )
        due = due_specs(args.queue)
        if not due:
            print(json.dumps({"status": "no_due_production"}))
            return 0
        from .orchestration.queue import pick_due_spec, record_failure
        spec_path = pick_due_spec(due, Path.cwd())
        if spec_path is None:
            print(json.dumps({"status": "all_due_productions_waiting_owner_voice",
                              "waiting": [p.stem for p in due]}))
            return 0
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
        from .orchestration.production import RenderHeld, WaitingOwnerVoice
        from .orchestration.recording import RecordingLengthError
        service = None

        def report_studio(
            status: str,
            stage: str,
            error: str | None = None,
            *,
            title: str | None = None,
            script: str | None = None,
            selected_topic: str | None = None,
            clear_voice: bool = False,
        ) -> None:
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
                    title=title,
                    script=script,
                    selected_topic=selected_topic,
                    clear_voice=clear_voice,
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
        except WaitingOwnerVoice as exc:
            refreshed = json.loads(spec_path.read_text(encoding="utf-8"))
            report_studio(
                "waiting_owner_voice",
                "script-ready",
                title=refreshed.get("title") or exc.title,
                script=exc.script,
                selected_topic=refreshed.get("brief") or refreshed.get("title"),
            )
            from .operations.email import send_record_needed
            send_record_needed(
                job_id=str(studio_job_id or spec["id"]),
                title=str(refreshed.get("title") or exc.title),
                format_name=str(spec.get("format", "short")),
                script=exc.script,
            )
            print(json.dumps({
                "status": "waiting_owner_voice",
                "production_id": spec["id"],
                "title": refreshed.get("title") or exc.title,
                "required_field": "owner_voice_media_ref",
                "message": "Topic research and script are ready. Upload the owner recording in Studio to resume from checkpoints.",
            }))
            return 0
        except RenderHeld as exc:
            report_studio("queued", "held-for-new-look", str(exc))
            print(json.dumps({"status": "render_held", "production_id": spec["id"], "reason": str(exc)}))
            return 0
        except RecordingLengthError as exc:
            refreshed = json.loads(spec_path.read_text(encoding="utf-8"))
            refreshed.pop("owner_voice_media_ref", None)
            spec_path.write_text(json.dumps(refreshed, indent=2) + "\n", encoding="utf-8")
            report_studio(
                "waiting_owner_voice",
                "recording-rejected",
                str(exc),
                clear_voice=True,
            )
            from .operations.email import send_record_needed
            script_file = Path("productions") / spec["id"] / "script.txt"
            plan_file = Path("productions") / spec["id"] / "scene-plan.json"
            if plan_file.exists():
                from .engine.content_rules import script_display
                display = script_display(json.loads(plan_file.read_text(encoding="utf-8")))
                script_file = Path("productions") / spec["id"] / "script-display.txt"
                script_file.write_text(display + "\n", encoding="utf-8")
            send_record_needed(
                job_id=str(studio_job_id or spec["id"]),
                title=str(refreshed.get("title") or spec["id"]),
                format_name=str(spec.get("format", "short")),
                script=script_file.read_text(encoding="utf-8") if script_file.exists() else "",
                rejection=str(exc),
            )
            print(json.dumps({
                "status": "waiting_owner_voice",
                "production_id": spec["id"],
                "reason": str(exc),
            }))
            return 0
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
            if spec_path.exists() and record_failure(spec_path):
                # Set aside after repeated failures so the queue keeps moving.
                print(f"::warning title=Production set aside::{spec['id']} failed {3} runs in a row: {str(exc)[:300]}")
            raise
        package_root = Path("release-packages") / spec["id"]
        package = json.loads((package_root / "package-manifest.json").read_text(encoding="utf-8"))
        files = package["files"]
        metadata = json.loads((package_root / files["metadata"]["file"]).read_text(encoding="utf-8"))
        uploader = YouTubeUploader(youtube, database, "UCqaXVBSBz7iQsRHOupKt-3w")
        release = package["release"]
        video_id = uploader.upload_private(spec["id"], package_root / files["video"]["file"], package_root / files["thumbnail"]["file"], metadata, release)
        retention = register_successful_upload(Path.cwd(), database, spec["id"], video_id)
        reels = None
        if spec.get("format") == "short" and bridge:
            # Shorts also go out as Instagram and Facebook Reels (with a cover
            # frame). Best effort: YouTube is already live, and a failed Reel
            # is retried by the distribution runs.
            try:
                from .orchestration.reels import publish_reels
                from .orchestration.studio_social import StudioSocialPublisher
                from .storage.r2 import r2_store_from_environment

                reels = publish_reels(
                    bridge=bridge, store=r2_store_from_environment(),
                    publisher_factory=lambda: StudioSocialPublisher(bridge=bridge),
                    production_id=spec["id"], video=package_root / files["video"]["file"],
                    metadata=metadata, youtube_video_id=video_id,
                    owner_voice_ref=str(spec.get("owner_voice_media_ref", "")),
                    cover=Path("build") / spec["id"] / "video-cover.jpg",
                )
            except Exception as exc:
                reels = {"reels_status": "failed", "error": str(exc)[:500]}
                print(f"::warning title=Reels not published::{str(exc)[:300]}")
        long_social = None
        if spec.get("format") == "long" and bridge and str(spec.get("generate_at", "")) >= LONG_SOCIAL_FROM:
            # Long videos also go to Facebook (native video) and LinkedIn at the
            # YouTube release time; the 19:30 distribution run publishes them.
            try:
                from .orchestration.reels import queue_long_social
                from .storage.r2 import r2_store_from_environment

                long_social = queue_long_social(
                    bridge=bridge, store=r2_store_from_environment(), production_id=spec["id"],
                    video=package_root / files["video"]["file"], metadata=metadata,
                    youtube_video_id=video_id, owner_voice_ref=str(spec.get("owner_voice_media_ref", "")),
                    publish_at=str(release.get("scheduled_at") or spec.get("release", {}).get("scheduled_at", "")),
                    cover=Path("build") / spec["id"] / "video-cover.jpg",
                )
            except Exception as exc:
                long_social = {"status": "failed", "error": str(exc)[:500]}
                print(f"::warning title=Long video not queued for Facebook/LinkedIn::{str(exc)[:300]}")
        done = spec_path.with_suffix(".completed.json")
        spec_path.rename(done)
        qa_warnings = []
        try:
            qa_warnings = json.loads((Path("productions") / spec["id"] / "qa-report.json").read_text(encoding="utf-8")).get("warnings", [])
        except Exception:
            pass
        report_studio("scheduled", "youtube-scheduled",
                      ("Published, but check the spelling of: " + ", ".join(w.split(": ", 1)[-1] for w in qa_warnings))
                      if qa_warnings else None)
        print(json.dumps({"status": "scheduled", "production_id": spec["id"], "youtube_video_id": video_id,
                          "retention": retention, "reels": reels, "long_social": long_social}))
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
