from __future__ import annotations


def validate_storyboard(scenes: list[dict], format: str) -> list[str]:
    problems: list[str] = []
    if not scenes:
        return ["storyboard requires scenes"]
    total = sum(float(scene.get("duration", 0)) for scene in scenes)
    maximum = 90 if format == "short" else 300
    if total <= 0 or total > maximum:
        problems.append(f"storyboard duration must be within 1-{maximum} seconds")
    opening_limit = 2.5 if format == "short" else 6.0
    if float(scenes[0].get("duration", 0)) > opening_limit:
        problems.append(f"opening visual must change within {opening_limit:g} seconds")
    longest = 4.0 if format == "short" else 8.0
    if any(float(scene.get("duration", 0)) > longest for scene in scenes):
        problems.append(f"no scene may remain visually static longer than {longest:g} seconds")
    if any(not scene.get("purpose") or not scene.get("asset_query") for scene in scenes):
        problems.append("every scene needs a narrative purpose and asset query")
    return problems
