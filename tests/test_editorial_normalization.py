from golide_engine.orchestration.production import ProductionService


def _scene(index: int) -> dict:
    return {
        "id": f"beat-{index:03d}",
        "start": index * 1.0,
        "end": (index + 1) * 1.0,
        "duration": 1.0,
        "motion": {
            "type": "push-in",
            "transition": "dissolve",
            "intensity": "strong",
            "audio_cue": "impact",
            "annotation": {
                "kind": "arrow",
                "start_offset": 0.9,
                "duration": 1.0,
            },
        },
    }


def test_editorial_intent_is_normalized_to_qa_density_limits():
    policy = {
        "editorial": {
            "maximum_non_cut_transition_ratio": 0.65,
            "maximum_sfx_beat_ratio": 0.6,
            "maximum_strong_motion_ratio": 0.45,
            "minimum_impact_spacing_seconds": 2.5,
        }
    }
    source = {"scenes": [_scene(index) for index in range(10)]}

    normalized = ProductionService._normalize_editorial_intent(source, policy)
    scenes = normalized["scenes"]

    assert sum(scene["motion"]["transition"] != "cut" for scene in scenes) <= 6
    assert sum(scene["motion"]["audio_cue"] != "none" for scene in scenes) <= 6
    assert sum(scene["motion"]["intensity"] == "strong" for scene in scenes) <= 4
    assert all(
        scene["motion"]["annotation"]["start_offset"]
        + scene["motion"]["annotation"]["duration"]
        <= scene["duration"]
        for scene in scenes
    )
    assert source["scenes"][0]["motion"]["transition"] == "dissolve"


def test_too_short_beat_drops_annotation_safely():
    assert ProductionService._fit_annotation(
        {"kind": "arrow", "start_offset": 0, "duration": 1}, 0.01
    ) == {"kind": "none"}


def test_failed_planner_recovery_is_local_diverse_and_qa_shaped():
    beats = [
        {
            "id": f"beat-{index:03d}",
            "start": index * 2.0,
            "end": (index + 1) * 2.0,
            "duration": 2.0,
            "text": f"Narration beat {index} explains a different part of the mechanism",
        }
        for index in range(48)
    ]

    scenes = ProductionService._build_recovery_storyboard(beats, primary_limit=12)

    assert len(scenes) == len(beats)
    assert {scene["beat_id"] for scene in scenes} == {beat["id"] for beat in beats}
    assert len({scene["asset_key"] for scene in scenes}) == 12
    assert sum(bool(scene["secondary_assets"]) for scene in scenes) / len(scenes) >= 0.25
    assert len({scene["motion"]["type"] for scene in scenes}) >= 4
    assert sum(scene["motion"]["audio_cue"] != "none" for scene in scenes) / len(scenes) >= 0.10

    keys = [scene["asset_key"] for scene in scenes]
    assert all(not (a == b == c) for a, b, c in zip(keys, keys[1:], keys[2:]))
