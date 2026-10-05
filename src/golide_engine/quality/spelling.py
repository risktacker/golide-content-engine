from __future__ import annotations

import re


_APOSTROPHE_TRANSLATION = str.maketrans({
    "\u2018": "'",
    "\u2019": "'",
    "\u02bc": "'",
})


def _spellcheck_words(text: str) -> set[str]:
    """Return plain words that are meaningful to send to the dictionary checker.

    Hashtags commonly join multiple valid words, contractions are valid English even
    when the spellchecker splits them internally, and hyphenated scientific compounds
    are better validated by the content/research gates than by a general dictionary.
    Smart/typographic apostrophes are normalized before tokenization so contractions
    such as ``isn\u2019t`` and ``doesn\u2019t`` are treated exactly like their ASCII forms.
    """
    cleaned = text.translate(_APOSTROPHE_TRANSLATION)
    cleaned = re.sub(r"#[A-Za-z0-9_]+", " ", cleaned)
    cleaned = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", cleaned)
    tokens = re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)*", cleaned)
    # Capitalised tokens (NVIDIA, Kubernetes, Lusaka) are names, not
    # misspellings; trending tech topics are full of them.
    return {
        token.lower()
        for token in tokens
        if len(token) > 2 and "'" not in token and "-" not in token
        and not token[0].isupper()
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
