from __future__ import annotations


def validate_thumbnail(brief: dict) -> list[str]:
    problems = []
    text = str(brief.get("text", "")).strip()
    if text:
        problems.append("thumbnail must not contain words or typography")
    if not brief.get("focal_subject"):
        problems.append("one focal subject is required")
    if not brief.get("topic_object_or_consequence"):
        problems.append("one topic-specific object or consequence is required")
    if brief.get("duplicates_title", False):
        problems.append("thumbnail must complement, not repeat, the title")
    return problems
