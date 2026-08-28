from __future__ import annotations


def validate_script(script: dict, format: str) -> list[str]:
    problems: list[str] = []
    words = str(script.get("narration", "")).split()
    target = (105, 175) if format == "short" else (525, 825)
    if not target[0] <= len(words) <= target[1]:
        problems.append(f"narration must contain {target[0]}-{target[1]} words")
    hook = str(script.get("hook", "")).split()
    if not hook or len(hook) > (18 if format == "short" else 28):
        problems.append("hook is missing or too long")
    beats = script.get("beats", [])
    minimum = 5 if format == "short" else 7
    if len(beats) < minimum:
        problems.append(f"at least {minimum} narrative beats are required")
    if not any(str(beat.get("type", "")) == "payoff" for beat in beats):
        problems.append("script requires an explicit payoff beat")
    return problems

