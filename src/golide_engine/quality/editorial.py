from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def check_editorial(storyboard: dict[str, Any], format_name: str, policy: dict[str, Any]) -> tuple[list[str], dict[str, float | int]]:
    rules = policy["editorial"]
    scenes = storyboard.get("scenes", [])
    failures: list[str] = []
    if not scenes:
        return ["storyboard has no editorial beats"], {"beats": 0}

    cursor = 0.0
    motions: list[str] = []
    transitions: list[str] = []
    audio_cues: list[str] = []
    primary_assets: list[str] = []
    asset_runtime: dict[str, float] = defaultdict(float)
    visible_annotations = 0
    layered_scenes = 0
    strong_motion = 0
    longest_beat = 0.0
    last_impact = -100.0

    for scene in scenes:
        scene_id = scene.get("id", "unknown")
        start = float(scene.get("start", cursor))
        end = float(scene.get("end", start + float(scene.get("duration", 0))))
        duration = float(scene.get("duration", 0))
        longest_beat = max(longest_beat, duration)
        if duration <= 0 or abs((end - start) - duration) > 0.08:
            failures.append(f"scene {scene_id} timing does not match duration")
        if abs(start - cursor) > float(rules["timeline_gap_tolerance_seconds"]):
            failures.append(f"scene {scene_id} is not contiguous with narration timing")
        cursor = end

        asset_key = str(scene.get("asset_key") or scene.get("media") or "").strip()
        if not asset_key:
            failures.append(f"scene {scene_id} has no primary visual asset")
        primary_assets.append(asset_key)
        asset_runtime[asset_key] += max(0.0, duration)
        if scene.get("secondary_assets") or scene.get("layers"):
            layered_scenes += 1

        motion = scene.get("motion") or {}
        motion_type = str(motion.get("type", ""))
        transition = str(motion.get("transition", ""))
        intensity = str(motion.get("intensity", ""))
        audio_cue = str(motion.get("audio_cue", "none"))
        motions.append(motion_type)
        transitions.append(transition)
        audio_cues.append(audio_cue)
        strong_motion += intensity == "strong"

        annotation = scene.get("annotation") or motion.get("annotation") or {}
        if annotation.get("kind", "none") != "none":
            visible_annotations += 1
            ann_start = float(annotation.get("start_offset", 0))
            ann_duration = float(annotation.get("duration", 0))
            if ann_start < 0 or ann_duration <= 0 or ann_start + ann_duration > duration + 0.05:
                failures.append(f"scene {scene_id} annotation is outside its narration beat")
            if len(str(scene.get("visual_caption", ""))) > int(rules["max_visual_caption_characters_with_annotation"]):
                failures.append(f"scene {scene_id} has competing annotation and visual-caption density")

        if audio_cue == "impact":
            if start - last_impact < float(rules["minimum_impact_spacing_seconds"]):
                failures.append(f"scene {scene_id} repeats a high-salience impact too soon")
            last_impact = start

    max_beat = float(rules[f"{format_name}_max_visual_beat_seconds"])
    if longest_beat > max_beat:
        failures.append(f"editorial beat {longest_beat:.2f}s exceeds {format_name} maximum {max_beat:.2f}s")

    max_same_motion = int(rules["max_consecutive_same_motion"])
    streak = 1
    for previous, current in zip(motions, motions[1:]):
        streak = streak + 1 if current == previous else 1
        if streak > max_same_motion:
            failures.append(f"motion recipe {current!r} repeats more than {max_same_motion} times")
            break

    max_same_asset = int(rules["max_consecutive_same_primary_asset"])
    streak = 1
    for previous, current in zip(primary_assets, primary_assets[1:]):
        streak = streak + 1 if current == previous else 1
        if current and streak > max_same_asset:
            failures.append(
                f"primary visual {current!r} repeats more than {max_same_asset} consecutive beats"
            )
            break

    unique_primary_assets = len({item for item in primary_assets if item})
    minimum_unique = int(rules[f"minimum_unique_primary_assets_{format_name}"])
    if unique_primary_assets < minimum_unique:
        failures.append(
            f"visual diversity too low: {unique_primary_assets} unique primary assets; minimum is {minimum_unique}"
        )

    if cursor > 0 and asset_runtime:
        dominant_asset, dominant_seconds = max(asset_runtime.items(), key=lambda item: item[1])
        dominant_ratio = dominant_seconds / cursor
        if dominant_ratio > float(rules["maximum_primary_asset_runtime_ratio"]):
            failures.append(
                f"primary visual {dominant_asset!r} dominates {dominant_ratio:.1%} of runtime"
            )
    else:
        dominant_ratio = 0.0

    layered_ratio = layered_scenes / len(scenes)
    minimum_layered = float(rules[f"minimum_layered_scene_ratio_{format_name}"])
    if layered_ratio < minimum_layered:
        failures.append(
            f"layered composition ratio {layered_ratio:.1%} is below {minimum_layered:.1%}"
        )

    non_cut_ratio = sum(item != "cut" for item in transitions) / len(transitions)
    if non_cut_ratio > float(rules["maximum_non_cut_transition_ratio"]):
        failures.append("transition density is too high; intentional hard cuts are required")

    strong_ratio = strong_motion / len(scenes)
    if strong_ratio > float(rules["maximum_strong_motion_ratio"]):
        failures.append("strong motion is overused and destroys editorial hierarchy")

    cue_ratio = sum(item != "none" for item in audio_cues) / len(audio_cues)
    if cue_ratio > float(rules["maximum_sfx_beat_ratio"]):
        failures.append("sound effects are assigned to too many narration beats")
    minimum_sfx_ratio = float(rules[f"minimum_sfx_beat_ratio_{format_name}"])
    if cue_ratio < minimum_sfx_ratio:
        failures.append(
            f"sound design density {cue_ratio:.1%} is below {minimum_sfx_ratio:.1%}"
        )

    unique_motion = len({item for item in motions if item})
    if len(scenes) >= 4 and unique_motion < int(rules["minimum_motion_recipes"]):
        failures.append("motion grammar lacks variation")

    metrics: dict[str, float | int] = {
        "beats": len(scenes),
        "duration_seconds": round(cursor, 3),
        "longest_beat_seconds": round(longest_beat, 3),
        "unique_primary_assets": unique_primary_assets,
        "dominant_primary_asset_runtime_ratio": round(dominant_ratio, 3),
        "layered_scene_ratio": round(layered_ratio, 3),
        "unique_motion_recipes": unique_motion,
        "non_cut_transition_ratio": round(non_cut_ratio, 3),
        "strong_motion_ratio": round(strong_ratio, 3),
        "sfx_beat_ratio": round(cue_ratio, 3),
        "visible_annotations": visible_annotations,
        "most_used_motion_count": max(Counter(motions).values()),
    }
    return failures, metrics
