from __future__ import annotations

import re


def _spellcheck_words(text: str) -> set[str]:
    """Return plain words that are meaningful to send to the dictionary checker.

    Hashtags commonly join multiple valid words, contractions are valid English even
    when the spellchecker splits them internally, and hyphenated scientific compounds
    are better validated by the content/research gates than by a general dictionary.
    """
    cleaned = re.sub(r"#[A-Za-z0-9_]+", " ", text)
    cleaned = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", cleaned)
    tokens = re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)*", cleaned)
    return {
        token.lower()
        for token in tokens
        if len(token) > 2 and "'" not in token and "-" not in token
    }


def check_spelling(texts: list[str], policy: dict) -> list[str]:
    try:
        from spellchecker import SpellChecker
    except ImportError as exc:
        raise RuntimeError("pyspellchecker is required for production QA") from exc
    ignore = {value.lower() for value in policy["spelling"].get("ignore", [])}
    words = {word for text in texts for word in _spellcheck_words(text)}
    unknown = sorted(SpellChecker().unknown(words) - ignore)
    return [f"possible misspelling: {word}" for word in unknown]
