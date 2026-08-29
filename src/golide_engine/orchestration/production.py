from __future__ import annotations

import json
import os
import subprocess
import re
from pathlib import Path
from typing import Any

from ..captions import words_to_srt
from ..feedback.engine import FeedbackEngine
from ..manifest import load_project
from ..music.registry import MusicRegistry
from ..operations.costs import CostTracker, Usage
from ..operations.notifications import Notifier
from ..providers.base import ProviderOutput
from ..providers.registry import ProviderRegistry
from ..quality.runner import QualityRunner
from ..quality.visual import normalize_thumbnail
from ..release.package import ReleasePackager
from ..render import render
from ..scoring import score_concept
from ..storage.database import Database
from ..youtube_metadata import load_metadata_policy, validate_upload_metadata
from .schemas import METADATA_SCHEMA, RESEARCH_SCHEMA, STORYBOARD_SCHEMA
from .stage_runner import StageRunner


class ProductionService:
    """Runs one explicitly approved production through a checkpointed release build."""

    def __init__(self, root: str | Path, database: Database):
        self.root = Path(root).resolve()
        self.database = database
        self.providers = ProviderRegistry(self.root / "config/providers.json")
        self.costs = CostTracker(database, self.root / "config/provider-pricing.json")
        self.runner = StageRunner(database, Notifier(self.root / "failure-events"))

    def _assert_authorized(self, spec: dict[str, Any]) -> None:
        if os.getenv("GOLIDE_ENABLE_PAID_PRODUCTION") != "1":
            raise RuntimeError("paid production lock is closed")
        if spec.get("production_authorized") is not True or spec.get("release", {}).get("approved") is not True:
            raise RuntimeError("production and release must both be explicitly approved")
        if spec.get("release", {}).get("channel_id") != "UCqaXVBSBz7iQsRHOupKt-3w":
            raise RuntimeError("production does not target the locked G$LIDE channel")

    def _record_text(self, production_id: str, stage: str, output: ProviderOutput) -> None:
        self.costs.record(production_id, stage, "openai", "gpt-5.6-sol", Usage(
            input_tokens=output.input_tokens, cached_input_tokens=output.cached_input_tokens,
            output_tokens=output.output_tokens,
        ), output.request_id)

    def _record_image(self, production_id: str, stage: str, fallback_model: str, output: ProviderOutput) -> None:
        usage = output.details or {}
        details = usage.get("input_tokens_details", {}) or {}
        text_tokens = int(details.get("text_tokens", 0) or 0)
        image_tokens = int(details.get("image_tokens", 0) or 0)
        output_tokens = int(usage.get("output_tokens", 0) or 0)
        if text_tokens or image_tokens or output_tokens:
            if text_tokens:
                self.costs.record(production_id, stage, "openai", "gpt-image-2-text-input", Usage(input_tokens=text_tokens), output.request_id)
            if image_tokens:
                self.costs.record(production_id, stage, "openai", "gpt-image-2-image-input", Usage(input_tokens=image_tokens), output.request_id)
            if output_tokens:
                self.costs.record(production_id, stage, "openai", "gpt-image-2-image-output", Usage(output_tokens=output_tokens), output.request_id)
        else:
            self.costs.record(production_id, stage, "openai", fallback_model, Usage(images=1), output.request_id)

    def _budget(self, spec: dict[str, Any]) -> None:
        spent = self.costs.total(spec["id"])
        if spent > float(spec["max_cost_usd"]):
            raise RuntimeError(f"production cost ${spent:.4f} exceeded ${float(spec['max_cost_usd']):.2f} ceiling")

    @staticmethod
    def _require_absent(path: Path, stage: str) -> None:
        if path.exists():
            raise RuntimeError(f"{stage} has an uncheckpointed artifact at {path}; reconcile it instead of repeating a paid request")

    def _reserve(self, spec: dict[str, Any], model: str, usage: Usage) -> None:
        projected = self.costs.total(spec["id"]) + self.costs.estimate("openai", model, usage)
        if projected > float(spec["max_cost_usd"]):
            raise RuntimeError(f"next request could exceed the ${float(spec['max_cost_usd']):.2f} production ceiling")

    @staticmethod
    def _duration(audio: Path) -> float:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(audio)],
            capture_output=True, text=True, check=True,
        )
        return float(result.stdout.strip())

    @staticmethod
    def _safe_id(value: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
            raise RuntimeError(f"unsafe generated identifier: {value!r}")
        return value

    def run(self, spec_path: str | Path) -> Path:
        spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
        self._assert_authorized(spec)
        self.database.initialize()
        self.database.upsert_production(spec, "running")
        production_id = spec["id"]
        work = self.root / "productions" / production_id
        work.mkdir(parents=True, exist_ok=True)
        # Validate every paid unit before the first API request to prevent a partial, unusable production.
        self.costs.require_rate("gpt-5.6-sol", "input_per_million_tokens")
        self.costs.require_rate("gpt-5.6-sol", "output_per_million_tokens")
        image_cost_model = f"gpt-image-2-medium-{ 'portrait' if spec['format'] == 'short' else 'landscape' }"
        self.costs.require_rate(image_cost_model, "fallback_per_image")
        self.costs.require_rate("gpt-image-2-high-landscape", "fallback_per_image")
        self.costs.require_rate("gpt-image-2-text-input", "input_per_million_tokens")
        self.costs.require_rate("gpt-image-2-image-input", "input_per_million_tokens")
        self.costs.require_rate("gpt-image-2-image-output", "output_per_million_tokens")
        self.costs.require_rate("gpt-4o-mini-tts", "input_per_million_tokens")
        self.costs.require_rate("gpt-4o-mini-tts", "output_per_million_tokens")
        self.costs.require_rate("whisper-1", "fallback_per_minute")
        self.costs.require_rate("web-search", "per_tool_call")
        adjustment = FeedbackEngine(self.database).adjustment(spec["format"], spec.get("generation_parameters", {}))
        score = score_concept(spec["format"], spec["concept"]["scores"], adjustment)
        if score.verdict != "produce":
            raise RuntimeError(f"concept is not production-ready: {score.verdict} {score.blockers}")
        (work / "concept-score.json").write_text(json.dumps({"total": score.total, "verdict": score.verdict, "feedback_adjustment": adjustment}, indent=2) + "\n", encoding="utf-8")

        text = self.providers.text(live=True)
        research_path = work / "research.json"
        def research_stage():
            self._require_absent(research_path, "research")
            self._reserve(spec, "gpt-5.6-sol", Usage(input_tokens=max(1, len(spec["brief"]) // 4), output_tokens=12000))
            output = text.generate_json(
                "Research only verifiable claims for an original G$LIDE explainer. Every claim requires a direct source URL. Reject sensational claims unsupported by evidence.",
                spec["brief"], RESEARCH_SCHEMA, web_search=True,
            )
            research_path.write_text(json.dumps(output.value, indent=2) + "\n", encoding="utf-8")
            self._record_text(production_id, "research", output)
            self.costs.record(production_id, "research-search", "openai", "web-search", Usage(tool_calls=1))
        self.runner.run(production_id, "research", research_stage)
        research = json.loads(research_path.read_text(encoding="utf-8"))
        self._budget(spec)

        script_path = work / "script.txt"
        def script_stage():
            self._require_absent(script_path, "script")
            script_input = spec["brief"] + json.dumps(research)
            self._reserve(spec, "gpt-5.6-sol", Usage(input_tokens=max(1, len(script_input) // 4), output_tokens=12000))
            output = text.write_script(spec["brief"], json.dumps(research))
            script_path.write_text(output.value.strip() + "\n", encoding="utf-8")
            self._record_text(production_id, "script", output)
        self.runner.run(production_id, "script", script_stage)
        script = script_path.read_text(encoding="utf-8").strip()
        self._budget(spec)

        storyboard_path = work / "storyboard.json"
        def storyboard_stage():
            self._require_absent(storyboard_path, "storyboard")
            limit = 90 if spec["format"] == "short" else 300
            self._reserve(spec, "gpt-5.6-sol", Usage(input_tokens=max(1, len(script) // 4), output_tokens=12000))
            output = text.generate_json(
                "Create a timed G$LIDE paper-explainer storyboard. Center subjects with negative space and an 8% safe margin. Use neon blue, GOLIDE gold, warm ivory and deep navy. Visual captions explain diagrams; they are not spoken captions. Use lowercase safe IDs. Reuse an asset_key when the same character, object or diagram can be reframed across multiple cuts; do not request a new paid image for every cut.",
                f"FORMAT={spec['format']} MAX_SECONDS={limit}\nSCRIPT\n{script}", STORYBOARD_SCHEMA,
            )
            storyboard_path.write_text(json.dumps(output.value, indent=2) + "\n", encoding="utf-8")
            self._record_text(production_id, "storyboard", output)
        self.runner.run(production_id, "storyboard", storyboard_stage)
        storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
        for scene in storyboard["scenes"]:
            self._safe_id(scene["id"])
            self._safe_id(scene["asset_key"])
        self._budget(spec)

        asset_provider = self.providers.images(live=True)
        asset_dir = work / "assets"
        reference_images = [Path(path) for path in spec.get("avatar_reference_images", [])]
        size = self.providers.config["assets"][f"{spec['format']}_size"]
        unique_assets = {}
        for scene in storyboard["scenes"]:
            unique_assets.setdefault(scene["asset_key"], scene)
        for asset_key, scene in unique_assets.items():
            target = asset_dir / f"{asset_key}.png"
            def asset_stage(scene=scene, target=target):
                self._require_absent(target, f"asset:{scene['asset_key']}")
                self._reserve(spec, image_cost_model, Usage(images=1))
                output = asset_provider.create_image(scene["visual_prompt"], target, size, reference_images or None)
                self._record_image(production_id, f"asset:{scene['asset_key']}", image_cost_model, output)
            self.runner.run(production_id, f"asset:{asset_key}", asset_stage)
            self._budget(spec)

        narration = work / "narration.wav"
        voice = self.providers.voice(live=True)
        def voice_stage():
            self._require_absent(narration, "voice")
            estimated_seconds = max(1, len(script.split()) / 180 * 60)
            estimate = Usage(input_tokens=max(1, len(script) // 4), output_tokens=round(estimated_seconds * 20))
            self._reserve(spec, "gpt-4o-mini-tts", estimate)
            voice.synthesize(script, narration)
            actual = Usage(input_tokens=max(1, len(script) // 4), output_tokens=round(self._duration(narration) * 20))
            self.costs.record(production_id, "voice", "openai", "gpt-4o-mini-tts", actual)
        self.runner.run(production_id, "voice", voice_stage)
        self._budget(spec)
        narration_seconds = self._duration(narration)
        maximum = 90 if spec["format"] == "short" else 300
        if narration_seconds > maximum:
            raise RuntimeError(f"narration is {narration_seconds:.1f}s and exceeds the {maximum}s format limit")
        planned_seconds = sum(float(scene["duration"]) for scene in storyboard["scenes"])
        if planned_seconds <= 0:
            raise RuntimeError("storyboard has no positive duration")
        scale = narration_seconds / planned_seconds
        for scene in storyboard["scenes"]:
            scene["duration"] = round(float(scene["duration"]) * scale, 3)
        storyboard_path.write_text(json.dumps(storyboard, indent=2) + "\n", encoding="utf-8")

        spoken_srt = work / "spoken-captions.srt"
        timed_words_path = work / "timed-words.json"
        captions_provider = self.providers.captions(live=True)
        def caption_stage():
            self._require_absent(timed_words_path, "captions")
            self._require_absent(spoken_srt, "captions")
            minutes = self._duration(narration) / 60
            self._reserve(spec, "whisper-1", Usage(audio_minutes=minutes))
            output = captions_provider.transcribe_words(narration)
            timed_words_path.write_text(json.dumps(output.value, indent=2) + "\n", encoding="utf-8")
            spoken_srt.write_text(words_to_srt(output.value), encoding="utf-8")
            self.costs.record(production_id, "captions", "openai", "whisper-1", Usage(audio_minutes=minutes), output.request_id)
        self.runner.run(production_id, "captions", caption_stage)
        self._budget(spec)

        music = MusicRegistry(self.root / "config/music-registry.json").select(spec["music"]["mood"], spec["music"].get("track_id"))
        manifest_path = work / "render-manifest.json"
        manifest = {
            "id": production_id, "title": spec.get("title", spec["concept"].get("promise", production_id)),
            "format": spec["format"], "max_cost_usd": spec["max_cost_usd"], "narration": str(narration),
            "music": str(music.path), "audio": {"music_source": music.source_url, "music_license": music.license, "music_volume": 0.08, "duck_under_voice": True},
            "captions": {"spoken_srt": str(spoken_srt)},
            "scenes": [{"id": scene["id"], "media": str(asset_dir / f"{scene['asset_key']}.png"), "duration": scene["duration"], "caption": scene["visual_caption"]} for scene in storyboard["scenes"]],
            "publish": {"approved": True},
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        video_path = self.root / "build" / production_id / "video.mp4"
        self.runner.run(production_id, "render", lambda: render(load_project(manifest_path), self.root), attempts=1)

        metadata_path = work / "upload-metadata.json"
        policy = load_metadata_policy(self.root / "config/youtube-metadata-policy.json")
        def metadata_stage():
            self._require_absent(metadata_path, "metadata")
            self._reserve(spec, "gpt-5.6-sol", Usage(input_tokens=max(1, len(script) // 4), output_tokens=12000))
            output = text.generate_json(
                "Create accurate YouTube metadata for G$LIDE. No hashtags in title. Describe the actual video, place only a few relevant hashtags at the description end, and use chapters only for long videos.",
                f"FORMAT={spec['format']}\nSCRIPT\n{script}", METADATA_SCHEMA,
            )
            metadata = output.value | {"format": spec["format"]}
            if music.attribution and music.attribution not in metadata["description"]:
                metadata["description"] = metadata["description"].rstrip() + f"\n\nMusic: {music.attribution}"
            validate_upload_metadata(metadata, policy)
            metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            self._record_text(production_id, "metadata", output)
        self.runner.run(production_id, "metadata", metadata_stage)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self._budget(spec)

        raw_thumbnail = work / "thumbnail-source.png"
        thumbnail = work / "thumbnail.png"
        thumbnail_provider = self.providers.thumbnails(live=True)
        def thumbnail_stage():
            self._require_absent(raw_thumbnail, "thumbnail")
            self._require_absent(thumbnail, "thumbnail")
            self._reserve(spec, "gpt-image-2-high-landscape", Usage(images=1))
            prompt = (
                "Original high-CTR G$LIDE paper-cut explainer thumbnail in 16:9 composition. "
                "Use the consistent unrealistic paper-cut Esiah avatar with a topic-specific expression, "
                "one clear topic object or consequence, deep navy, neon blue, warm ivory and G$LIDE gold. "
                "No words, letters, captions, labels, logos or typography anywhere in the image. "
                f"Topic context: {metadata['title']}"
            )
            output = thumbnail_provider.create_thumbnail(prompt, raw_thumbnail, self.providers.config["thumbnail"]["size"], reference_images or None)
            normalize_thumbnail(raw_thumbnail, thumbnail)
            self._record_image(production_id, "thumbnail", "gpt-image-2-high-landscape", output)
        self.runner.run(production_id, "thumbnail", thumbnail_stage)
        self._budget(spec)

        visual_srt = self.root / "build" / production_id / "visual-labels.srt"
        source_ledger = work / "source-ledger.json"
        source_ledger.write_text(json.dumps({"claims": research["claims"], "music": MusicRegistry.source_ledger(music)}, indent=2) + "\n", encoding="utf-8")
        params_path = work / "generation-parameters.json"
        params_path.write_text(json.dumps(spec.get("generation_parameters", {}), indent=2) + "\n", encoding="utf-8")
        qa_path = work / "qa-report.json"
        def qa_stage():
            result = QualityRunner(self.root / "config/qa-policy.json").run(video_path, spec["format"], storyboard, [script, metadata["title"], metadata["description"]], qa_path, thumbnail)
            if not result.passed:
                raise RuntimeError("automatic QA failed: " + "; ".join(result.failures))
            return result
        qa_result = self.runner.run(production_id, "qa", qa_stage, attempts=1)
        qa = qa_result or QualityRunner(self.root / "config/qa-policy.json").run(video_path, spec["format"], storyboard, [script, metadata["title"], metadata["description"]], None, thumbnail)
        if not qa.passed:
            raise RuntimeError("automatic QA failed: " + "; ".join(qa.failures))

        release = spec["release"] | {"qa": {"passed": True}}
        files = {
            "video": video_path, "thumbnail": thumbnail, "metadata": metadata_path,
            "spoken_captions": spoken_srt, "visual_captions": visual_srt,
            "source_ledger": source_ledger, "generation_parameters": params_path, "qa_report": qa_path,
        }
        packager = ReleasePackager(self.root / "release-packages")
        def release_stage():
            return packager.build(production_id, files, release, {"total_usd": self.costs.total(production_id), "ceiling_usd": spec["max_cost_usd"]})
        release_result = self.runner.run(production_id, "release", release_stage, attempts=1)
        archive = release_result or (self.root / "release-packages" / f"{production_id}.zip")
        self.database.execute("UPDATE productions SET status='release_ready', updated_at=datetime('now') WHERE production_id=?", (production_id,))
        return archive
