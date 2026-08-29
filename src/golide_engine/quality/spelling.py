from __future__ import annotations

import re


def check_spelling(texts: list[str], policy: dict) -> list[str]:
    try:
        from spellchecker import SpellChecker
    except ImportError as exc:
        raise RuntimeError("pyspellchecker is required for production QA") from exc
    ignore = {value.lower() for value in policy["spelling"].get("ignore", [])}
    words = {word.lower() for text in texts for word in re.findall(r"[A-Za-z']+", text) if len(word) > 2}
    unknown = sorted(SpellChecker().unknown(words) - ignore)
    return [f"possible misspelling: {word}" for word in unknown]
