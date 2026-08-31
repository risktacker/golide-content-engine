from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .base import ProviderOutput


class ElevenLabsAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def alignment_to_words(alignment: dict[str, Any]) -> list[dict[str, float | str]]:
    """Convert ElevenLabs character alignment into word-level timing."""
    characters = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    if not characters or not (len(characters) == len(starts) == len(ends)):
        raise ValueError("ElevenLabs returned incomplete character alignment")

    words: list[dict[str, float | str]] = []
    token: list[str] = []
    token_start: float | None = None
    token_end: float | None = None

    def flush() -> None:
        nonlocal token, token_start, token_end
        value = "".join(token).strip()
        if value and token_start is not None and token_end is not None:
            words.append({"word": value, "start": token_start, "end": token_end})
        token, token_start, token_end = [], None, None

    for raw_character, raw_start, raw_end in zip(characters, starts, ends):
        character = str(raw_character)
        start, end = float(raw_start), float(raw_end)
        if character.isspace():
            flush()
            continue
        if token_start is None:
            token_start = start
        token.append(character)
        token_end = end
    flush()
    if not words:
        raise ValueError("ElevenLabs alignment contained no timed words")
    return words


class ElevenLabsVoiceProvider:
    api_root = "https://api.elevenlabs.io/v1"

    def __init__(
        self,
        model: str,
        voice_id: str,
        output_format: str = "mp3_44100_128",
        voice_settings: dict[str, Any] | None = None,
        max_characters_per_request: int = 10_000,
        monthly_character_limit: int = 27_000,
    ):
        self.model = model
        self.voice_id = voice_id
        self.output_format = output_format
        self.voice_settings = voice_settings or {}
        self.max_characters_per_request = int(max_characters_per_request)
        self.monthly_character_limit = int(monthly_character_limit)
        if not self.voice_id:
            raise ValueError("ElevenLabs voice_id is required")
        if self.max_characters_per_request < 1 or self.monthly_character_limit < 1:
            raise ValueError("ElevenLabs character limits must be positive")

    @staticmethod
    def _api_key() -> str:
        key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        if not key:
            raise RuntimeError("ELEVENLABS_API_KEY is not configured")
        return key

    def _request(self, method: str, url: str, payload: dict[str, Any] | None = None) -> tuple[dict[str, Any], Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            url,
            data=body,
            method=method,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "xi-api-key": self._api_key(),
            },
        )
        try:
            with urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data, response.headers
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise ElevenLabsAPIError(f"ElevenLabs HTTP {exc.code}: {detail}", exc.code) from exc
        except URLError as exc:
            raise ConnectionError(f"ElevenLabs connection failed: {exc.reason}") from exc

    def validate_voice(self) -> dict[str, Any]:
        payload, _ = self._request("GET", f"{self.api_root}/voices/{quote(self.voice_id, safe='')}")
        returned_id = str(payload.get("voice_id", ""))
        if returned_id and returned_id != self.voice_id:
            raise RuntimeError("ElevenLabs returned a different voice_id")
        return {
            "voice_id": self.voice_id,
            "name": payload.get("name"),
            "category": payload.get("category"),
            "model": self.model,
        }

    def synthesize(self, script: str, output: Path) -> ProviderOutput:
        text = script.strip()
        characters = len(text)
        if not text:
            raise ValueError("narration script is empty")
        if characters > self.max_characters_per_request:
            raise ValueError(
                f"narration has {characters} characters; limit is {self.max_characters_per_request}"
            )
        payload, headers = self._request(
            "POST",
            (
                f"{self.api_root}/text-to-speech/{quote(self.voice_id, safe='')}/with-timestamps"
                f"?output_format={quote(self.output_format, safe='')}"
            ),
            {
                "text": text,
                "model_id": self.model,
                "voice_settings": self.voice_settings,
            },
        )
        encoded_audio = payload.get("audio_base64")
        alignment = payload.get("normalized_alignment") or payload.get("alignment")
        if not encoded_audio or not alignment:
            raise RuntimeError("ElevenLabs response omitted audio or alignment")
        words = alignment_to_words(alignment)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(base64.b64decode(encoded_audio, validate=True))
        request_id = headers.get("request-id") or headers.get("x-request-id")
        return ProviderOutput(
            output,
            request_id,
            details={
                "provider": "elevenlabs",
                "model": self.model,
                "voice_id": self.voice_id,
                "characters": characters,
                "duration_seconds": float(words[-1]["end"]),
                "words": words,
            },
        )
