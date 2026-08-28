from __future__ import annotations


def validate_voice_brief(brief: dict, format: str) -> list[str]:
    problems = []
    if not brief.get("provider") or not brief.get("voice_id"):
        problems.append("voice provider and voice_id are required")
    pace = float(brief.get("words_per_minute", 0))
    lower, upper = ((150, 185) if format == "short" else (135, 165))
    if not lower <= pace <= upper:
        problems.append(f"voice pace must be {lower}-{upper} words per minute")
    if float(brief.get("estimated_cost_usd", 0)) < 0:
        problems.append("voice cost cannot be negative")
    return problems

