from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class Source:
    url: str
    title: str
    publisher: str
    published: str | None = None
    primary: bool = False

    def validate(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"invalid source URL: {self.url}")
        if not self.title.strip() or not self.publisher.strip():
            raise ValueError("source title and publisher are required")


@dataclass(frozen=True)
class Claim:
    text: str
    source_urls: tuple[str, ...]
    visualizable: bool


def validate_evidence(sources: tuple[Source, ...], claims: tuple[Claim, ...]) -> list[str]:
    problems: list[str] = []
    known = set()
    for source in sources:
        try:
            source.validate()
            known.add(source.url)
        except ValueError as exc:
            problems.append(str(exc))
    for claim in claims:
        if not claim.source_urls:
            problems.append(f"unsourced claim: {claim.text}")
        for url in claim.source_urls:
            if url not in known:
                problems.append(f"claim references unknown source: {url}")
    if claims and not any(source.primary for source in sources):
        problems.append("at least one primary source is required")
    return problems

