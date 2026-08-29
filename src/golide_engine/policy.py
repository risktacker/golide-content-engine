from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PolicyError(ValueError):
    pass


def load_policy(path: str | Path) -> dict[str, Any]:
    policy = json.loads(Path(path).read_text(encoding="utf-8"))
    short = policy.get("shorts", {})
    voice = policy.get("voice", {})
    captions = policy.get("captions", {})
    music = policy.get("music", {})
    loop = policy.get("loop", {})
    visuals = policy.get("visuals", {})
    thumbnail = policy.get("thumbnail", {})

    if short.get("weekly_count") != 3:
        raise PolicyError("shorts.weekly_count must remain 3")
    if not loop.get("required") or not loop.get("closing_reconnects_to_opening"):
        raise PolicyError("shorts must use a circular opening/closing loop")
    if voice.get("age_character") != "mature-adult":
        raise PolicyError("voice must use a mature-adult character")
    if voice.get("energy") not in {"high", "very_high"}:
        raise PolicyError("voice energy must be high")
    pace = voice.get("pace_wpm_range", [])
    if len(pace) != 2 or pace[0] < 165 or pace[1] > 200 or pace[0] >= pace[1]:
        raise PolicyError("voice pace range must be a valid high-retention range")
    if not captions.get("visual_labels") or not captions.get("spoken_captions"):
        raise PolicyError("both visual labels and spoken captions are required")
    if not music.get("required") or not music.get("license_record_required"):
        raise PolicyError("licensed background music is required")
    composition = visuals.get("composition", {})
    if composition.get("default") != "center-stage-with-negative-space":
        raise PolicyError("explainer visuals must default to centered staging")
    if composition.get("edge_to_edge_default") is not False:
        raise PolicyError("edge-to-edge framing cannot be the default")
    if not visuals.get("avatar", {}).get("face_consistency_required"):
        raise PolicyError("avatar face consistency must be enforced")
    if thumbnail.get("text_policy") != "none":
        raise PolicyError("thumbnail text must remain disabled")
    if thumbnail.get("output_dimensions") != [1280, 720]:
        raise PolicyError("thumbnail output must remain 1280x720")
    if thumbnail.get("banner_safe_area_rules_apply") is not False:
        raise PolicyError("banner safe-area rules cannot be applied to thumbnails")
    return policy
