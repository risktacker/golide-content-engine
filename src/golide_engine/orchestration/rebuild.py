"""Rebuild a finished video with the current renderer, then republish it.

Two steps, so nothing goes public until the owner has watched it:

1. ``build``: re-render an already-produced job from its saved checkpoints
   (same script, same owner recording and word timings, same metadata and
   thumbnail). No new script or research is paid for. The new video is put in
   temporary storage and the owner gets an email with a private preview link.
2. ``publish``: after the owner approves, upload it to YouTube as a new public
   video and post the same file as an Instagram Reel and a Facebook Reel.
   Deleting the superseded YouTube video stays a manual owner action.

Each step records its progress in production-queue/rebuild/<id>.json, so a
failed run can be dispatched again and continues where it stopped.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..engine.content_rules import script_text
from ..storage.database import Database

REDO_ALWAYS = ("render-vector-v1", "qa", "release")
REDO_ART = ("visual-plan-v1", "illustrations-v1")
REDO_VOICE = ("owner-voice", "captions-authoritative-v3")
PREVIEW_HOURS = 48


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


class RebuildError(RuntimeError):
    pass


class Rebuild:
    def __init__(self, root: Path, database: Database, production_id: str):
        self.root = root
        self.database = database
        self.id = production_id
        self.spec_path = root / "production-queue" / f"{production_id}.completed.json"
        self.work = root / "productions" / production_id
        self.state_path = root / "production-queue" / "rebuild" / f"{production_id}.json"
        self.record_path = root / "data" / "production-records" / f"{production_id}.json"

    # ------------------------------------------------------------------ state
    def state(self) -> dict[str, Any]:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        return {"production_id": self.id}

    def save(self, state: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    def spec(self) -> dict[str, Any]:
        if not self.spec_path.exists():
            raise RebuildError(f"{self.id} has no finished job to rebuild ({self.spec_path} missing)")
        return json.loads(self.spec_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------- preparing
    def prepare(self, scene_plan: Path | None = None, new_art: bool = False) -> list[str]:
        """Restore free checkpoints and mark only the render onward for redo."""
        spec = self.spec()
        self.work.mkdir(parents=True, exist_ok=True)
        record = json.loads(self.record_path.read_text(encoding="utf-8")) if self.record_path.exists() else {}
        restore = {
            "research.json": record.get("research"),
            "upload-metadata.json": record.get("metadata"),
        }
        for name, value in restore.items():
            path = self.work / name
            if not path.exists() and value:
                path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        script_path = self.work / "script.txt"
        if not script_path.exists() and record.get("narration"):
            script_path.write_text(str(record["narration"]).strip() + "\n", encoding="utf-8")
        if not script_path.exists():
            raise RebuildError("the saved script is missing; this job cannot be rebuilt without paying for a new one")
        script = script_path.read_text(encoding="utf-8")

        plan_path = self.work / "scene-plan.json"
        if scene_plan is not None:
            plan = json.loads(scene_plan.read_text(encoding="utf-8"))
            if _words(script_text(plan)) != _words(script):
                raise RebuildError("the new scene plan does not have exactly the recorded words")
            plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        if not plan_path.exists():
            raise RebuildError("no scene plan; only videos made by the vector renderer can be rebuilt")

        redo = list(REDO_ALWAYS)
        if new_art:
            redo += list(REDO_ART)
            (self.work / "visual-plan.json").unlink(missing_ok=True)
            shutil.rmtree(self.work / "illustrations", ignore_errors=True)
        narration = self.work / "narration-owner.wav"
        timed = self.work / "timed-words-owner.json"
        if not narration.exists() or not timed.exists():
            if not str(spec.get("owner_voice_media_ref", "")).startswith("r2://"):
                raise RebuildError("the owner recording is no longer available; upload it again")
            redo += list(REDO_VOICE)
            for name in ("narration-owner.wav", "timed-words-owner.json", "timed-words-authoritative-v3.json",
                         "spoken-captions-authoritative-v3.srt", "owner-voice-source"):
                (self.work / name).unlink(missing_ok=True)
        if not (self.work / "thumbnail.png").exists():
            redo.append("thumbnail")
            (self.work / "thumbnail-source.png").unlink(missing_ok=True)

        self.database.initialize()
        marks = ",".join("?" for _ in redo)
        self.database.execute(
            f"DELETE FROM stage_runs WHERE production_id=? AND stage IN ({marks})", (self.id, *redo)
        )
        (self.root / "build" / self.id / "video.mp4").unlink(missing_ok=True)
        (self.work / "qa-report.json").unlink(missing_ok=True)
        shutil.rmtree(self.root / "release-packages" / self.id, ignore_errors=True)
        (self.root / "release-packages" / f"{self.id}.zip").unlink(missing_ok=True)
        return redo

    def package(self) -> tuple[dict[str, Any], Path]:
        root = self.root / "release-packages" / self.id
        manifest = root / "package-manifest.json"
        if not manifest.exists():
            raise RebuildError("the rebuilt video package is missing; run the rebuild (preview) step again")
        return json.loads(manifest.read_text(encoding="utf-8")), root

    # --------------------------------------------------------------- step 1
    def build(self, *, service, store, bridge=None, notify=None, scene_plan: Path | None = None,
              new_art: bool = False) -> dict[str, Any]:
        redo = self.prepare(scene_plan, new_art)
        service.run(self.spec_path)
        package, root = self.package()
        video = root / package["files"]["video"]["file"]
        upload = store.upload_bytes(
            filename=f"{self.id}-rebuild.mp4",
            media_kind="video",
            data=video.read_bytes(),
            content_type="video/mp4",
            retention_hours=PREVIEW_HOURS + 24,
        )
        if bridge is not None:
            try:
                bridge.register_media([{
                    "media_ref": upload.media_ref,
                    "media_kind": "video",
                    "expires_at": upload.expires_at.isoformat(),
                }])
            except Exception as exc:  # tracking only; the preview still works
                print(json.dumps({"status": "media_register_failed", "error": str(exc)}))
        preview = store.resolve(upload.media_ref, expires_seconds=PREVIEW_HOURS * 3600)
        earlier = self.state()
        state = {
            "production_id": self.id,
            "previous": earlier if earlier.get("status") == "published" else earlier.get("previous"),
            "status": "awaiting_approval",
            "media_ref": upload.media_ref,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "preview_expires_at": (datetime.now(timezone.utc) + timedelta(hours=PREVIEW_HOURS)).isoformat(),
            "redone_stages": redo,
        }
        self.save(state)
        if notify is not None:
            notify(title=self.spec().get("title", self.id), preview_url=preview, production_id=self.id)
        return state | {"preview_url": preview}

    # --------------------------------------------------------------- step 2
    def publish(self, *, uploader, bridge, publisher_factory, store=None, register_upload=None) -> dict[str, Any]:
        state = self.state()
        if state.get("status") not in {"awaiting_approval", "youtube_published", "reels_queued"}:
            raise RebuildError(f"nothing approved to publish for {self.id} (status {state.get('status')})")
        package, root = self.package()
        files = package["files"]
        metadata = json.loads((root / files["metadata"]["file"]).read_text(encoding="utf-8"))
        spec = self.spec()

        if not state.get("youtube_video_id"):
            previous = os.environ.get("GOLIDE_FORCE_REUPLOAD_PRODUCTION_ID")
            os.environ["GOLIDE_FORCE_REUPLOAD_PRODUCTION_ID"] = self.id
            try:
                video_id = uploader.upload_private(
                    self.id, root / files["video"]["file"], root / files["thumbnail"]["file"],
                    metadata, package["release"],
                )
            finally:
                if previous is None:
                    os.environ.pop("GOLIDE_FORCE_REUPLOAD_PRODUCTION_ID", None)
                else:
                    os.environ["GOLIDE_FORCE_REUPLOAD_PRODUCTION_ID"] = previous
            state.update(status="youtube_published", youtube_video_id=video_id)
            self.save(state)
            if register_upload is not None:
                register_upload(video_id)

        if not state.get("social_post_id"):
            from .reels import publish_reels

            reels = publish_reels(
                bridge=bridge, store=store, publisher_factory=publisher_factory,
                production_id=self.id, video=root / files["video"]["file"], metadata=metadata,
                youtube_video_id=state["youtube_video_id"],
                owner_voice_ref=spec.get("owner_voice_media_ref", ""),
                video_ref=state["media_ref"],
                # A rebuild is a new post: never collide with an earlier Reel.
                content_id=f"{self.id}-reels-" + "".join(ch for ch in str(state.get("built_at", ""))[:19] if ch.isdigit()),
                cover=Path("build") / self.id / "video-cover.jpg",
            )
            state.update(status="reels_queued", social_post_id=reels["social_post_id"])
            self.save(state)
            outcome = reels["reels_status"]
        else:
            results = publisher_factory().run_due()
            mine = next((r for r in results if r.get("post_id") == state["social_post_id"]), None)
            outcome = mine["status"] if mine else "not_claimed"
        state.update(reels_status=outcome, published_at=datetime.now(timezone.utc).isoformat())
        if outcome == "published":
            state["status"] = "published"
        self.save(state)
        return state
