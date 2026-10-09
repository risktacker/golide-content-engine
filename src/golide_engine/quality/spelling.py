from __future__ import annotations

import re
from pathlib import Path


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


DICTIONARY = "data/dictionary.txt"  # the GOLIDE dictionary: "add to dictionary", kept for good


def load_dictionary(root: str | Path | None = None) -> set[str]:
    path = Path(root or ".") / DICTIONARY
    if not path.exists():
        return set()
    return {line.split("#", 1)[0].strip().lower() for line in path.read_text(encoding="utf-8").splitlines()
            if line.split("#", 1)[0].strip()}


def add_to_dictionary(root: str | Path, word: str, reason: str) -> None:
    path = Path(root) / DICTIONARY
    path.parent.mkdir(parents=True, exist_ok=True)
    known = load_dictionary(root)
    if word.lower() in known:
        return
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{word.lower()}  # {reason}\n")


def unknown_words(texts: list[str], policy: dict, known: set[str] | None = None) -> list[str]:
    try:
        from spellchecker import SpellChecker
    except ImportError as exc:
        raise RuntimeError("pyspellchecker is required for production QA") from exc
    ignore = {value.lower() for value in policy["spelling"].get("ignore", [])} | set(known or ())
    words = {word for text in texts for word in _spellcheck_words(text)}
    checker = SpellChecker()
    unknown = checker.unknown(words) - ignore
    # British spellings are correct (2026-10-09: "maths" stopped a finished short).
    return sorted(word for word in unknown if not checker.known(_american_forms(word)))


_BRITISH_WORDS = {"maths": "math", "programme": "program", "programmes": "programs", "cheque": "check",
                  "tyre": "tire", "tyres": "tires", "kerb": "curb", "aluminium": "aluminum", "grey": "gray",
                  "storey": "story", "plough": "plow", "mum": "mom", "learnt": "learned", "spelt": "spelled"}


def _american_forms(word: str) -> list[str]:
    """American spellings a British word may correspond to."""
    import re
    w = word.lower()
    forms = [_BRITISH_WORDS[w]] if w in _BRITISH_WORDS else []
    rules = (
        (r"our(s|ed|ing|ful|ite|ites|able)?$", r"or\1"),          # colour, favourite, honourable
        (r"is(e|es|ed|ing|ation|ations|er|ers)$", r"iz\1"),       # organise, organisation
        (r"ys(e|es|ed|ing)$", r"yz\1"),                            # analyse
        (r"tre(s)?$", r"ter\1"),                                   # centre, metre
        (r"ogue(s)?$", r"og\1"),                                   # catalogue, dialogue
        (r"ence(s)?$", r"ense\1"),                                 # defence, licence
        (r"ll(ed|ing|er|ers)$", r"l\1"),                           # travelled, labelling
        (r"ae", "e"), (r"oe", "e"),                                  # paediatric, manoeuvre
    )
    for pattern, repl in rules:
        alt = re.sub(pattern, repl, w)
        if alt != w:
            forms.append(alt)
    return forms


def accept_with_evidence(root: str | Path, flagged: list[str], evidence: dict[str, str]) -> dict[str, str]:
    """Add flagged words that independent evidence shows are real; return word -> reason.

    Evidence is free text keyed by where it came from: the speech-to-text of the
    owner's recording (a separate system that independently heard and spelled
    the word) and the research sources the script was written from.
    """
    accepted: dict[str, str] = {}
    tokens = {name: set(re.findall(r"[a-z]+", text.lower())) for name, text in evidence.items()}
    for word in flagged:
        found = [name for name, seen in tokens.items() if word in seen]
        if found:
            reason = "seen in " + " and ".join(found)
            add_to_dictionary(root, word, reason)
            accepted[word] = reason
    return accepted


def check_spelling(texts: list[str], policy: dict, known: set[str] | None = None) -> list[str]:
    return [f"possible misspelling: {word}" for word in unknown_words(texts, policy, known)]
