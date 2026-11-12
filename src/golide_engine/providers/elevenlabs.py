from __future__ import annotations

import base64
import json
import os
import re
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


def strip_cues(words: list[dict]) -> list[dict]:
    """Drop the emotion cues ([excited], [clears throat]) from timed words: they are performed, not said."""
    out, inside = [], False
    for w in words:
        token = str(w["word"])
        if "[" in token:
            inside = True
        if not inside:
            out.append(w)
        elif "]" in token:
            inside = False
            rest = token.split("]", 1)[1].strip()
            if rest:
                out.append(dict(w, word=rest))
    return out


class ElevenLabsVoiceProvider:
    api_root = "https://api.elevenlabs.io/v1"
    _FORBIDDEN_NARRATION_PREFIX = re.compile(
        r"(?im)^\s*(?:#{1,6}\s*)?(?:script|narrator|visual|scene|camera|shot|b-?roll|"
        r"caption|on[- ]?screen|music|sfx|sound effect|transition|editor(?:ial)? note|"
        r"production note)\s*[:\-]"
    )
    _FORBIDDEN_BRACKET_DIRECTION = re.compile(
        r"(?i)\[(?:visual|scene|camera|shot|b-?roll|music|sfx|sound effect|transition|pause\s+\d+[^]]*)\]"
    )

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

    @classmethod
    def validate_spoken_narration(cls, text: str) -> None:
        """Fail before any paid TTS request if production directions leaked into speech."""
        stripped = text.strip()
        if not stripped:
            raise ValueError("narration script is empty")
        marker = cls._FORBIDDEN_NARRATION_PREFIX.search(stripped)
        if marker:
            raise ValueError(
                "narration contains a production-direction label and was blocked before ElevenLabs: "
                + marker.group(0).strip()
            )
        bracket = cls._FORBIDDEN_BRACKET_DIRECTION.search(stripped)
        if bracket:
            raise ValueError(
                "narration contains a bracketed production direction and was blocked before ElevenLabs"
            )
        if "```" in stripped:
            raise ValueError("narration contains a code/markdown fence and was blocked before ElevenLabs")
        words = re.findall(r"\b[\w'-]+\b", stripped)
        if len(words) < 20:
            raise ValueError("narration is too short to authorize a paid ElevenLabs request")
        sentence_marks = len(re.findall(r"[.!?]", stripped))
        if sentence_marks < max(2, len(words) // 120):
            raise ValueError(
                "narration has too little sentence punctuation for natural speech; blocked before ElevenLabs"
            )

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

    def _parts(self, text: str) -> list[str]:
        """Paragraphs (then sentences) packed into requests under the per-request limit."""
        limit = self.max_characters_per_request
        pieces: list[str] = []
        for para in [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]:
            if len(para) <= limit:
                pieces.append(para)
                continue
            for sentence in re.split(r"(?<=[.!?])\s+", para):
                pieces.append(sentence)
        parts: list[str] = []
        for piece in pieces:
            if len(piece) > limit:
                raise ValueError(f"one sentence has {len(piece)} characters; limit is {limit}")
            if parts and len(parts[-1]) + 2 + len(piece) <= limit:
                parts[-1] += "\n\n" + piece
            else:
                parts.append(piece)
        return parts

    def _one(self, text: str, output: Path) -> tuple[list[dict], Any]:
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
        if not encoded_audio:
            raise RuntimeError("ElevenLabs response omitted audio")
        alignment = payload.get("normalized_alignment") or payload.get("alignment")
        try:
            words = alignment_to_words(alignment) if alignment else []
        except ValueError:
            words = []
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(base64.b64decode(encoded_audio, validate=True))
        return words, headers

    @staticmethod
    def _duration(path: Path) -> float:
        import subprocess
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                             capture_output=True, text=True, check=True)
        return float(out.stdout.strip() or 0)

    def synthesize(self, script: str, output: Path) -> ProviderOutput:
        """2026-11-12: read in parts under the per-request limit (Eleven v3 takes 5,000 characters) and joined.
        Emotion cues in square brackets ([excited], [serious]...) are performed, never spoken, and are
        dropped from the word timings. Word timings may be empty (then the caller transcribes the audio)."""
        import subprocess
        text = script.strip()
        self.validate_spoken_narration(text)
        characters = len(text)
        parts = self._parts(text)
        words: list[dict] = []
        files: list[Path] = []
        offset, request_id, timed = 0.0, None, True
        for i, part in enumerate(parts):
            piece = output.with_name(f"{output.stem}.part{i}{output.suffix}")
            part_words, headers = self._one(part, piece)
            request_id = request_id or headers.get("request-id") or headers.get("x-request-id")
            timed = timed and bool(part_words)
            words += [dict(w, start=float(w["start"]) + offset, end=float(w["end"]) + offset) for w in part_words]
            try:
                offset += self._duration(piece)
            except Exception:  # noqa: BLE001 - no readable length: the last timed word ends the part
                offset = float(words[-1]["end"]) if words else offset
            files.append(piece)
        if len(files) == 1:
            files[0].replace(output)
        else:
            listing = output.with_name(output.stem + ".parts.txt")
            listing.write_text("".join(f"file '{f.resolve()}'\n" for f in files), encoding="utf-8")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                            "-c", "copy", str(output)], check=True)
            for f in files + [listing]:
                f.unlink(missing_ok=True)
        words = strip_cues(words) if timed else []
        return ProviderOutput(
            output,
            request_id,
            details={
                "provider": "elevenlabs",
                "model": self.model,
                "voice_id": self.voice_id,
                "characters": characters,
                "parts": len(parts),
                "duration_seconds": offset,
                "words": words,
            },
        )
