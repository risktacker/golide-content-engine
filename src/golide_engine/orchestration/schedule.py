from __future__ import annotations

import json
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _clock(value: str) -> time:
    hour, minute = (int(part) for part in value.split(":", 1))
    return time(hour, minute)


def _scores(format: str) -> dict[str, int]:
    if format == "short":
        return {
            "scroll_stop": 9,
            "visual_payoff": 9,
            "curiosity_gap": 9,
            "retention_design": 9,
            "broad_relevance": 8,
            "evidence_strength": 8,
            "novelty": 8,
            "replay_or_loop": 8,
            "revenue_fit": 6,
        }
    return {
        "click_promise": 9,
        "thumbnail_title_fit": 9,
        "narrative_engine": 9,
        "visual_depth": 9,
        "evidence_strength": 8,
        "retention_design": 9,
        "broad_relevance": 8,
        "novelty": 8,
        "revenue_fit": 7,
    }


def build_spec(rule: dict[str, Any], day, timezone_name: str, channel_id: str) -> dict[str, Any]:
    zone = ZoneInfo(timezone_name)
    generate_at = datetime.combine(day, _clock(rule["generate_time"]), zone)
    publish_at = datetime.combine(day, _clock(rule["publish_time"]), zone)
    format = rule["format"]
    production_id = f"golide-{format}-{day.isoformat()}"
    return {
        "id": production_id,
        "studio_managed": True,
        "format": format,
        "title": f"GOLIDE {format.title()} · {day.isoformat()}",
        "brief": (
            "Choose an original evidence-backed GOLIDE technology, software or business topic "
            "with strong current niche demand and a timely angle. Prioritize useful changes, tools, "
            "workflows, industry shifts or surprising real mechanisms. Keep Shorts and long-form "
            "product-independent; never turn scheduled video into a GOLIDE product advertisement "
            "and never copy an existing video."
        ),
        "demand_query": "current technology software business trends",
        "demand_validation_required": True,
        "budget_class": "scheduled",
        "purpose": "channel-automation",
        "generate_at": _iso_utc(generate_at),
        "max_cost_usd": 6.0,
        "production_authorized": True,
        "output_destination": "render-and-upload",
        "owner_voice_required": True,
        "concept": {
            "family": "technology-software-business",
            "promise": "A high-interest current niche topic explained with authoritative evidence and a useful GOLIDE angle",
            "scores": _scores(format),
        },
        "generation_parameters": {
            "brand_preset": "golide-editorial",
            "voice": "owner-recording-only",
            "pacing": "fast",
            "visual_density": 4,
            "motion_intensity": 4,
            "annotation_density": 3,
            "avatar_frequency": 2,
            "sound_design": 3,
            "image_change_bias": 4,
            "editorial_manifest": "beat-motion-audio-v1",
            "platform_demand_gate": "youtube-wide-proxy-v1",
            "schedule_rule": rule["id"],
        },
        "music": {"mood": "curious-tension"},
        "avatar_reference_images": [],
        "release": {
            "approved": True,
            "channel_id": channel_id,
            "scheduled_at": _iso_utc(publish_at),
        },
    }


def materialize_due(
    queue_directory: str | Path,
    config_path: str | Path,
    now: datetime | None = None,
) -> list[Path]:
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    zone = ZoneInfo(config["timezone"])
    now = now or datetime.now(timezone.utc)
    local_now = now.astimezone(zone)
    queue = Path(queue_directory)
    queue.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    weekday = local_now.strftime("%A").lower()
    for rule in config["rules"]:
        if local_now.date().isoformat() < rule["start_date"]:
            continue
        if weekday not in rule["weekdays"]:
            continue
        spec = build_spec(rule, local_now.date(), config["timezone"], config["channel_id"])
        generate_at = datetime.fromisoformat(spec["generate_at"].replace("Z", "+00:00"))
        publish_at = datetime.fromisoformat(spec["release"]["scheduled_at"].replace("Z", "+00:00"))
        if now < generate_at or now >= publish_at:
            continue
        if list(queue.glob(f"{spec['id']}*.json")):
            continue
        path = queue / f"{spec['id']}.json"
        path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        created.append(path)
    return created
