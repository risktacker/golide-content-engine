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

from ..captions import respell_from_script, clean_timed_words, words_to_beats, words_to_srt
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
from ..engine.content_rules import SCRIPT_SCHEMA, chapter_problems, follow_problems, length_problems, script_display, script_instructions, script_text, SPOKEN_SCHEMA, SPOKEN_PASS_EFFORT, spoken_pass_instructions, merge_spoken
from .recording import RecordingLengthError, check_recording_length
from .stage_runner import StageRunner


TITLE_FIX_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"titles": {"type": "array", "items": {"type": "string"}}},
    "required": ["titles"],
}

MAX_REDRAWS = 2                    # extra pictures per video for unclear drawings
REDRAW_COUNTER = ".redraws"        # lives in the video's illustration folder


def redraws_used(counter: Path) -> int:
    try:
        return int(counter.read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0

class RenderHeld(RuntimeError):
    """The owner has paused rendering until a new visual style is approved."""


def transcription_prompt(script: str) -> str:
    """Spelling hints for speech-to-text: the brand plus the script's names.

    Whisper-style models copy the spelling of words they see in the prompt, so
    "GOLIDE" (said "GO-lide") is written correctly instead of a sound-alike.
    """
    names: list[str] = []
    for word in re.findall(r"\b[A-Z][A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?\b", script):
        if word not in names and word.lower() not in {"i", "the", "a", "an", "and", "but", "so", "you", "it", "this", "that"}:
            names.append(word)
    return "GOLIDE, golidee.com. " + ", ".join(names[:60]) + "."


def render_hold_reason(root: Path, format_name: str) -> str | None:
    path = Path(root) / "config" / "render-hold.json"
    if not path.exists():
        return None
    if os.getenv("GOLIDE_RENDER_HOLD_BYPASS") == "1":
        return None  # private previews for the owner's approval only
    hold = json.loads(path.read_text(encoding="utf-8"))
    if format_name in hold.get("hold_formats", []):
        return str(hold.get("reason") or "rendering is on hold")
    return None


def youtube_thumbnail_prompt(title: str, moment: str = "", colors: list[str] | None = None) -> str:
    """The YouTube thumbnail brief: the static-post look in two or three meaning colours
    (owner direction 2026-10-18; see vector.thumbnail_style). No people; the short hook
    is typeset afterwards by code, so the image itself has no text."""
    from ..vector.thumbnail_style import DEFAULT, thumbnail_prompt

    return thumbnail_prompt(title, moment, list(colors or DEFAULT))


class WaitingOwnerVoice(RuntimeError):
    """Checkpointed pause after topic research and script generation."""

    def __init__(self, production_id: str, title: str, script: str):
        super().__init__("owner voice recording is required to resume production")
        self.production_id = production_id
        self.title = title
        self.script = script


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

    @staticmethod
    def _storyboard_facts(spec: dict, work: Path) -> str:
        """What the storyboard artist needs to draw the real things (2026-10-23)."""
        parts = []
        source = spec.get("source_breakout") or {}
        if source.get("title"):
            parts.append("TRENDING VIDEO THIS MODELS: " + str(source["title"]) + " | "
                         + str(source.get("description", ""))[:300])
        try:
            research = json.loads((work / "research.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            research = {}
        claims = research.get("claims") or research.get("facts") or []
        lines = []
        for item in claims[:12]:
            text = item.get("claim") or item.get("text") or item.get("fact") if isinstance(item, dict) else item
            if text:
                lines.append("- " + str(text)[:220])
        if research.get("summary"):
            parts.append("STORY: " + str(research["summary"])[:600])
        if lines:
            parts.append("RESEARCH FACTS:\n" + "\n".join(lines))
        parts.append("LOOK IT UP: before describing any real, named product, vehicle, robot or device, "
                     "use web search to see what it actually looks like, and describe that real design.")
        return "\n".join(parts) + "\n"

    @staticmethod
    def _source_video_block(spec: dict) -> str:
        """The trending video this script models (2026-10-22: model it, not just reference it)."""
        b = spec.get("source_breakout") or {}
        if not b.get("title"):
            return ""
        return ("\n\nSOURCE VIDEO (the trending video we are modelling: follow its angle and the order "
                "it tells the story in, our facts and our words)\n"
                + json.dumps({k: b.get(k) for k in ("title", "channel", "views", "views_per_hour",
                                                     "duration_seconds", "description")}))

    def _recent_scripts(self, production_id: str, limit: int = 6) -> list[str]:
        """The last few published scripts, so a new one never reuses their openings."""
        records = []
        for path in (self.root / "data" / "production-records").glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if record.get("production_id") != production_id and record.get("narration"):
                records.append((str(record.get("recorded_at", "")), str(record["narration"])))
        return [text for _, text in sorted(records, reverse=True)[:limit]]

    def _modelled_titles(self, spec, production_id: str, text, text_model: str,
                         candidates: list[dict]) -> list[dict]:
        """Keep candidates whose title is the source title with 1 to 3 words changed.
        Titles that fail get one cheap fix; a title still failing falls back to the
        source title plus "Explained" (one word, the channel's own word)."""
        from ..youtube.breakouts import title_changes, title_tweak_problem

        bad = [c for c in candidates
               if title_tweak_problem(c["breakout"]["title"], str(c.get("model_title", "")))]
        if bad:
            ask = [{"source_title": c["breakout"]["title"], "our_title": c.get("model_title", ""),
                    "problem": title_tweak_problem(c["breakout"]["title"], str(c.get("model_title", "")))}
                   for c in bad]
            self._reserve(spec, text_model, Usage(input_tokens=300 + 60 * len(ask), output_tokens=1500),
                          stage="trend-candidates")
            try:
                fixed = text.generate_json(
                    "Each item has a trending video's exact title (source_title). Write our_title: that "
                    "exact title with ONE to THREE words changed so it is ours. Keep its order, hook, "
                    "keywords and capitals; drop hashtags. Return the titles in the same order.",
                    json.dumps(ask), TITLE_FIX_SCHEMA, max_output_tokens=1500,
                )
                self._record_text(production_id, "trend-titles", fixed)
                for c, title in zip(bad, fixed.value.get("titles", [])):
                    c["model_title"] = str(title).strip()
            except Exception as exc:  # noqa: BLE001 - the fallback below still applies
                print(json.dumps({"status": "title_fix_failed", "error": str(exc)[:200]}))
        for c in candidates:
            source = c["breakout"]["title"]
            if title_tweak_problem(source, str(c.get("model_title", ""))):
                clean = " ".join(re.sub(r"#\w+", " ", source).split())
                c["model_title"] = (clean + " Explained")[:100]
            c["title_changes"] = title_changes(source, c["model_title"])
        from ..youtube.breakouts import is_english
        # 2026-10-28: an English channel never publishes a title in another language.
        return [c for c in candidates if not title_tweak_problem(c["breakout"]["title"], c["model_title"])
                and is_english(c["model_title"]) and is_english(c["breakout"]["title"])]

    def _redraw_if_unclear(self, spec, part, prompt: str, target: Path, line_art, cost_model: str,
                           production_id: str, reference: Path | None = None) -> None:
        """2026-10-21: a picture that would read as an undefined block (all glow, empty, a
        tangle) is drawn once more with the problem named; the better of the two is kept.
        At most MAX_REDRAWS per video (owner: "cap it 2 per video"), counted on disk so a
        resumed run never starts the count again."""
        from ..vector.illustrate import picture_problems, vectorize
        from ..vector.scene_art import picture_size

        counter = target.parent / REDRAW_COUNTER
        used = redraws_used(counter)
        if used >= MAX_REDRAWS:
            return
        try:
            problems = picture_problems(vectorize(target))
        except Exception:  # a picture the tracer cannot read at all
            problems = ["the drawing has no clear lines; draw the object with a clean white outline"]
        if not problems:
            return
        print(json.dumps({"status": "picture_redrawn", "picture": part.picture_id, "problems": problems,
                          "redraw": used + 1, "of": MAX_REDRAWS}))
        retry = target.with_name(target.stem + "-retry.png")
        try:
            self._reserve(spec, cost_model, Usage(images=1), stage="illustrations")
            counter.write_text(str(used + 1), encoding="utf-8")  # counted before the paid call
            output = line_art.create(prompt + " FIX THESE: " + "; ".join(problems) + ".", retry,
                                     picture_size(str(spec["format"]), part),
                                     **({"reference": reference} if reference else {}))
            self._record_image(production_id, "illustrations", cost_model, output)
            if len(picture_problems(vectorize(retry))) <= len(problems):
                retry.replace(target)
        except Exception as exc:  # the first picture still stands
            print(json.dumps({"status": "picture_redraw_failed", "picture": part.picture_id,
                              "error": str(exc)[:200]}))
        finally:
            retry.unlink(missing_ok=True)

    @staticmethod
    def _stamp_thumbnail(work: Path, thumbnail: Path) -> None:
        """Typeset the opening card's line on the dark left, ending before the art (2026-10-25)."""
        try:
            from ..vector.thumbnail_style import palette_rgb, thumbnail_colors
            from ..vector.thumbnail_v2 import stamp_overlap as stamp_thumbnail
            plan = json.loads((work / "visual-plan.json").read_text(encoding="utf-8"))
            cover = plan.get("cover") or {}
            colors = thumbnail_colors(cover, plan.get("scenes") or [])
            # 2026-10-25: the thumbnail carries the opening card's line, not 1 to 3 words.
            words = str(cover.get("text") or cover.get("thumbnail_text") or "")
            punch = str(cover.get("gold") or cover.get("thumbnail_punch") or "")
            stamp_thumbnail(thumbnail, words, punch, palette_rgb(colors))
        except Exception as exc:  # the plain artwork still works as a thumbnail
            print(json.dumps({"status": "thumbnail_text_skipped", "error": str(exc)[:300]}))

    def _sharpen_cover_line(self, spec, production_id: str, text, text_model: str, cover: dict,
                            recent: list[dict]) -> dict:
        """The opening-card line is also the thumbnail (2026-10-25): one cheap fix when it
        repeats the title, uses the worn "Who ...?" shape or opens like a recent line."""
        from ..vector.cover import clean_cover_text
        from ..vector.cover_line import line_problems, record_line
        title = str(spec.get("title", ""))
        topic = str((spec.get("source_breakout") or {}).get("url") or spec.get("selected_topic_source") or "")
        problems = line_problems(str(cover.get("text", "")), title, recent, topic)
        if problems:
            schema = {"type": "object", "additionalProperties": False,
                      "properties": {"text": {"type": "string"}, "gold": {"type": "string"}},
                      "required": ["text", "gold"]}
            try:
                self._reserve(spec, text_model, Usage(input_tokens=1500, output_tokens=1500))
                fixed = text.generate_json(
                    "Rewrite the line that opens a GOLIDE video and is printed on its thumbnail. 3 to 6 "
                    "words, Title Case: a claim or a sharp question about this story that the title sets up "
                    "but does not say. Never repeat the title's words, never start with \"Who\", never open "
                    "like a recent line. \"gold\" is the 1 to 3 punch words copied exactly from the line.",
                    f"TITLE: {title}\nBRIEF: {str(spec.get('brief', ''))[:800]}\nLINE: {cover.get('text', '')}\n"
                    f"PROBLEMS: {'; '.join(problems)}\nRECENT LINES: "
                    + "; ".join(r.get("text", "") for r in recent),
                    schema, max_output_tokens=1500)
                self._record_text(production_id, "cover-line", fixed)
                new_text, new_gold = clean_cover_text(str(fixed.value.get("text", "")), str(fixed.value.get("gold", "")))
                if new_text and len(line_problems(new_text, title, recent, topic)) < len(problems):
                    cover["text"], cover["gold"] = new_text, new_gold
            except Exception as exc:  # the first line still stands
                print(json.dumps({"status": "cover_line_fix_failed", "error": str(exc)[:200]}))
        cover["thumbnail_text"], cover["thumbnail_punch"] = cover.get("text", ""), cover.get("gold", "")
        record_line(self.root, production_id, str(spec.get("format", "")), title, str(cover.get("text", "")), topic)
        return cover

    @staticmethod
    def _thumbnail_moment(work: Path) -> str:
        try:
            plan = json.loads((work / "visual-plan.json").read_text(encoding="utf-8"))
            return str((plan.get("cover") or {}).get("thumbnail_moment") or "")
        except (OSError, ValueError):
            return ""

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
        # 2026-10-22: once a topic is chosen it is locked. A resumed run (after the owner's
        # recording) used to choose again and swapped the Roadster video's title for another
        # candidate's ("Apple CEO John Ternus..."), while the script and visuals stayed.
        topic_locked = bool(spec.get("selected_topic_source")) and \
            spec.get("platform_demand", {}).get("verdict") == "pass"
        if self.youtube is not None and not topic_locked:
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
                # A breakout candidate always wins, here as in the fresh-discovery path.
                from ..youtube.pulse import choose as choose_breakout_first
                candidate, demand = choose_breakout_first(gate, spec)
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
                    from ..youtube.breakouts import BREAKOUT_RULES, find_breakouts
                    from ..youtube.pulse import fresh_headlines

                    headlines = json.dumps(fresh_headlines(), separators=(",", ":"))
                    # 2026-10-21: YouTube decides the topic; the news only supplies facts.
                    # 2026-10-22: same format only, numbers bar, and NO news fallback: with
                    # no trending video to model there is no script that day.
                    fmt = str(spec["format"])
                    try:
                        breakouts = find_breakouts(self.youtube, fmt)
                    except Exception as exc:  # noqa: BLE001
                        print(json.dumps({"status": "breakouts_unavailable", "error": str(exc)[:200]}))
                        breakouts = []
                    (work / "breakouts.json").write_text(json.dumps(breakouts, indent=2) + "\n", encoding="utf-8")
                    if not breakouts:
                        raise TopicDemandRejected(
                            f"no trending {fmt} video cleared the numbers bar in the last 96 hours, "
                            "so there is nothing to model today"
                        )
                    instructions = (
                        "Create 3 to 5 GOLIDE video topic candidates built on the YouTube BREAKOUTS below.\n\n"
                        + BREAKOUT_RULES
                        + "\nEach candidate needs a concise search query, a brief (what the video explains in "
                        "plain words and the science or engineering underneath), an evidence summary, one direct "
                        "credible source URL found through web search (the company, the original report or a "
                        "major outlet), broke_on and science_angle. Reject rumours and unsupported claims."
                    )
                    packet = (f"CURRENT BRIEF\n{spec['brief']}\n\nBREAKOUTS\n"
                              + json.dumps([{k: b.get(k) for k in ("title", "channel", "views", "views_per_hour",
                                                                    "breakout", "hours_old", "duration_seconds",
                                                                    "description")}
                                            for b in breakouts], separators=(",", ":"))
                              + f"\n\nRECENT GOLIDE TOPICS (repeats are fine with a new narrative)\n"
                              f"{json.dumps(recent_titles)}\n\nFRESH HEADLINES (facts only)\n{headlines}")
                    output = text.generate_json(
                        instructions,
                        packet,
                        TREND_CANDIDATES_SCHEMA,
                        web_search=True,
                        # 2026-10-19: 3,000 cut the answer off once trend fields and
                        # headlines were added (the budget includes reasoning).
                        max_output_tokens=12000,
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
                        source = int(item.get("source_breakout", -1))
                        candidates.append({
                            **item,
                            "evidence_valid": True,
                            "platform_seed_demand": asdict(seed_demand),
                            **({"breakout": breakouts[source]} if 0 <= source < len(breakouts) else {}),
                        })
                    # Every candidate models a trending video, and its title is that video's
                    # title with one to three words changed (checked here, not trusted).
                    candidates = self._modelled_titles(spec, production_id, text, text_model,
                                                       [c for c in candidates if c.get("breakout")])
                    if not candidates:
                        raise TopicDemandRejected(
                            "no candidate modelled a trending video with a properly tweaked title"
                        )
                    from ..youtube.pulse import attach as attach_pulse
                    attach_pulse(self.youtube, candidates)
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
                from ..youtube.pulse import choose as choose_with_pulse
                candidate, demand = choose_with_pulse(gate, spec)

            spec["brief"] = candidate["brief"]
            spec["title"] = candidate.get("model_title") or candidate.get("title", spec.get("title", production_id))
            if candidate.get("breakout"):
                # The YouTube title is modelled on the winning video's title (2026-10-21).
                spec["model_title"] = str(candidate.get("model_title") or candidate["title"]).strip()
                spec["source_breakout"] = candidate["breakout"]
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
        # An owner-approved topic change ships its own research next to the
        # script override (production-queue/<id>.research.json).
        research_override = self.root / "production-queue" / f"{production_id}.research.json"
        if research_override.exists():
            research_path.write_text(research_override.read_text(encoding="utf-8"), encoding="utf-8")
        research = json.loads(research_path.read_text(encoding="utf-8"))
        self._budget(spec)

        script_path = work / "script.txt"
        scene_plan_path = work / "scene-plan.json"
        source_video = self._source_video_block(spec)

        def script_problems(plan: dict) -> list[str]:
            # 2026-10-29: only what the engine needs (length, chapters, the follow line);
            # the style comes from the modelled videos, not from rules.
            return (length_problems(plan, str(spec["format"]))
                    + chapter_problems(plan, str(spec["format"])) + follow_problems(plan, str(spec["format"])))

        models_path = work / "model-scripts.json"
        # 2026-10-29: production-queue/<id>.rescript asks for a fresh script (new token, new
        # script), only while the recording has not been made.
        rescript = self.root / "production-queue" / f"{production_id}.rescript"
        if rescript.exists() and not (work / "timed-words-owner.json").exists():
            token = rescript.read_text(encoding="utf-8").strip()
            done = work / "rescript-done.txt"
            if not done.exists() or done.read_text(encoding="utf-8").strip() != token:
                for name in ("script.txt", "scene-plan.json", "model-scripts.json", "spoken-pass.json"):
                    (work / name).unlink(missing_ok=True)
                self.database.execute("DELETE FROM stage_runs WHERE production_id=? AND stage='script'",
                                      (production_id,))
                done.write_text(token + "\n", encoding="utf-8")
                print(json.dumps({"status": "rescript", "production_id": production_id, "token": token}))

        def model_scripts_block() -> str:
            """Transcripts of the videos this script models (fetched once, kept for a resume)."""
            if models_path.exists():
                models = json.loads(models_path.read_text(encoding="utf-8"))
            else:
                from ..youtube.transcripts import choose_models
                try:
                    breakouts = json.loads((work / "breakouts.json").read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    breakouts = []
                models = choose_models(spec.get("source_breakout"), breakouts if isinstance(breakouts, list) else [],
                                       str(spec["format"]))
                models_path.write_text(json.dumps(models, indent=2) + "\n", encoding="utf-8")
                print(json.dumps({"status": "model_scripts", "count": len(models),
                                  "videos": [m["url"] for m in models]}))
            if not models:
                return ""
            return "\n\nMODEL SCRIPTS (videos working on YouTube now; study how they talk to the viewer)\n" + "\n\n".join(
                f"--- {m.get('title') or m['url']} ({m.get('channel', '')}) ---\n{m['transcript']}" for m in models)

        # 2026-10-22: an 8-minute script plus its visual fields needs a bigger budget.
        script_tokens = 16000 if str(spec["format"]) == "long" else 6000

        def script_stage():
            self._require_absent(script_path, "script")
            models_block = model_scripts_block()
            script_input = spec["brief"] + json.dumps(research) + source_video + models_block
            self._reserve(
                spec, text_model,
                Usage(input_tokens=max(1, len(script_input) // 4), output_tokens=script_tokens),
                stage="script",
            )
            output = text.generate_json(
                script_instructions(str(spec["format"]), str(spec["id"])),
                f"TOPIC BRIEF\n{spec['brief']}{source_video}{models_block}\n\nVERIFIED RESEARCH\n{json.dumps(research)}",
                SCRIPT_SCHEMA,
                max_output_tokens=script_tokens,
            )
            plan = dict(output.value)
            problems = script_problems(plan)
            for _round in range(2):
                if not problems:
                    break
                # Rewrite when the script is choppy or breaks a structure rule; checked again after.
                self._record_text(production_id, "script-draft", output)
                self._reserve(spec, text_model, Usage(input_tokens=max(1, len(json.dumps(plan)) // 3 + 3000),
                                                      output_tokens=script_tokens))
                output = text.generate_json(
                    script_instructions(str(spec["format"]), str(spec["id"])),
                    f"TOPIC BRIEF\n{spec['brief']}{source_video}{models_block}\n\nVERIFIED RESEARCH\n{json.dumps(research)}"
                    f"\n\nYOUR PREVIOUS DRAFT\n{json.dumps(plan)}\n\nREWRITE IT. Fix these problems: "
                    + "; ".join(problems) + ". Keep the facts, the length and the way it talks to the viewer.",
                    SCRIPT_SCHEMA,
                    max_output_tokens=script_tokens,
                )
                plan = dict(output.value)
                problems = script_problems(plan)
            # 2026-10-24 spoken pass: the draft is rewritten the way the owner says things
            # (his approved scripts are the reference), line for line so the visuals still
            # match. Kept only when it breaks no more rules than the draft.
            draft_lines = [{"text": line.get("text", ""), "emphasis": line.get("emphasis", "")}
                           for line in plan.get("lines", [])]
            self._reserve(spec, text_model, Usage(input_tokens=max(1, len(json.dumps(draft_lines)) // 3 + 6000),
                                                  output_tokens=script_tokens * 2))
            try:
                spoken_out = text.generate_json(
                    spoken_pass_instructions(str(spec["format"])),
                    "DRAFT LINES\n" + json.dumps({"lines": draft_lines}, ensure_ascii=False),
                    SPOKEN_SCHEMA,
                    max_output_tokens=script_tokens * 2,  # high effort spends tokens thinking first
                    reasoning_effort=SPOKEN_PASS_EFFORT,
                )
                self._record_text(production_id, "script-spoken", spoken_out)
                spoken = merge_spoken(plan, dict(spoken_out.value))
            except Exception as error:  # the draft still stands if this pass fails
                spoken, report = None, {"status": "failed", "reason": str(error)[:300]}
            else:
                report = {"status": "unmatched", "reason": "the rewrite changed the number of lines"}
            if spoken is not None:
                spoken_problems = script_problems(spoken)
                if len(spoken_problems) <= len(problems):
                    plan, problems = spoken, spoken_problems
                    report = {"status": "applied"}
                else:
                    report = {"status": "discarded", "reason": "; ".join(spoken_problems)[:300]}
            # 2026-10-25: written down so the script email says what happened to the pass.
            (work / "spoken-pass.json").write_text(json.dumps(report) + "\n", encoding="utf-8")
            print(json.dumps({"status": "spoken_pass_" + report["status"], **report}))
            if problems:
                print(json.dumps({"status": "script_rules_unmet_after_rewrites", "problems": problems}))
            scene_plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
            script_path.write_text(script_text(plan) + "\n", encoding="utf-8")
            self._record_text(production_id, "script", output)
        self.runner.run(production_id, "script", script_stage)
        # An owner-approved rewrite committed as production-queue/<id>.script-plan.json
        # replaces the generated script until the recording has been processed; the
        # owner reads the rewrite shown in Studio, so words and voice stay matched.
        override = self.root / "production-queue" / f"{production_id}.script-plan.json"
        if override.exists() and not (work / "timed-words-owner.json").exists():
            plan = json.loads(override.read_text(encoding="utf-8"))
            if script_text(plan) != script_path.read_text(encoding="utf-8").strip():
                scene_plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
                script_path.write_text(script_text(plan) + "\n", encoding="utf-8")
        # 2026-10-27: every number in the script is written as digits (also fixes a plan
        # written before the rule, until the recording has been processed).
        if scene_plan_path.exists() and not (work / "timed-words-owner.json").exists():
            from ..engine.numerals import plan_digits
            current = json.loads(scene_plan_path.read_text(encoding="utf-8"))
            fixed = plan_digits(current)
            if fixed != current:
                scene_plan_path.write_text(json.dumps(fixed, indent=2) + "\n", encoding="utf-8")
                script_path.write_text(script_text(fixed) + "\n", encoding="utf-8")
        script = script_path.read_text(encoding="utf-8").strip()
        self._budget(spec)

        owner_voice_ref = str(spec.get("owner_voice_media_ref", "")).strip()
        if not owner_voice_ref:
            plan_for_display = json.loads(scene_plan_path.read_text(encoding="utf-8")) if scene_plan_path.exists() else None
            raise WaitingOwnerVoice(
                production_id,
                str(spec.get("title", production_id)),
                script_display(plan_for_display) if plan_for_display else script,
            )

        from .voice_reset import reset_if_recording_changed
        reset_if_recording_changed(self.database, self.root, production_id, work, owner_voice_ref)

        narration = work / "narration-owner.wav"
        timed_words_path = work / "timed-words-owner.json"

        def _normalized_words(value: str) -> str:
            return " ".join(re.findall(r"[a-z0-9']+", value.lower()))

        def voice_stage():
            # 2026-10-27: the timed words are written only after every check passed, so
            # both files on disk mean the stage finished and only its checkpoint record
            # was lost (a run stopped right after). Reconcile instead of failing forever.
            if timed_words_path.exists():
                try:
                    finished = bool(json.loads(timed_words_path.read_text(encoding="utf-8")))
                except ValueError:
                    finished = False
                if finished:
                    if not narration.exists():
                        fetch_narration()  # free: the paid transcription is kept
                    print(json.dumps({"status": "owner_voice_reconciled", "production_id": production_id}))
                    return
                timed_words_path.unlink(missing_ok=True)
            # A failed attempt leaves only free-to-redo local files; clear them
            # so a retry (for example after a fixed recording) can run again.
            if not timed_words_path.exists():
                narration.unlink(missing_ok=True)
            try:
                _voice_stage_body()
            except Exception:
                narration.unlink(missing_ok=True)
                (work / "owner-voice-source").unlink(missing_ok=True)
                raise

        def fetch_narration():
            """Download the owner's recording and convert it (free; 2026-10-27: also used to
            restore a narration file a failed retry removed after the stage had finished)."""
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

        def _voice_stage_body():
            self._require_absent(narration, "owner-voice")
            self._require_absent(timed_words_path, "owner-voice")
            source = work / "owner-voice-source"
            fetch_narration()
            # Reject a wrong-length recording before paying for transcription.
            try:
                check_recording_length(str(spec["format"]), self._duration(narration))
            except RecordingLengthError:
                narration.unlink(missing_ok=True)
                source.unlink(missing_ok=True)
                raise

            captioner = self.providers.captions(live=True)
            try:
                output = captioner.transcribe_words(narration, prompt=transcription_prompt(script))
            except TypeError:  # providers without spelling hints
                output = captioner.transcribe_words(narration)
            words = output.value
            if not words:
                raise RuntimeError("owner voice transcription returned no word timing")

            transcript = " ".join(str(item.get("word", "")) for item in words)
            # Compare words, not characters, and disable autojunk: on long
            # strings difflib treats common letters and spaces as junk, which
            # scored a faithful reading as 0.11.
            similarity = difflib.SequenceMatcher(
                None,
                _normalized_words(script).split(),
                _normalized_words(transcript).split(),
                autojunk=False,
            ).ratio()
            if similarity < 0.55:
                raise RuntimeError(
                    f"owner voice does not match the approved script closely enough ({similarity:.2f})"
                )

            timed_words_path.write_text(
                json.dumps(words, indent=2) + "\n", encoding="utf-8"
            )

        self.runner.run(production_id, "owner-voice", voice_stage)
        if not narration.exists() and timed_words_path.exists():
            fetch_narration()
            print(json.dumps({"status": "owner_voice_restored", "production_id": production_id}))
        self._budget(spec)
        narration_seconds = self._duration(narration)
        # The owner recording is the master timeline: never retime the voice.
        check_recording_length(str(spec["format"]), narration_seconds)

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

        timed_words = clean_timed_words(respell_from_script(clean_timed_words(timed_words), script))
        if not timed_words:
            raise RuntimeError("owner-voice transcription produced no usable words")

        spoken_srt = work / "spoken-captions-authoritative-v3.srt"

        def caption_stage():
            self._require_absent(spoken_srt, "captions-authoritative-v3")
            spoken_srt.write_text(words_to_srt(timed_words), encoding="utf-8")

        self.runner.run(
            production_id, "captions-authoritative-v3", caption_stage, attempts=1
        )

        # Locked 2026-10-04: new jobs are drawn by the GOLIDE Black vector
        # renderer (code-drawn line art synced to the owner's words). Jobs
        # created before the change, which have no scene plan, keep the old
        # still-image path so their checkpoints remain valid.
        scene_plan_path = work / "scene-plan.json"
        vector_mode = scene_plan_path.exists()
        video_path = self.root / "build" / production_id / "video.mp4"
        if vector_mode:
            from ..vector.align import align_lines
            from ..vector.render import VectorRenderer

            music = MusicRegistry(self.root / "config/music-registry.json").select(
                spec["music"]["mood"], spec["music"].get("track_id")
            )
            plan = json.loads(scene_plan_path.read_text(encoding="utf-8"))
            held = render_hold_reason(self.root, str(spec["format"]))
            already = self.database.rows(
                "SELECT 1 FROM stage_runs WHERE production_id=? AND stage='render-vector-v1' AND status='completed' LIMIT 1",
                (production_id,),
            )
            if held and not already:
                raise RenderHeld(held)

            # Owner direction 2026-10-05: each idea is one animated line
            # illustration, not icons. The storyboard is planned from the
            # final words (never changing them), then one picture per scene.
            from ..providers.openai_media import OpenAILineArtProvider
            from ..vector.illustrate import (
                VISUAL_PLAN_SCHEMA, illustration_prompt, scene_plan_instructions, validate_scenes,
            )

            spoken_lines = [line for line in plan["lines"] if str(line.get("text", "")).strip()]
            visual_plan_path = work / "visual-plan.json"
            illustration_dir = work / "illustrations"

            def spoken_line_times() -> list[tuple[float, float]]:
                timed = align_lines(plan, timed_words, narration_seconds)
                return [(line.start, line.end) for line in timed][:len(spoken_lines)]

            def visual_plan_stage():
                self._require_absent(visual_plan_path, "visual-plan")
                from ..vector.chapters import line_chapters
                owners = line_chapters(plan)
                rows = []
                times = spoken_line_times()
                for i, line in enumerate(spoken_lines):
                    if owners[i] is not None and (i == 0 or owners[i] != owners[i - 1]):
                        chapter = plan["chapters"][owners[i]]
                        rows.append(f"== CHAPTER {chapter.get('number', '')} {chapter.get('title', '')} ==".replace("  ", " "))
                    rows.append(f"{i}: [{times[i][0]:.1f}s] {line['text']}")
                numbered = "\n".join(rows)
                self._reserve(spec, text_model, Usage(input_tokens=len(numbered) // 3 + 1500, output_tokens=8000))
                # 2026-10-23: the storyboard knows what the real things look like: the
                # research, the trending video it models, and one web search for the look of
                # any named product (a brand-new robot is otherwise drawn as a generic one).
                facts = self._storyboard_facts(spec, work)
                from ..vector.cover_line import recent_block, recent_lines
                recent = recent_lines(self.root, production_id)
                output = text.generate_json(
                    scene_plan_instructions(str(spec["format"]), narration_seconds),
                    f"TITLE={spec.get('title', '')}\n{facts}{recent_block(recent)}LINES\n{numbered}",
                    VISUAL_PLAN_SCHEMA,
                    max_output_tokens=10000,
                    web_search=True,
                )
                self.costs.record(production_id, "visual-plan-search", "openai", "web-search",
                                  Usage(tool_calls=1))
                breaks = {i for i in range(1, len(owners)) if owners[i] is not None and owners[i] != owners[i - 1]}
                from ..vector.pacing import scene_range
                raw_scenes = list(output.value["scenes"])
                scenes = validate_scenes(raw_scenes, len(spoken_lines), breaks,
                                         max_scenes=scene_range(str(spec["format"]), narration_seconds)[1] + 2)
                cover = dict(output.value.get("cover") or {})
                number = cover.get("scene")
                cover["scene"] = ""
                if isinstance(number, int) and 1 <= number <= len(raw_scenes):
                    # Map through a line of the chosen scene: validation may re-order,
                    # merge or split scenes, so positions shift but lines do not.
                    line = int(raw_scenes[number - 1].get("first_line", 0))
                    cover["scene"] = next((sc["id"] for sc in scenes
                                           if sc["first_line"] <= line <= sc["last_line"]), "")
                from ..vector.cover import clean_cover_text
                cover["text"], cover["gold"] = clean_cover_text(str(cover.get("text", "")), str(cover.get("gold", "")))
                cover = self._sharpen_cover_line(spec, production_id, text, text_model, cover, recent)
                visual_plan_path.write_text(json.dumps({"scenes": scenes, "cover": cover}, indent=2) + "\n",
                                            encoding="utf-8")
                self._record_text(production_id, "visual-plan", output)

            self.runner.run(production_id, "visual-plan-v1", visual_plan_stage)
            visual_plan = json.loads(visual_plan_path.read_text(encoding="utf-8"))
            from ..vector.layouts import normalize as normalize_layouts
            from ..vector.scene_art import parts as scene_parts
            from ..vector.scene_art import picture_size, try_figure

            from ..vector.pacing import pace_scenes
            # Pacing applies to plans made before it existed too (idempotent).
            scenes = pace_scenes(normalize_layouts(visual_plan["scenes"], str(spec["format"])),
                                 spoken_line_times(), str(spec["format"]))
            line_art = OpenAILineArtProvider(
                self.providers.config["assets"]["support_model"],
                self.providers.config["assets"]["support_quality"],
            )

            def illustrations_stage():
                from ..providers.openai_media import is_moderation_block
                from ..vector.scene_art import calm_prompt, fill_from_neighbours
                from ..vector.thumbnail_v2 import fetch_reference
                # 2026-10-25: scenes that draw the video's real product get a picture of it
                # (the modelled video's thumbnail) for its structure, so a Tesla Roadster or a
                # Centa Painter is drawn as itself, never as a generic car or robot.
                product = str((visual_plan.get("cover") or {}).get("product_name") or "").strip()
                product_ref = None
                if product:
                    product_ref = fetch_reference(str((spec.get("source_breakout") or {}).get("url") or ""),
                                                  work / "product-reference.jpg")
                print(json.dumps({"status": "product_reference", "product": product, "used": product_ref is not None}))

                from ..vector.structures import structures_for

                def reference_for(part):
                    """The real product's picture, else (2026-10-28) code-drawn sketches of the money
                    and business objects the drawing names, so they come out properly built."""
                    if product_ref and product.lower() in str(part.drawing).lower():
                        return product_ref
                    return structures_for(str(part.drawing), work / "structures") or None

                ordered: list[Path] = []
                refused: set[Path] = set()
                for scene in scenes:
                    for part in scene_parts(scene):
                        target = illustration_dir / f"{part.picture_id}.png"
                        ordered.append(target)
                        if target.exists():
                            continue  # already paid for and checkpointed
                        if try_figure(part, target, str(spec["format"])):
                            continue  # math and physics layer: drawn in code, at no cost
                        prompt = illustration_prompt(part.drawing, part.gold, str(spec["format"]), part.layout,
                                                     part.label)
                        for attempt in (prompt, calm_prompt(prompt, part)):
                            self._reserve(spec, support_image_cost_model, Usage(images=1), stage="illustrations")
                            try:
                                ref = reference_for(part)
                                output = line_art.create(attempt, target, picture_size(str(spec["format"]), part),
                                                         **({"reference": ref} if ref else {}))
                            except Exception as exc:
                                if not is_moderation_block(exc):
                                    raise
                                print(f"::warning title=Picture refused by the safety filter::{part.picture_id}")
                                continue
                            self._record_image(production_id, "illustrations", support_image_cost_model, output)
                            self._redraw_if_unclear(spec, part, attempt, target, line_art, support_image_cost_model,
                                                    production_id, reference_for(part))
                            break
                        else:
                            refused.add(target)
                if refused:
                    fill_from_neighbours(ordered, refused)

            self.runner.run(production_id, "illustrations-v1", illustrations_stage)
            illustrations = {part.picture_id: illustration_dir / f"{part.picture_id}.png"
                             for scene in scenes for part in scene_parts(scene)}
            plan = plan | {"scenes": scenes, "cover": visual_plan.get("cover") or {}}
            timed_lines = align_lines(plan, timed_words, narration_seconds)
            from ..vector.chapters import chapter_marks
            (work / "chapters.json").write_text(json.dumps(
                [{"start": m.start, "number": m.number, "title": m.title}
                 for m in chapter_marks(plan, timed_lines)], indent=2) + "\n", encoding="utf-8")
            storyboard = {
                "renderer": "vector",
                "scenes": [
                    {"id": f"line-{line.index:03d}", "start": line.start, "end": line.end,
                     "duration": line.end - line.start, "visual": line.visual,
                     "visual_caption": line.label}
                    for line in timed_lines
                ],
            }
            storyboard_path = work / "storyboard-vector.json"
            storyboard_path.write_text(json.dumps(storyboard, indent=2) + "\n", encoding="utf-8")
            labels_srt = self.root / "build" / production_id / "visual-labels.srt"
            labels_srt.parent.mkdir(parents=True, exist_ok=True)
            labels_srt.write_text(words_to_srt([
                {"word": line.label or line.visual.replace("_", " ").upper(),
                 "start": line.start, "end": line.end}
                for line in timed_lines
            ]), encoding="utf-8")

            def vector_render_stage():
                # Rotate the four atmosphere beds in order across videos.
                rendered_before = self.database.rows(
                    "SELECT COUNT(DISTINCT production_id) n FROM stage_runs WHERE stage='render-vector-v1' "
                    "AND status='completed' AND production_id<>?", (production_id,),
                )
                VectorRenderer(str(spec["format"])).render(
                    plan, timed_words, narration, video_path, narration_seconds,
                    music=None, illustrations=illustrations,
                    bed_variant=int(rendered_before[0]["n"]) if rendered_before else None,
                )

            self.runner.run(production_id, "render-vector-v1", vector_render_stage, attempts=1)
            rendered_seconds = self._duration(video_path)
            if abs(rendered_seconds - narration_seconds) > max(0.75, narration_seconds * 0.01):
                raise RuntimeError(
                    f"render duration {rendered_seconds:.2f}s does not match narration "
                    f"{narration_seconds:.2f}s"
                )
        else:
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
                "Create accurate, search-optimised YouTube metadata for GOLIDE. No hashtags in the title. "
                "description: two or three short paragraphs that describe the actual video in plain, human words "
                "(no hashtags, no keyword list, no timestamps, no links, no source citations; those are added separately or not at all). "
                "keywords: 12 to 15 search phrases people are typing right now about this topic (use web search for "
                "what is trending), most specific first, each 1 to 4 words. "
                "hashtags: 5 to 8 relevant hashtags without spaces. "
                "tags: 25 to 30 unique YouTube tags (exact topic, named companies, products and people, common "
                "synonyms and searches, GOLIDE), each under 30 characters. "
                "Do not write any timestamps or a chapter list; real chapters are added from the recording. "
                "Return chapters as an empty list.",
                f"FORMAT={spec['format']}\nSCRIPT\n{script}", METADATA_SCHEMA,
                web_search=True,
            )
            metadata = apply_locked_upload_defaults(
                output.value | {"format": spec["format"]}, policy
            )
            if spec.get("model_title"):
                # 2026-10-21: the title rides the breakout it was modelled on.
                metadata["title"] = str(spec["model_title"])[:100]
            # 2026-10-13 SEO layout: summary, keywords, (chapters), hashtags; 20+ tags.
            from ..youtube_metadata import compose_description, fit_tags, seo_body
            metadata["seo_body"] = seo_body(str(metadata["description"]))
            metadata["description"] = compose_description(
                metadata["seo_body"], metadata.get("keywords") or [], metadata.get("hashtags") or [])
            metadata["tags"] = fit_tags(metadata.get("tags") or [], metadata.get("keywords") or [])
            chapters_path = work / "chapters.json"
            if spec["format"] == "long" and chapters_path.exists():
                # Real chapter times from the recording replace anything guessed.
                from ..vector.chapters import ChapterMark, with_chapters, youtube_chapters
                marks = [ChapterMark(float(m["start"]), str(m["number"]), str(m["title"]))
                         for m in json.loads(chapters_path.read_text(encoding="utf-8"))]
                metadata["chapters"] = youtube_chapters(marks, narration_seconds)
                metadata["description"] = with_chapters(str(metadata["description"]), metadata["chapters"])
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
            if raw_thumbnail.exists() and not thumbnail.exists():
                # Paid for but not normalised (a crash between the two steps): finish it.
                normalize_thumbnail(raw_thumbnail, thumbnail)
                self._stamp_thumbnail(work, thumbnail)
                return
            self._require_absent(raw_thumbnail, "thumbnail")
            self._require_absent(thumbnail, "thumbnail")
            if str(spec["format"]) == "short":
                # 2026-10-27 owner: "the video first block itself is enough" for a short.
                # No paid image: the short's own opening card becomes its thumbnail.
                cover = video_path.with_name(video_path.stem + "-cover.jpg")
                if cover.exists():
                    from PIL import Image
                    card = Image.open(cover).convert("RGB")
                    card.thumbnail((1280, 720))
                    canvas = Image.new("RGB", (1280, 720), (11, 11, 14))
                    canvas.paste(card, ((1280 - card.width) // 2, (720 - card.height) // 2))
                    thumbnail.parent.mkdir(parents=True, exist_ok=True)
                    canvas.save(thumbnail)
                    print(json.dumps({"status": "short_thumbnail_from_cover"}))
                    return
            self._reserve(
                spec, thumbnail_cost_model, Usage(images=1), stage="thumbnail"
            )
            from ..providers.openai_media import SAFE_RETRY, is_moderation_block

            from ..vector.thumbnail_style import thumbnail_colors, thumbnail_prompt
            from ..vector.thumbnail_v2 import fetch_reference, thumbnail_prompt_v2
            try:
                plan_json = json.loads((work / "visual-plan.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                plan_json = {}
            colors = thumbnail_colors(plan_json.get("cover") or {}, plan_json.get("scenes") or [])
            # 2026-10-18: the static-post look, glowing in two or three meaning colours.
            # 2026-10-25: the modelled video's thumbnail shows the real product; the image
            # model draws THAT product in our style instead of guessing a brand-new one.
            source_url = str((spec.get("source_breakout") or {}).get("url") or "")
            reference = fetch_reference(source_url, work / "thumbnail-reference.jpg")
            prompt = thumbnail_prompt_v2(metadata["title"], self._thumbnail_moment(work), colors, reference is not None)
            print(json.dumps({"status": "thumbnail_reference", "used": reference is not None, "source": source_url}))
            output = None
            for attempt, refs in ((prompt, [reference] if reference else None),
                                  (thumbnail_prompt(metadata["title"], "one simple glowing symbol of the topic", colors)
                                   + SAFE_RETRY, None)):
                try:
                    output = thumbnail_provider.create_thumbnail(attempt, raw_thumbnail,
                                                                 self.providers.config["thumbnail"]["size"], refs)
                    break
                except Exception as exc:
                    if not is_moderation_block(exc):
                        raise
                    print("::warning title=Thumbnail refused by the safety filter::retrying with a calmer prompt")
            if output is None:
                # Both refused: the video's own designed cover becomes the thumbnail.
                cover = video_path.with_name(video_path.stem + "-cover.jpg")
                if not cover.exists():
                    raise RuntimeError("thumbnail refused by the safety filter and no cover to fall back on")
                normalize_thumbnail(cover, thumbnail)
                print("::warning title=Thumbnail from cover::the image model refused the thumbnail twice")
                return
            normalize_thumbnail(raw_thumbnail, thumbnail)
            self._stamp_thumbnail(work, thumbnail)
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
            # "Add to dictionary": a word the dictionary does not know is accepted
            # (and remembered) when the speech-to-text of the owner's recording
            # spelled it the same way, or the research sources contain it.
            from ..quality.spelling import accept_with_evidence, load_dictionary, unknown_words
            policy = json.loads((self.root / "config/qa-policy.json").read_text(encoding="utf-8"))
            cover_text = str(((json.loads((work / "visual-plan.json").read_text(encoding="utf-8"))
                               if (work / "visual-plan.json").exists() else {}).get("cover") or {}).get("text", ""))
            texts = [script, metadata["title"], metadata["description"], cover_text]
            flagged = unknown_words(texts, policy, load_dictionary(self.root))
            if flagged:
                heard = " ".join(str(w.get("word", "")) for w in timed_words)
                evidence = {"your recording": heard, "the research sources": json.dumps(research)}
                approved = self.root / "production-queue" / f"{production_id}.script-plan.json"
                if approved.exists():
                    # A script the owner approved word for word is his spelling.
                    evidence["the owner-approved script"] = approved.read_text(encoding="utf-8")
                accepted = accept_with_evidence(self.root, flagged, evidence)
                if accepted:
                    print(json.dumps({"status": "dictionary_added", "words": accepted}))
            result = QualityRunner(self.root / "config/qa-policy.json").run(video_path, spec["format"], storyboard, [script, metadata["title"], metadata["description"]], qa_path, thumbnail, editorial=not vector_mode)
            if not result.passed:
                raise RuntimeError("automatic QA failed: " + "; ".join(result.failures))
            if result.warnings:
                print("::warning title=Spelling to look at::" + "; ".join(result.warnings))
            return result
        qa_result = self.runner.run(production_id, "qa", qa_stage, attempts=1)
        qa = qa_result or QualityRunner(self.root / "config/qa-policy.json").run(video_path, spec["format"], storyboard, [script, metadata["title"], metadata["description"]], None, thumbnail, editorial=not vector_mode)
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
