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
