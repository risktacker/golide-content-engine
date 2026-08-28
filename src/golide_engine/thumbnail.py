from __future__ import annotations


def validate_thumbnail(brief: dict) -> list[str]:
    problems = []
    text = str(brief.get("text", "")).strip()
    if len(text.split()) > 4:
        problems.append("thumbnail text must contain at most four words")
    if not brief.get("focal_subject"):
        problems.append("one focal subject is required")
    if not brief.get("visual_question"):
        problems.append("thumbnail must create a visual question")
    if brief.get("duplicates_title", False):
        problems.append("thumbnail must complement, not repeat, the title")
    return problems

