from __future__ import annotations

import difflib
import json
import os
import re
import shutil
import subprocess
import urllib.request
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
from ..quality.editorial import check_editorial
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


def apply_locked_upload_defaults(metadata: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """Apply deterministic channel defaults after creative metadata generation."""
    normalized = dict(metadata)
    defaults = policy["upload_defaults"]
    normalized["video_language"] = defaults["video_language"]
    normalized["title_description_language"] = defaults["title_description_language"]
    return normalized


class ProductionService:
    """Runs one explicitly approved production through a checkpointed release build."""

    def __init__(
        self, root: str | Path, database: Database, youtube: Any | None = None,
        stage_listener=None,
    ):
        self.root = Path(root).resolve()
        self.database = database
        self.youtube = youtube
        self.providers = ProviderRegistry(self.root / "config/providers.json")
        self.costs = CostTracker(database, self.root / "config/provider-pricing.json")
        self.budget = MonthlyBudget(
            database, self.costs, self.root / "config/budget-policy.json"
        )
        self.runner = StageRunner(
            database, Notifier(self.root / "failure-events"), on_update=stage_listener
        )

    def _assert_authorized(self, spec: dict[str, Any]) -> None:
        if os.getenv("GOLIDE_ENABLE_PAID_PRODUCTION") != "1":
            raise RuntimeError("paid production lock is closed")
        if spec.get("production_authorized") is not True or spec.get("release", {}).get("approved") is not True:
            raise RuntimeError("production and release must both be explicitly approved")
        if spec.get("release", {}).get("channel_id") != "UCqaXVBSBz7iQsRHOupKt-3w":
            raise RuntimeError("production does not target the locked G$LIDE channel")
        voice_cfg = self.providers.config.get("voice", {})
        if voice_cfg.get("provider") != "owner_recording":
            raise RuntimeError("production narration must use the owner's recorded voice")
        if not str(spec.get("owner_voice_media_ref", "")).strip():
            raise RuntimeError("owner_voice_media_ref is required before video production can run")

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

    @staticmethod
    def _fit_annotation(raw: dict[str, Any] | None, beat_duration: float) -> dict[str, Any]:
        """Fit model-authored annotation timing inside its authoritative narration beat."""
        annotation = dict(raw or {})
        if annotation.get("kind", "none") == "none":
            return annotation
        beat = max(0.0, float(beat_duration))
        if beat <= 0.02:
            return {"kind": "none"}
        start = max(0.0, min(float(annotation.get("start_offset", 0)), beat - 0.01))
        remaining = beat - start
        duration = max(0.001, min(float(annotation.get("duration", remaining)), remaining))
        annotation["start_offset"] = round(start, 6)
        annotation["duration"] = round(duration, 6)
        return annotation

    @classmethod
    def _normalize_editorial_intent(
        cls, storyboard: dict[str, Any], policy: dict[str, Any]
    ) -> dict[str, Any]:
        """Enforce premium rhythm without repeating a paid planning request."""
        normalized = json.loads(json.dumps(storyboard))
        scenes = normalized.get("scenes", [])
        if not scenes:
            return normalized
        rules = policy["editorial"]

        def spread(indices: list[int], limit: int) -> set[int]:
            if len(indices) <= limit:
                return set(indices)
            if limit <= 0:
                return set()
            if limit == 1:
                return {indices[len(indices) // 2]}
            return {
                indices[round(position * (len(indices) - 1) / (limit - 1))]
                for position in range(limit)
            }

        non_cuts = [
            index for index, scene in enumerate(scenes)
            if (scene.get("motion") or {}).get("transition") != "cut"
        ]
        keep_transitions = spread(
            non_cuts,
            int(len(scenes) * float(rules["maximum_non_cut_transition_ratio"])),
        )
        cue_indices = [
            index for index, scene in enumerate(scenes)
            if (scene.get("motion") or {}).get("audio_cue", "none") != "none"
        ]
        keep_cues = spread(
            cue_indices,
            int(len(scenes) * float(rules["maximum_sfx_beat_ratio"])),
        )
        strong_indices = [
            index for index, scene in enumerate(scenes)
            if (scene.get("motion") or {}).get("intensity") == "strong"
        ]
        keep_strong = spread(
            strong_indices,
            int(len(scenes) * float(rules["maximum_strong_motion_ratio"])),
        )

        last_impact = -100.0
        for index, scene in enumerate(scenes):
            motion = scene.setdefault("motion", {})
            if index in non_cuts and index not in keep_transitions:
                motion["transition"] = "cut"
            if index in cue_indices and index not in keep_cues:
                motion["audio_cue"] = "none"
            if index in strong_indices and index not in keep_strong:
                motion["intensity"] = "medium"
            if motion.get("audio_cue") == "impact":
                start = float(scene.get("start", 0))
                if start - last_impact < float(rules["minimum_impact_spacing_seconds"]):
                    motion["audio_cue"] = "tick"
                else:
                    last_impact = start
            motion["annotation"] = cls._fit_annotation(
                motion.get("annotation"), float(scene.get("duration", 0))
            )
        return normalized

    @staticmethod
    def _build_recovery_storyboard(
        beats: list[dict[str, Any]], primary_limit: int
    ) -> list[dict[str, Any]]:
        """Build a deterministic no-text-API storyboard after a failed paid planner call."""
        if not beats:
            return []
        asset_count = min(primary_limit, len(beats))
        roles = ["CONTEXT", "PROCESS", "CAUSE_EFFECT", "CONTRAST", "REVEAL", "DATA"]
        motion_types = [
            "push-in", "pan-left", "reframe", "pull-out", "pan-right", "layer-reveal",
        ]
        templates: list[dict[str, str]] = []
        for slot in range(asset_count):
            representative_index = (
                0 if asset_count == 1
                else round(slot * (len(beats) - 1) / (asset_count - 1))
            )
            representative = str(beats[representative_index]["text"])
            prompt_excerpt = " ".join(representative.split()[:18]).rstrip(".,;:!?")
            templates.append({
                "asset_key": f"recovery-visual-{slot:02d}",
                "visual_role": roles[slot % len(roles)],
                "visual_prompt": (
                    "Blue and gold paper-cut scientific explainer scene showing "
                    f"{prompt_excerpt}. Clean mechanism or diagram composition, no readable text."
                ),
            })

        scenes: list[dict[str, Any]] = []
        for index, beat in enumerate(beats):
            base_slot = min(asset_count - 1, (index * asset_count) // len(beats))
            slot = (base_slot + (index % 2)) % asset_count
            template = templates[slot]
            caption = " ".join(str(beat["text"]).split()[:6]).rstrip(".,;:!?")
            duration = max(0.05, float(beat["duration"]))
            secondary_assets = []
            if index % 4 == 0 and asset_count > 1:
                detail = templates[(slot + 1) % asset_count]
                start_offset = min(0.10, max(0.0, duration - 0.01))
                secondary_assets.append({
                    "asset_key": detail["asset_key"],
                    "visual_prompt": detail["visual_prompt"],
                    "role": "detail",
                    "position": "right" if index % 8 == 0 else "left",
                    "scale": 0.42,
                    "entrance": "fade",
                    "start_offset": round(start_offset, 6),
                    "duration": round(max(0.01, duration - start_offset), 6),
                })
            scenes.append({
                "beat_id": beat["id"],
                "asset_key": template["asset_key"],
                "visual_role": template["visual_role"],
                "visual_caption": caption,
                "visual_prompt": template["visual_prompt"],
                "motion": {
                    "type": motion_types[index % len(motion_types)],
                    "intensity": "strong" if index % 8 == 0 else "medium",
                    "transition": "match-cut" if index % 5 == 0 else "cut",
                    "easing": "ease-in-out",
                    "emphasis": caption,
                    "audio_cue": "tick" if index % 7 == 0 else "none",
                    "annotation": {"kind": "none"},
                },
                "secondary_assets": secondary_assets,
                "subject_bounds": [],
            })
        return scenes

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
        self.costs.require_rate("web-search", "per_tool_call")
        text = self.providers.text(live=True)

        demand_path = work / "platform-demand.json"
        if self.youtube is not None:
            gate = YouTubeDemandGate(self.youtube, self.database)
            # Scheduled automation specs are deliberately generic. They must always
            # discover and compare fresh niche topics rather than allowing the generic
            # seed query (or an old trial topic) to become the production topic.
            requires_fresh_topic = (
                spec.get("purpose") == "channel-automation"
                and not spec.get("topic_candidates")
            )
            try:
                if requires_fresh_topic:
                    raise TopicDemandRejected("scheduled automation requires fresh topic discovery")
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
                    recent_titles = [
                        row["title"] for row in self.database.rows(
                            "SELECT title FROM productions WHERE production_id<>? ORDER BY updated_at DESC LIMIT 25",
                            (production_id,),
                        )
                        if row.get("title")
                    ]
                    seed_packet = json.dumps(
                        [{
                            "title": item["title"],
                            "markets": item.get("markets", []),
                            "views_per_day": item.get("views_per_day", 0),
                        } for item in seeds[:60]],
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
                        "Create 3 to 5 original G$LIDE science, technology, unusual-true-event or impossible-but-real explainer candidates from current YouTube platform signals. Compare the candidates for current demand, visual explanation potential, evidence strength, broad curiosity and novelty. Do not copy video titles or premises. Do not reuse or lightly reword any recently produced/trial topic supplied in RECENT G$LIDE TOPICS. Each candidate must have a concise search query and one direct authoritative primary or institutional source URL found through web search. Reject gossip, celebrity news, politics, unsupported claims and topics that cannot support a premium visual explanation.",
                        f"CURRENT BRIEF\n{spec['brief']}\n\nRECENT G$LIDE TOPICS\n{json.dumps(recent_titles)}\n\nPLATFORM TREND SEEDS\n{seed_packet}",
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

        narration = work / "narration-owner.wav"
        timed_words_path = work / "timed-words-owner.json"
        owner_voice_ref = str(spec.get("owner_voice_media_ref", "")).strip()

        def _normalized_words(value: str) -> str:
            return " ".join(re.findall(r"[a-z0-9']+", value.lower()))

        def voice_stage():
            self._require_absent(narration, "owner-voice")
            self._require_absent(timed_words_path, "owner-voice")
            source = work / "owner-voice-source"

            if owner_voice_ref.startswith("r2://"):
                from ..storage.r2 import r2_store_from_environment
                store = r2_store_from_environment()
                if store is None:
                    raise RuntimeError("R2 is required to resolve the owner voice recording")
                source_url = store.resolve(owner_voice_ref, expires_seconds=3600)
                with urllib.request.urlopen(source_url, timeout=90) as response:
                    source.write_bytes(response.read())
            elif owner_voice_ref.startswith("https://"):
                with urllib.request.urlopen(owner_voice_ref, timeout=90) as response:
                    source.write_bytes(response.read())
            else:
                local = Path(owner_voice_ref).expanduser()
                if not local.is_file():
                    raise RuntimeError("owner voice recording could not be found")
                shutil.copyfile(local, source)

            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(source),
                    "-vn", "-ac", "1", "-ar", "44100", str(narration),
                ],
                capture_output=True, text=True, check=True,
            )

            captioner = self.providers.captions(live=True)
            output = captioner.transcribe_words(narration)
            words = output.value
            if not words:
                raise RuntimeError("owner voice transcription returned no word timing")

            transcript = " ".join(str(item.get("word", "")) for item in words)
            similarity = difflib.SequenceMatcher(
                None,
                _normalized_words(script),
                _normalized_words(transcript),
            ).ratio()
            if similarity < 0.55:
                raise RuntimeError(
                    f"owner voice does not match the approved script closely enough ({similarity:.2f})"
                )

            timed_words_path.write_text(
                json.dumps(words, indent=2) + "\n", encoding="utf-8"
            )

        self.runner.run(production_id, "owner-voice", voice_stage)
        self._budget(spec)
        narration_seconds = self._duration(narration)
        maximum = 90 if spec["format"] == "short" else 300
        if narration_seconds > maximum:
            if narration_seconds > maximum * 1.08:
                raise RuntimeError(
                    f"narration is {narration_seconds:.1f}s and exceeds the "
                    f"{maximum}s format limit by more than the safe 8% correction"
                )
            target_seconds = maximum - 2
            tempo = narration_seconds / target_seconds
            corrected = narration.with_name(
                f"{narration.stem}.duration-corrected{narration.suffix}"
            )
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(narration),
                    "-filter:a", f"atempo={tempo:.8f}",
                    "-vn", str(corrected),
                ],
                capture_output=True, text=True, check=True,
            )
            corrected.replace(narration)
            adjusted_words = json.loads(
                timed_words_path.read_text(encoding="utf-8")
            )
            for word in adjusted_words:
                word["start"] = round(float(word["start"]) / tempo, 4)
                word["end"] = round(float(word["end"]) / tempo, 4)
            timed_words_path.write_text(
                json.dumps(adjusted_words, indent=2) + "\n",
                encoding="utf-8",
            )
            narration_seconds = self._duration(narration)
            if narration_seconds > maximum:
                raise RuntimeError(
                    f"duration correction left narration at "
                    f"{narration_seconds:.1f}s"
                )

        raw_timed_words = json.loads(timed_words_path.read_text(encoding="utf-8"))
        authoritative_words_path = work / "timed-words-authoritative-v3.json"
        if authoritative_words_path.exists():
            timed_words = json.loads(authoritative_words_path.read_text(encoding="utf-8"))
        else:
            timed_words = json.loads(json.dumps(raw_timed_words))
            alignment_seconds = float(timed_words[-1]["end"])
            timing_tolerance = max(0.75, narration_seconds * 0.01)
            if alignment_seconds <= 0:
                raise RuntimeError("owner-voice timing alignment has no positive duration")
            if abs(alignment_seconds - narration_seconds) > timing_tolerance:
                timing_scale = narration_seconds / alignment_seconds
                for word in timed_words:
                    word["start"] = round(float(word["start"]) * timing_scale, 4)
                    word["end"] = round(float(word["end"]) * timing_scale, 4)
            authoritative_words_path.write_text(
                json.dumps(timed_words, indent=2) + "\n", encoding="utf-8"
            )

        spoken_srt = work / "spoken-captions-authoritative-v3.srt"

        def caption_stage():
            self._require_absent(spoken_srt, "captions-authoritative-v3")
            spoken_srt.write_text(words_to_srt(timed_words), encoding="utf-8")

        self.runner.run(
            production_id, "captions-authoritative-v3", caption_stage, attempts=1
        )

        beats_path = work / "editorial-beats-authoritative-v3.json"

        def beat_stage():
            self._require_absent(beats_path, "editorial-beats-authoritative-v3")
            beats = words_to_beats(timed_words, max_seconds=3.2)
            beats_path.write_text(json.dumps(beats, indent=2) + "\n", encoding="utf-8")

        self.runner.run(
            production_id, "editorial-beats-authoritative-v3", beat_stage, attempts=1
        )
        beats = json.loads(beats_path.read_text(encoding="utf-8"))

        previous_storyboard_path = work / "storyboard-authoritative-v2.json"
        asset_inventory: dict[str, dict[str, Any]] = {}
        previous_scenes: list[dict[str, Any]] = []
        if previous_storyboard_path.exists():
            previous_storyboard = json.loads(
                previous_storyboard_path.read_text(encoding="utf-8")
            )
            previous_scenes = previous_storyboard.get("scenes", [])
            for previous_scene in previous_scenes:
                asset_inventory.setdefault(
                    previous_scene["asset_key"],
                    {
                        "asset_key": previous_scene["asset_key"],
                        "visual_prompt": previous_scene.get("visual_prompt", ""),
                    },
                )
                for previous_layer in previous_scene.get("secondary_assets", []):
                    asset_inventory.setdefault(
                        previous_layer["asset_key"],
                        {
                            "asset_key": previous_layer["asset_key"],
                            "visual_prompt": previous_layer.get("visual_prompt", ""),
                        },
                    )

        storyboard_path = work / "storyboard-authoritative-v5.json"

        def storyboard_stage():
            self._require_absent(storyboard_path, "storyboard")
            primary_limit = 5 if spec["format"] == "short" else 12
            minimum_unique = 5 if spec["format"] == "short" else 12
            minimum_layered_ratio = 0.15 if spec["format"] == "short" else 0.25

            prior_storyboard_failure = bool(self.database.rows(
                """SELECT 1 FROM stage_runs
                   WHERE production_id=? AND stage='storyboard-authoritative-v5'
                   AND status='failed' LIMIT 1""",
                (production_id,),
            ))

            if previous_scenes:
                # Recovery uses already-paid media and never invents replacement assets.
                def editorial_tokens(value: str) -> set[str]:
                    return {
                        token for token in re.findall(r"[a-z0-9]+", value.lower())
                        if len(token) > 2
                    }

                template_tokens = []
                for template in previous_scenes:
                    searchable = " ".join([
                        str(template.get("spoken_excerpt", "")),
                        str(template.get("visual_caption", "")),
                        str(template.get("visual_prompt", "")),
                    ])
                    template_tokens.append(editorial_tokens(searchable))

                motion_types = [
                    "push-in", "pan-left", "reframe", "pull-out",
                    "pan-right", "layer-reveal",
                ]
                transitions = ["cut", "match-cut", "paper-wipe", "object-transition"]
                roles = ["CONTEXT", "CAUSE_EFFECT", "CONTRAST", "REVEAL"]
                planned_scenes = []
                for index, beat in enumerate(beats):
                    beat_tokens = editorial_tokens(beat["text"])
                    scores = [
                        len(beat_tokens & tokens) * 100
                        - ((template_index - index) % len(previous_scenes))
                        for template_index, tokens in enumerate(template_tokens)
                    ]
                    template = previous_scenes[max(range(len(scores)), key=scores.__getitem__)]
                    spoken_words = str(beat["text"]).split()
                    caption = " ".join(spoken_words[:6]).rstrip(".,;:!?")
                    number_match = re.search(r"\b\d+(?:\.\d+)?\b", beat["text"])
                    annotation = {"kind": "none"}
                    if number_match:
                        annotation = {
                            "kind": "number",
                            "text": number_match.group(0),
                            "start_offset": 0.08,
                            "duration": min(1.1, max(0.1, float(beat["duration"]) - 0.1)),
                            "position": "center",
                            "color_token": "golide-gold",
                        }
                    planned_scenes.append({
                        "beat_id": beat["id"],
                        "asset_key": template["asset_key"],
                        "visual_role": template.get("visual_role", roles[index % len(roles)]),
                        "visual_caption": caption,
                        "visual_prompt": template.get("visual_prompt", ""),
                        "motion": {
                            "type": motion_types[index % len(motion_types)],
                            "intensity": "strong" if index % 5 == 0 else "medium",
                            "transition": transitions[index % len(transitions)],
                            "easing": "ease-in-out",
                            "emphasis": caption,
                            "audio_cue": "impact" if index % 9 == 0 else (
                                "soft-trace" if index % 3 == 0 else "none"
                            ),
                            "annotation": annotation,
                        },
                        "secondary_assets": template.get("secondary_assets", []),
                        "subject_bounds": template.get("subject_bounds", []),
                    })
            elif prior_storyboard_failure:
                # A prior paid planner response already failed to parse. Recover locally
                # from checkpointed narration beats rather than buying the same text stage again.
                planned_scenes = self._build_recovery_storyboard(beats, primary_limit)
            else:
                # New production: plan the full edit before the first image purchase.
                # The authoritative caption beats are intentionally merged in pairs for
                # the paid planning call. A long-form episode can contain ~100 three-second
                # beats; asking the model to repeat the full nested scene schema for every
                # beat made the structured JSON hit the output ceiling and truncate.
                # Pair planning cuts that payload roughly in half while preserving the
                # final one-scene-per-authoritative-beat contract after local expansion.
                planning_groups = []
                for offset in range(0, len(beats), 2):
                    members = beats[offset:offset + 2]
                    planning_groups.append({
                        "id": f"plan-{offset // 2:03d}",
                        "source_beat_ids": [member["id"] for member in members],
                        "start": members[0]["start"],
                        "end": members[-1]["end"],
                        "duration": round(
                            float(members[-1]["end"]) - float(members[0]["start"]), 6
                        ),
                        "text": " ".join(str(member["text"]) for member in members),
                    })
                compact_beats = [{
                    "id": group["id"],
                    "start": group["start"],
                    "end": group["end"],
                    "duration": group["duration"],
                    "text": group["text"],
                } for group in planning_groups]
                planning_input = json.dumps({
                    "format": spec["format"],
                    "brief": spec["brief"],
                    "narration": script,
                    "research": research,
                    "editorial_beats": compact_beats,
                    "primary_asset_limit": primary_limit,
                    "minimum_unique_primary_assets": minimum_unique,
                    "minimum_layered_scene_ratio": minimum_layered_ratio,
                }, separators=(",", ":"))
                storyboard_output_tokens = 9000
                self._reserve(
                    spec, text_model,
                    Usage(
                        input_tokens=max(1, len(planning_input) // 4),
                        output_tokens=storyboard_output_tokens,
                    ),
                    stage="storyboard-authoritative-v5",
                )
                output = text.generate_json(
                    """Plan a premium G$LIDE science/technology explanation edit. Return exactly one scene for every supplied planning beat_id and never change narration timing. Each planning beat represents one or two final authoritative beats, so NEVER reuse the same primary asset_key on adjacent planning beats. Build a deliberate Premiere-Pro/After-Effects-like visual language using the available motion grammar: multi-layer composition, 2.5D-feeling parallax through foreground/detail layers, camera push/pull/pan/reframe, diagram-like reveals, tracked labels or numbers, kinetic emphasis, object/match transitions, depth, restrained technical HUD/data overlays, and blue/gold paper-cut compositing. Do not use an effect merely because it exists; each motion, layer and SFX cue must explain what the narrator is saying.

Use the smallest paid image set that still looks genuinely varied. Respect the supplied primary asset limit. Meet or exceed the supplied minimum unique primary assets. No primary asset may dominate the episode. Reuse an asset only when the viewer is intentionally returning to the same concept, and change framing/layers to show progression. At least the supplied minimum layered-scene ratio must use secondary assets. Reuse secondary detail/HUD assets when sensible rather than generating needless images.

Keep the structured response compact: visual_caption and motion emphasis at six words or fewer; each visual_prompt at thirty words or fewer; no prose explanations outside schema fields. Sound cues must correspond to visible actions: soft-trace for diagram/data movement, tick for numbers/UI, paper/swipe for directional reveals, impact only for rare major reveals. Keep many beats without SFX so sound has hierarchy. Use hard cuts often; reserve paper-wipe, match-cut and object-transition for motivated transitions. Use annotations sparingly. Visual prompts must describe the actual explanatory image to generate, not editing instructions or text-heavy title cards. Favor diagrams, cutaways, mechanisms, scale comparisons, maps/data or object relationships over generic decorative art. Never request readable paragraphs in generated images.""",
                    planning_input,
                    STORYBOARD_SCHEMA,
                    max_output_tokens=storyboard_output_tokens,
                )
                group_scenes = output.value["scenes"]
                expected_group_ids = {group["id"] for group in planning_groups}
                planned_group_ids = {scene["beat_id"] for scene in group_scenes}
                if (
                    len(planned_group_ids) != len(group_scenes)
                    or planned_group_ids != expected_group_ids
                ):
                    raise RuntimeError(
                        "compact storyboard must contain every planning beat exactly once"
                    )

                # If the model reuses one asset on adjacent planning beats, repair the
                # sequence locally from its already-approved asset catalog instead of
                # repeating the paid planning request.
                asset_templates = {}
                for scene in group_scenes:
                    asset_templates.setdefault(scene["asset_key"], scene)

                def compact_tokens(value: str) -> set[str]:
                    return {
                        token for token in re.findall(r"[a-z0-9]+", value.lower())
                        if len(token) > 2
                    }

                for index in range(1, len(group_scenes)):
                    current = group_scenes[index]
                    previous = group_scenes[index - 1]
                    if current["asset_key"] != previous["asset_key"]:
                        continue
                    candidates = [
                        template for key, template in asset_templates.items()
                        if key != previous["asset_key"]
                    ]
                    if not candidates:
                        continue
                    beat_tokens = compact_tokens(planning_groups[index]["text"])
                    replacement = max(
                        candidates,
                        key=lambda template: len(
                            beat_tokens & compact_tokens(
                                " ".join([
                                    str(template.get("visual_caption", "")),
                                    str(template.get("visual_prompt", "")),
                                ])
                            )
                        ),
                    )
                    current["asset_key"] = replacement["asset_key"]
                    current["visual_role"] = replacement["visual_role"]
                    current["visual_prompt"] = replacement["visual_prompt"]
                    current["secondary_assets"] = json.loads(json.dumps(
                        replacement.get("secondary_assets", [])
                    ))
                    current["subject_bounds"] = json.loads(json.dumps(
                        replacement.get("subject_bounds", [])
                    ))

                # Expand each compact planning scene back onto the original authoritative
                # narration beats. Two beats may intentionally share one explanatory
                # asset, matching the policy's maximum consecutive reuse of two.
                group_scene_map = {scene["beat_id"]: scene for scene in group_scenes}
                beat_map = {beat["id"]: beat for beat in beats}
                motion_types = [
                    "push-in", "pan-left", "reframe", "pull-out",
                    "pan-right", "layer-reveal",
                ]
                planned_scenes = []
                for group_index, group in enumerate(planning_groups):
                    template = group_scene_map[group["id"]]
                    for member_index, beat_id in enumerate(group["source_beat_ids"]):
                        beat = beat_map[beat_id]
                        scene = json.loads(json.dumps(template))
                        scene["beat_id"] = beat_id
                        caption = " ".join(
                            str(beat["text"]).split()[:6]
                        ).rstrip(".,;:!?")
                        scene["visual_caption"] = caption
                        motion = scene.setdefault("motion", {})
                        if member_index == 1:
                            current_type = motion.get("type", "push-in")
                            try:
                                motion_index = motion_types.index(current_type) + 1
                            except ValueError:
                                motion_index = group_index + 1
                            motion["type"] = motion_types[motion_index % len(motion_types)]
                            motion["transition"] = "cut"
                            motion["audio_cue"] = "none"
                        motion["emphasis"] = caption

                        # Layer timings authored for a paired planning beat must be
                        # clamped inside the shorter authoritative beat before render.
                        beat_duration = max(0.05, float(beat["duration"]))
                        for layer in scene.get("secondary_assets", []):
                            start_offset = max(
                                0.0, min(
                                    float(layer.get("start_offset", 0.0)),
                                    max(0.0, beat_duration - 0.01),
                                )
                            )
                            remaining = max(0.01, beat_duration - start_offset)
                            layer["start_offset"] = round(start_offset, 6)
                            layer["duration"] = round(
                                min(
                                    max(0.01, float(layer.get("duration", remaining))),
                                    remaining,
                                ),
                                6,
                            )
                        planned_scenes.append(scene)

                self._record_text(production_id, "storyboard-authoritative-v5", output)

            planned = {scene["beat_id"]: scene for scene in planned_scenes}
            expected = {beat["id"] for beat in beats}
            if len(planned) != len(planned_scenes) or set(planned) != expected:
                raise RuntimeError("storyboard must contain every editorial beat exactly once")

            primary_keys = {scene["asset_key"] for scene in planned_scenes}
            if len(primary_keys) > primary_limit:
                raise RuntimeError(
                    f"storyboard requested {len(primary_keys)} primary assets; limit is {primary_limit}"
                )
            if not previous_scenes and len(primary_keys) < minimum_unique:
                raise RuntimeError(
                    f"storyboard has only {len(primary_keys)} unique primary assets; minimum is {minimum_unique}"
                )
            layered_ratio = sum(bool(scene.get("secondary_assets")) for scene in planned_scenes) / len(planned_scenes)
            if not previous_scenes and layered_ratio < minimum_layered_ratio:
                raise RuntimeError(
                    f"storyboard layered-scene ratio {layered_ratio:.1%} is below {minimum_layered_ratio:.1%}"
                )

            requested_asset_keys = set(primary_keys)
            requested_asset_keys.update(
                layer["asset_key"]
                for scene in planned_scenes
                for layer in scene.get("secondary_assets", [])
            )
            if previous_scenes and not requested_asset_keys.issubset(asset_inventory):
                unknown = sorted(requested_asset_keys - set(asset_inventory))
                raise RuntimeError(f"corrective storyboard invented uncached assets: {unknown}")

            merged = []
            for beat in beats:
                scene = planned[beat["id"]]
                self._safe_id(scene["asset_key"])
                for layer in scene.get("secondary_assets", []):
                    self._safe_id(layer["asset_key"])
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
                    "secondary_assets": scene.get("secondary_assets", []),
                    "subject_bounds": scene.get("subject_bounds", []),
                })
            storyboard_path.write_text(
                json.dumps({
                    "timing_source": "elevenlabs-normalized-alignment",
                    "planning_mode": "cached-correction" if previous_scenes else "fresh-premium",
                    "scenes": merged,
                }, indent=2) + "\n",
                encoding="utf-8",
            )

        self.runner.run(production_id, "storyboard-authoritative-v5", storyboard_stage)
        storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
        qa_policy = json.loads(
            (self.root / "config/qa-policy.json").read_text(encoding="utf-8")
        )
        normalized_storyboard = self._normalize_editorial_intent(
            storyboard, qa_policy
        )
        if normalized_storyboard != storyboard:
            storyboard = normalized_storyboard
            storyboard_path.write_text(
                json.dumps(storyboard, indent=2) + "\n", encoding="utf-8"
            )
        # Editorial structure must pass locally before the first paid image request.
        # This catches repetitive assets, weak layering, motion spam and missing SFX
        # while the only sunk cost is the already-checkpointed planning/narration work.
        editorial_failures, editorial_metrics = check_editorial(
            storyboard, spec["format"], qa_policy
        )
        (work / "storyboard-preflight.json").write_text(
            json.dumps({
                "passed": not editorial_failures,
                "failures": editorial_failures,
                "metrics": editorial_metrics,
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        if editorial_failures:
            raise RuntimeError(
                "storyboard failed zero-image-spend editorial preflight: "
                + "; ".join(editorial_failures)
            )
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
        # Preflight the complete image batch before generating the first image.
        image_batch = []
        for asset_key in unique_assets:
            target = asset_dir / f"{asset_key}.png"
            if target.exists():
                # Checkpointed paid media is never charged a second time in preflight.
                continue
            is_hero = asset_key in hero_keys and asset_key not in secondary_keys
            image_batch.append((
                hero_image_cost_model if is_hero else support_image_cost_model,
                Usage(images=1),
            ))
        # Reserve room for the one thumbnail as part of the same visual-spend plan.
        # The later thumbnail stage still performs its own exact reservation; this
        # batch check only guarantees we do not knowingly consume the asset budget
        # and discover at the end that the release thumbnail cannot be finished.
        thumbnail_checkpoint = work / "thumbnail.png"
        if not thumbnail_checkpoint.exists():
            image_batch.append((thumbnail_cost_model, Usage(images=1)))
        self.budget.reserve_batch(
            spec, image_batch, provider="openai", stage="planned-visual-and-thumbnail-batch"
        )
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
            "music": str(music.path), "audio": {"music_source": music.source_url, "music_license": music.license, "music_volume": 0.03, "duck_under_voice": True},
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
                "annotation": self._fit_annotation(
                    scene["motion"].get("annotation"), scene["duration"]
                ),
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
        scene_total = sum(float(scene["duration"]) for scene in manifest["scenes"])
        if scene_total <= 0:
            raise RuntimeError("render manifest has no positive scene duration")
        manifest_tolerance = max(0.75, narration_seconds * 0.01)
        if abs(scene_total - narration_seconds) > manifest_tolerance:
            timeline_scale = narration_seconds / scene_total
            cursor = 0.0
            for scene in manifest["scenes"]:
                duration = float(scene["duration"]) * timeline_scale
                scene["start"] = round(cursor, 6)
                cursor += duration
                scene["end"] = round(cursor, 6)
                scene["duration"] = round(duration, 6)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        video_path = self.root / "build" / production_id / "video.mp4"
        self.runner.run(
            production_id, "render-full-duration-v11",
            lambda: render(load_project(manifest_path), self.root), attempts=1,
        )
        rendered_seconds = self._duration(video_path)
        duration_tolerance = max(0.75, narration_seconds * 0.01)
        if abs(rendered_seconds - narration_seconds) > duration_tolerance:
            raise RuntimeError(
                f"render duration {rendered_seconds:.2f}s does not match narration "
                f"{narration_seconds:.2f}s within {duration_tolerance:.2f}s"
            )

        metadata_path = work / "upload-metadata.json"
        policy = load_metadata_policy(self.root / "config/youtube-metadata-policy.json")
        def metadata_stage():
            self._require_absent(metadata_path, "metadata")
            self._reserve(spec, text_model, Usage(input_tokens=max(1, len(script) // 4), output_tokens=12000))
            output = text.generate_json(
                "Create accurate YouTube metadata for G$LIDE. No hashtags in title. Describe the actual video, place only a few relevant hashtags at the description end, and use chapters only for long videos.",
                f"FORMAT={spec['format']}\nSCRIPT\n{script}", METADATA_SCHEMA,
            )
            metadata = apply_locked_upload_defaults(
                output.value | {"format": spec["format"]}, policy
            )
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
