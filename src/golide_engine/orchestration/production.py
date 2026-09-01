from __future__ import annotations

import json
import os
import subprocess
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..captions import words_to_beats, words_to_srt
from ..feedback.engine import FeedbackEngine
from ..manifest import load_project
from ..music.registry import MusicRegistry
from ..operations.budget import MonthlyBudget
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
from ..youtube.demand import TopicDemandRejected, YouTubeDemandGate
from ..youtube_metadata import load_metadata_policy, validate_upload_metadata
from .schemas import METADATA_SCHEMA, RESEARCH_SCHEMA, STORYBOARD_SCHEMA, TREND_CANDIDATES_SCHEMA
from .stage_runner import StageRunner


class ProductionService:
    """Runs one explicitly approved production through a checkpointed release build."""

    def __init__(self, root: str | Path, database: Database, youtube: Any | None = None):
        self.root = Path(root).resolve()
        self.database = database
        self.youtube = youtube
        self.providers = ProviderRegistry(self.root / "config/providers.json")
        self.costs = CostTracker(database, self.root / "config/provider-pricing.json")
        self.budget = MonthlyBudget(
            database, self.costs, self.root / "config/budget-policy.json"
        )
        self.runner = StageRunner(database, Notifier(self.root / "failure-events"))

    def _assert_authorized(self, spec: dict[str, Any]) -> None:
        if os.getenv("GOLIDE_ENABLE_PAID_PRODUCTION") != "1":
            raise RuntimeError("paid production lock is closed")
        if spec.get("production_authorized") is not True or spec.get("release", {}).get("approved") is not True:
            raise RuntimeError("production and release must both be explicitly approved")
        if spec.get("release", {}).get("channel_id") != "UCqaXVBSBz7iQsRHOupKt-3w":
            raise RuntimeError("production does not target the locked G$LIDE channel")
        voice_cfg = self.providers.config.get("voice", {})
        if voice_cfg.get("provider") != "elevenlabs":
            raise RuntimeError("production narration must use ElevenLabs")
        if voice_cfg.get("approval_status") != "approved":
            raise RuntimeError("GOLIDE narrator is not approved; production remains locked")

    def _record_text(self, production_id: str, stage: str, output: ProviderOutput) -> None:
        model = self.providers.config["text"]["model"]
        self.costs.record(production_id, stage, "openai", model, Usage(
            input_tokens=output.input_tokens, cached_input_tokens=output.cached_input_tokens,
            output_tokens=output.output_tokens,
        ), output.request_id)

    def _record_image(self, production_id: str, stage: str, fallback_model: str, output: ProviderOutput) -> None:
        # Published per-image output prices are the predictable reservation unit.
        # Request IDs remain attached for provider reconciliation and audit.
        self.costs.record(
            production_id, stage, "openai", fallback_model,
            Usage(images=1), output.request_id,
        )

    def _budget(self, spec: dict[str, Any]) -> None:
        spent = self.costs.total(spec["id"])
        if spent > float(spec["max_cost_usd"]):
            raise RuntimeError(f"production cost ${spent:.4f} exceeded ${float(spec['max_cost_usd']):.2f} ceiling")

    @staticmethod
    def _require_absent(path: Path, stage: str) -> None:
        if path.exists():
            raise RuntimeError(f"{stage} has an uncheckpointed artifact at {path}; reconcile it instead of repeating a paid request")

    def _reserve(
        self,
        spec: dict[str, Any],
        model: str,
        usage: Usage,
        provider: str = "openai",
        stage: str = "paid-request",
    ) -> None:
        self.budget.reserve(spec, model, usage, provider=provider, stage=stage)

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

        # Validate every paid unit before the first API request.
        text_model = self.providers.config["text"]["model"]
        orientation = "portrait" if spec["format"] == "short" else "landscape"
        support_image_cost_model = f"gpt-image-1-mini-medium-{orientation}"
        hero_image_cost_model = f"gpt-image-2-medium-{orientation}"
        thumbnail_cost_model = "gpt-image-2-medium-landscape"
        self.costs.require_rate(text_model, "input_per_million_tokens")
        self.costs.require_rate(text_model, "output_per_million_tokens")
        self.costs.require_rate(support_image_cost_model, "fallback_per_image")
        self.costs.require_rate(hero_image_cost_model, "fallback_per_image")
        self.costs.require_rate(thumbnail_cost_model, "fallback_per_image")
        self.costs.require_rate("gpt-image-2-text-input", "input_per_million_tokens")
        self.costs.require_rate("gpt-image-2-image-input", "input_per_million_tokens")
        self.costs.require_rate("gpt-image-2-image-output", "output_per_million_tokens")
        voice_cfg = self.providers.config["voice"]
        self.costs.require_rate(voice_cfg["model"], "fallback_per_million_characters")
        self.costs.require_rate("web-search", "per_tool_call")
        text = self.providers.text(live=True)

        demand_path = work / "platform-demand.json"
        if self.youtube is not None:
            gate = YouTubeDemandGate(self.youtube, self.database)
            try:
                candidate, demand = gate.select(spec)
            except TopicDemandRejected:
                candidate_path = work / "trend-candidates.json"

                def trend_candidate_stage():
                    self._require_absent(candidate_path, "trend-candidates")
                    seeds = gate.trending_seeds()
                    if not seeds:
                        raise TopicDemandRejected(
                            "the YouTube trend feed returned no usable Science & Technology seeds"
                        )
                    seed_packet = json.dumps(
                        [{"title": item["title"], "market": item["market"]} for item in seeds[:60]],
                        separators=(",", ":"),
                    )
                    self._reserve(
                        spec,
                        text_model,
                        Usage(
                            input_tokens=max(1, (len(spec["brief"]) + len(seed_packet)) // 4),
                            output_tokens=3000,
                        ),
                        stage="trend-candidates",
                    )
                    output = text.generate_json(
                        "Create 3 to 5 original G$LIDE science, technology, unusual-true-event or impossible-but-real explainer candidates from current YouTube platform signals. Do not copy video titles or premises. Each candidate must have a concise search query and one direct authoritative primary or institutional source URL found through web search. Reject gossip, celebrity news, politics, unsupported claims and topics that cannot support a premium visual explanation.",
                        f"CURRENT BRIEF\n{spec['brief']}\n\nPLATFORM TREND SEEDS\n{seed_packet}",
                        TREND_CANDIDATES_SCHEMA,
                        web_search=True,
                        max_output_tokens=3000,
                    )
                    candidates = []
                    for item in output.value["candidates"]:
                        url = item["authoritative_source_url"].strip()
                        if not url.startswith(("https://", "http://")):
                            continue
                        seed_demand = gate.evaluate_trending_candidate(
                            item.get("query") or item["title"],
                            spec["format"],
                            seeds,
                        )
                        candidates.append({
                            **item,
                            "evidence_valid": True,
                            "platform_seed_demand": asdict(seed_demand),
                        })
                    if len(candidates) < 3:
                        raise TopicDemandRejected(
                            "trend planning did not return three evidence-backed candidates"
                        )
                    candidate_path.write_text(
                        json.dumps({"candidates": candidates}, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    self._record_text(production_id, "trend-candidates", output)
                    self.costs.record(
                        production_id, "trend-candidates-search", "openai",
                        "web-search", Usage(tool_calls=1),
                    )

                self.runner.run(
                    production_id, "trend-candidates", trend_candidate_stage, attempts=1
                )
                packet = json.loads(candidate_path.read_text(encoding="utf-8"))
                candidates = packet["candidates"]
                if any(
                    "platform_seed_demand" not in item for item in candidates
                ):
                    current_seeds = gate.trending_seeds()
                    if not current_seeds:
                        raise TopicDemandRejected(
                            "the YouTube trend feed returned no usable Science & Technology seeds"
                        )
                    for item in candidates:
                        item["platform_seed_demand"] = asdict(
                            gate.evaluate_trending_candidate(
                                item.get("query") or item["title"],
                                spec["format"],
                                current_seeds,
                            )
                        )
                    candidate_path.write_text(
                        json.dumps({"candidates": candidates}, indent=2) + "\n",
                        encoding="utf-8",
                    )
                spec["topic_candidates"] = candidates
                candidate, demand = gate.select(spec)

            spec["brief"] = candidate["brief"]
            spec["title"] = candidate.get("title", spec.get("title", production_id))
            spec["platform_demand"] = asdict(demand)
            spec["selected_topic_source"] = candidate.get("authoritative_source_url")
            Path(spec_path).write_text(
                json.dumps(spec, indent=2) + "\n", encoding="utf-8"
            )
            demand_path.write_text(
                json.dumps(spec["platform_demand"], indent=2) + "\n",
                encoding="utf-8",
            )
            self.database.upsert_production(spec, "running")
        elif spec.get("platform_demand", {}).get("verdict") != "pass":
            raise TopicDemandRejected(
                "platform-wide YouTube demand validation is required before production"
            )

        adjustment = FeedbackEngine(self.database).adjustment(spec["format"], spec.get("generation_parameters", {}))
        score = score_concept(spec["format"], spec["concept"]["scores"], adjustment)
        if score.verdict != "produce":
            raise RuntimeError(f"concept is not production-ready: {score.verdict} {score.blockers}")
        (work / "concept-score.json").write_text(json.dumps({"total": score.total, "verdict": score.verdict, "feedback_adjustment": adjustment}, indent=2) + "\n", encoding="utf-8")

        research_path = work / "research.json"
        def research_stage():
            self._require_absent(research_path, "research")
            self._reserve(spec, text_model, Usage(input_tokens=max(1, len(spec["brief"]) // 4), output_tokens=12000))
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
            target_words = "130-170" if spec["format"] == "short" else "650-780"
            script_brief = (
                f"FORMAT={spec['format']} TARGET_WORDS={target_words}. "
                "Stay inside the word range and end with a circular question. "
                + spec["brief"]
            )
            script_input = script_brief + json.dumps(research)
            self._reserve(
                spec, text_model,
                Usage(input_tokens=max(1, len(script_input) // 4), output_tokens=6000),
                stage="script",
            )
            output = text.write_script(script_brief, json.dumps(research))
            script_path.write_text(output.value.strip() + "\n", encoding="utf-8")
            self._record_text(production_id, "script", output)
        self.runner.run(production_id, "script", script_stage)
        script = script_path.read_text(encoding="utf-8").strip()
        self._budget(spec)

        voice_cfg = self.providers.config["voice"]
        narration = work / "narration.mp3"
        timed_words_path = work / "timed-words.json"
        voice = self.providers.voice(live=True)

        def voice_stage():
            self._require_absent(narration, "voice")
            self._require_absent(timed_words_path, "voice")
            characters = len(script)
            self.costs.require_monthly_character_capacity(
                "elevenlabs", characters, int(voice_cfg["monthly_character_limit"])
            )
            self._reserve(
                spec, voice_cfg["model"], Usage(characters=characters), provider="elevenlabs"
            )
            voice.validate_voice()
            output = voice.synthesize(script, narration)
            details = output.details or {}
            words = details.get("words")
            if not words:
                raise RuntimeError("ElevenLabs narration returned no timing alignment")
            timed_words_path.write_text(
                json.dumps(words, indent=2) + "\n", encoding="utf-8"
            )
            self.costs.record(
                production_id, "voice", "elevenlabs", voice_cfg["model"],
                Usage(characters=characters), output.request_id,
            )

        self.runner.run(production_id, "voice", voice_stage)
        self._budget(spec)
        narration_seconds = self._duration(narration)
        maximum = 90 if spec["format"] == "short" else 300
        if narration_seconds > maximum:
            raise RuntimeError(
                f"narration is {narration_seconds:.1f}s and exceeds the {maximum}s format limit"
            )

        timed_words = json.loads(timed_words_path.read_text(encoding="utf-8"))
        spoken_srt = work / "spoken-captions.srt"

        def caption_stage():
            self._require_absent(spoken_srt, "captions")
            spoken_srt.write_text(words_to_srt(timed_words), encoding="utf-8")

        self.runner.run(production_id, "captions", caption_stage, attempts=1)

        beats_path = work / "editorial-beats.json"

        def beat_stage():
            self._require_absent(beats_path, "editorial-beats")
            beats = words_to_beats(timed_words, max_seconds=3.2)
            beats_path.write_text(json.dumps(beats, indent=2) + "\n", encoding="utf-8")

        self.runner.run(production_id, "editorial-beats", beat_stage, attempts=1)
        beats = json.loads(beats_path.read_text(encoding="utf-8"))

        storyboard_path = work / "storyboard.json"

        def storyboard_stage():
            self._require_absent(storyboard_path, "storyboard")
            beat_packet = json.dumps(beats, separators=(",", ":"))
            self._reserve(
                spec, text_model,
                Usage(input_tokens=max(1, (len(script) + len(beat_packet)) // 4), output_tokens=18000),
            )
            output = text.generate_json(
                "Act as the G$LIDE Editorial Director. Return exactly one scene for every supplied beat_id and never invent timing. Map meaning to visible response: introduce nouns, punch spoken numbers, trace processes, switch composition for contrast, link cause to effect, and reserve strong reveals for key insights. Center subjects with negative space and an 8% safe margin. Use only named G$LIDE colors: neon-blue, golide-gold, warm-ivory, deep-navy, and danger-red only for danger/error. STRICT ASSET LIMIT: use no more than five unique primary asset_key values for a Short or twelve for long-form. Reuse those assets through reframing, progressive reveals, pushes, pans, crops, layers and match-cuts. Use secondary_assets only when an independent foreground, detail crop, label object or inset materially improves the explanation. Across the entire project, request no more than four unique secondary assets for a Short or twelve for long-form; reuse them across beats and request isolated paper-cut objects on transparent backgrounds. Vary camera and transition recipes; avoid Ken Burns repetition, transition spam, sound-effect spam, caption overload and avatar wallpaper. Motion, annotation and audio cues must be semantically synchronized. Use impact only for a true reveal and use none when narration should carry the emphasis.",
                f"FORMAT={spec['format']} NARRATION_SECONDS={narration_seconds:.3f}\nSCRIPT\n{script}\nTIMED_BEATS\n{beat_packet}",
                STORYBOARD_SCHEMA,
                max_output_tokens=18000,
            )
            planned_scenes = output.value["scenes"]
            planned = {scene["beat_id"]: scene for scene in planned_scenes}
            expected = {beat["id"] for beat in beats}
            if len(planned) != len(planned_scenes) or set(planned) != expected:
                raise RuntimeError("storyboard must contain every editorial beat exactly once")
            primary_limit = 5 if spec["format"] == "short" else 12
            primary_keys = {scene["asset_key"] for scene in planned_scenes}
            if len(primary_keys) > primary_limit:
                raise RuntimeError(
                    f"storyboard requested {len(primary_keys)} primary assets; limit is {primary_limit}"
                )
            merged = []
            for beat in beats:
                scene = planned[beat["id"]]
                self._safe_id(scene["asset_key"])
                merged.append({
                    "id": beat["id"],
                    "asset_key": scene["asset_key"],
                    "visual_role": scene["visual_role"],
                    "start": beat["start"],
                    "end": beat["end"],
                    "duration": beat["duration"],
                    "spoken_excerpt": beat["text"],
                    "visual_caption": scene["visual_caption"],
                    "visual_prompt": scene["visual_prompt"],
                    "motion": scene["motion"],
                    "secondary_assets": scene["secondary_assets"],
                    "subject_bounds": scene["subject_bounds"],
                })
            storyboard_path.write_text(
                json.dumps({"timing_source": "elevenlabs-normalized-alignment", "scenes": merged}, indent=2) + "\n",
                encoding="utf-8",
            )
            self._record_text(production_id, "storyboard", output)

        self.runner.run(production_id, "storyboard", storyboard_stage)
        storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
        self._budget(spec)

        support_provider = self.providers.images("support", live=True)
        hero_provider = self.providers.images("hero", live=True)
        asset_dir = work / "assets"
        reference_images = [Path(path) for path in spec.get("avatar_reference_images", [])]
        size = self.providers.config["assets"][f"{spec['format']}_size"]
        unique_assets = {}
        secondary_keys = set()
        hero_candidates = []
        for scene in storyboard["scenes"]:
            unique_assets.setdefault(scene["asset_key"], scene)
            if scene.get("visual_role") in {"REVEAL", "CONTRAST", "CAUSE_EFFECT"}:
                hero_candidates.append(scene["asset_key"])
            for layer in scene.get("secondary_assets", []):
                secondary_keys.add(layer["asset_key"])
                unique_assets.setdefault(layer["asset_key"], layer)
        secondary_limit = 4 if spec["format"] == "short" else 12
        if len(secondary_keys) > secondary_limit:
            raise RuntimeError(
                f"editorial plan requests {len(secondary_keys)} secondary assets; limit is {secondary_limit}"
            )
        hero_limit = int(self.providers.config["assets"]["hero_limits"][spec["format"]])
        hero_keys = set(dict.fromkeys(hero_candidates[:hero_limit]))
        for asset_key, scene in unique_assets.items():
            target = asset_dir / f"{asset_key}.png"
            is_hero = asset_key in hero_keys and asset_key not in secondary_keys
            asset_provider = hero_provider if is_hero else support_provider
            asset_cost_model = hero_image_cost_model if is_hero else support_image_cost_model

            def asset_stage(
                scene=scene,
                target=target,
                asset_provider=asset_provider,
                asset_cost_model=asset_cost_model,
            ):
                self._require_absent(target, f"asset:{scene['asset_key']}")
                self._reserve(
                    spec, asset_cost_model, Usage(images=1),
                    stage=f"asset:{scene['asset_key']}",
                )
                output = asset_provider.create_image(
                    scene["visual_prompt"], target, size, reference_images or None
                )
                self._record_image(
                    production_id, f"asset:{scene['asset_key']}", asset_cost_model, output
                )

            self.runner.run(production_id, f"asset:{asset_key}", asset_stage)
            self._budget(spec)

        music = MusicRegistry(self.root / "config/music-registry.json").select(spec["music"]["mood"], spec["music"].get("track_id"))
        manifest_path = work / "render-manifest.json"
        manifest = {
            "id": production_id, "title": spec.get("title", spec["concept"].get("promise", production_id)),
            "format": spec["format"], "max_cost_usd": spec["max_cost_usd"], "narration": str(narration),
            "music": str(music.path), "audio": {"music_source": music.source_url, "music_license": music.license, "music_volume": 0.08, "duck_under_voice": True},
            "captions": {"spoken_srt": str(spoken_srt)},
            "scenes": [{
                "id": scene["id"],
                "media": str(asset_dir / f"{scene['asset_key']}.png"),
                "start": scene["start"],
                "end": scene["end"],
                "duration": scene["duration"],
                "caption": scene["visual_caption"],
                "visual_role": scene["visual_role"],
                "motion": scene["motion"],
                "annotation": scene["motion"]["annotation"],
                "layers": [{
                    "media": str(asset_dir / f"{layer['asset_key']}.png"),
                    "role": layer["role"],
                    "position": layer["position"],
                    "scale": layer["scale"],
                    "entrance": layer["entrance"],
                    "start_offset": layer["start_offset"],
                    "duration": layer["duration"],
                } for layer in scene.get("secondary_assets", [])],
            } for scene in storyboard["scenes"]],
            "publish": {"approved": True},
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        video_path = self.root / "build" / production_id / "video.mp4"
        self.runner.run(production_id, "render", lambda: render(load_project(manifest_path), self.root), attempts=1)

        metadata_path = work / "upload-metadata.json"
        policy = load_metadata_policy(self.root / "config/youtube-metadata-policy.json")
        def metadata_stage():
            self._require_absent(metadata_path, "metadata")
            self._reserve(spec, text_model, Usage(input_tokens=max(1, len(script) // 4), output_tokens=12000))
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
            self._reserve(
                spec, thumbnail_cost_model, Usage(images=1), stage="thumbnail"
            )
            prompt = (
                "Original high-CTR G$LIDE paper-cut explainer thumbnail in 16:9 composition. "
                "Use the consistent unrealistic paper-cut Esiah avatar with a topic-specific expression, "
                "one clear topic object or consequence, deep navy, neon blue, warm ivory and G$LIDE gold. "
                "No words, letters, captions, labels, logos or typography anywhere in the image. "
                f"Topic context: {metadata['title']}"
            )
            output = thumbnail_provider.create_thumbnail(prompt, raw_thumbnail, self.providers.config["thumbnail"]["size"], reference_images or None)
            normalize_thumbnail(raw_thumbnail, thumbnail)
            self._record_image(production_id, "thumbnail", thumbnail_cost_model, output)
        self.runner.run(production_id, "thumbnail", thumbnail_stage)
        self._budget(spec)

        visual_srt = self.root / "build" / production_id / "visual-labels.srt"
        source_ledger = work / "source-ledger.json"
        source_ledger.write_text(
            json.dumps({
                "claims": research["claims"],
                "platform_demand": spec["platform_demand"],
                "music": MusicRegistry.source_ledger(music),
            }, indent=2) + "\n",
            encoding="utf-8",
        )
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
