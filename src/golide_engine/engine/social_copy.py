"""Clean model-written social copy before it is published.

Web-search answers carry citations as markdown, e.g.
"([apnews.com](https://apnews.com/...?utm_source=openai))". Those read as
noise on every network (Instagram does not even make them links), so they are
removed: the copy already names its source in words.

X allows 280 characters, with every link counted as 23. A post over that is
refused by X ("You are not permitted to perform this action"), so X copy is
fitted at a sentence boundary before it is sent.
"""

from __future__ import annotations

import re

X_LIMIT = 280
X_URL_WEIGHT = 23

_MD_CITATION = re.compile(r"\s*\(\s*\[[^\]]*\]\(\s*https?://[^)\s]+\s*\)\s*\)")
_MD_LINK = re.compile(r"\[([^\]]*)\]\(\s*(https?://[^)\s]+)\s*\)")
_TRACKING = re.compile(r"([?&])utm_[a-z]+=[^&\s)]*&?")
_URL = re.compile(r"https?://\S+")


def strip_citations(text: str) -> str:
    text = _MD_CITATION.sub("", text)
    text = _MD_LINK.sub(lambda m: m.group(1) or m.group(2), text)
    text = _TRACKING.sub(lambda m: m.group(1), text).replace("?&", "?")
    text = re.sub(r"\?(\s|$)", r"\1", text)
    text = re.sub(r"[ \t]+([.,;:!?])", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return "\n".join(row.rstrip() for row in text.splitlines()).strip()


def x_length(text: str) -> int:
    return len(_URL.sub("x" * X_URL_WEIGHT, text))


def fit_x(text: str, limit: int = X_LIMIT) -> str:
    """Keep whole sentences (and a trailing link, if any) within X's limit."""
    text = text.strip()
    if x_length(text) <= limit:
        return text
    links = _URL.findall(text)
    link = links[-1] if links else ""
    body = _URL.sub("", text).strip()
    sentences = re.findall(r"[^.!?\n]+[.!?]?\s*", body)
    kept = ""
    budget = limit - (X_URL_WEIGHT + 2 if link else 0)
    for sentence in sentences:
        if x_length(kept + sentence) > budget:
            break
        kept += sentence
    kept = kept.strip()
    if not kept:  # a single very long sentence: cut on a word boundary
        kept = body[: budget - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return kept + ("\n\n" + link if link else "")
