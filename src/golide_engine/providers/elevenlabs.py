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
        hook_takes: int = 1,
        take_settings: dict[str, Any] | None = None,
    ):
        self.model = model
        self.voice_id = voice_id
        self.output_format = output_format
        self.voice_settings = voice_settings or {}
        self.max_characters_per_request = int(max_characters_per_request)
        self.monthly_character_limit = int(monthly_character_limit)
        self.hook_takes = max(1, int(hook_takes))
        self.take_settings = take_settings or {}
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

    MIN_PART = 250     # ElevenLabs: very short v3 prompts give inconsistent reads; stay above 250 characters
    HOOK_MAX = 400     # the hook read several times: its opening 2 or 3 sentences

    def _parts(self, text: str) -> list[str]:
        """2026-11-13 (owner, Isaac's method): one request per paragraph, so each paragraph gets its own slightly
        different tone and pace (as a person's energy shifts) instead of one even pattern for the whole video. Same
        characters, same cost. A paragraph under 250 characters joins the next; one over the request limit is split
        on sentences."""
        limit = self.max_characters_per_request
        pieces: list[str] = []
        for para in [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]:
            if len(para) <= limit:
                pieces.append(para)
                continue
            chunk = ""
            for sentence in re.split(r"(?<=[.!?])\s+", para):
                if len(sentence) > limit:
                    raise ValueError(f"one sentence has {len(sentence)} characters; limit is {limit}")
                if chunk and len(chunk) + 1 + len(sentence) > limit:
                    pieces.append(chunk)
                    chunk = sentence
                else:
                    chunk = f"{chunk} {sentence}".strip()
            if chunk:
                pieces.append(chunk)
        if self.hook_takes <= 1:
            # 2026-11-13 (owner): ONE read whenever it fits (v4: 10,000 characters, every video we make). Separate
            # requests come back as different people; only a script past the limit is split, at paragraph breaks,
            # into as few parts as possible.
            parts = []
            for piece in pieces:
                if parts and len(parts[-1]) + 2 + len(piece) <= limit:
                    parts[-1] += "\n\n" + piece
                else:
                    parts.append(piece)
            flat = lambda s: re.sub(r"\s+", " ", s).strip()
            if flat(" ".join(parts)) != flat(" ".join(pieces)):
                raise RuntimeError("voice parts do not add up to the script; nothing was sent")
            return parts
        if self.hook_takes > 1 and pieces and len(pieces[0]) > self.HOOK_MAX:
            # the hook is the opening sentences only (it is the part read several times)
            sentences, hook = re.split(r"(?<=[.!?])\s+", pieces[0]), ""
            while sentences and (len(hook) < self.MIN_PART or len(hook) + 1 + len(sentences[0]) <= self.HOOK_MAX):
                hook = f"{hook} {sentences.pop(0)}".strip()
            rest = " ".join(sentences)
            pieces[0:1] = [hook] + ([rest] if rest else [])
        parts: list[str] = []
        for i, piece in enumerate(pieces):
            if i == 1 and self.hook_takes > 1:      # the hook stays on its own
                parts.append(piece)
                continue
            if parts and len(parts[-1]) < self.MIN_PART and len(parts[-1]) + 2 + len(piece) <= limit:
                parts[-1] += "\n\n" + piece
            else:
                parts.append(piece)
        if len(parts) > 1 and len(parts[-1]) < self.MIN_PART and len(parts[-2]) + 2 + len(parts[-1]) <= limit:
            # 2026-11-13: pop first, then join. `parts[-2] += parts.pop()` read one part and wrote another: the
            # opening of the script was overwritten and the middle read twice (the broken Short of 2026-11-13).
            last = parts.pop()
            parts[-1] = parts[-1] + "\n\n" + last
        # nothing lost, nothing doubled: the parts put back together are the script, in order
        flat = lambda s: re.sub(r"\s+", " ", s).strip()
        if flat(" ".join(parts)) != flat(" ".join(pieces)):
            raise RuntimeError("voice parts do not add up to the script; nothing was sent")
        return parts

    def planned_characters(self, script: str, hook_takes: int | None = None) -> int:
        """Characters this read will use: the script once, plus the extra takes of the hook."""
        takes, self.hook_takes = self.hook_takes, self.hook_takes if hook_takes is None else max(1, hook_takes)
        try:
            parts = self._parts(script.strip())
            return len(script.strip()) + (self.hook_takes - 1) * (len(parts[0]) if len(parts) > 1 else 0)
        finally:
            self.hook_takes = takes

    def _one(self, text: str, output: Path, settings: dict[str, Any] | None = None) -> tuple[list[dict], Any]:
        payload, headers = self._request(
            "POST",
            (
                f"{self.api_root}/text-to-speech/{quote(self.voice_id, safe='')}/with-timestamps"
                f"?output_format={quote(self.output_format, safe='')}"
            ),
            {
                "text": text,
                "model_id": self.model,
                "voice_settings": settings or self.voice_settings,
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

    def _best_take(self, text: str, output: Path) -> tuple[list[dict], Any, list[dict]]:
        """2026-11-13 (owner): the hook (the first part) is read several times and the best read is kept: the
        first with the usual settings, the others with v3's more expressive setting. A take that drops or adds
        words (its length is far off the others') is out; of the rest, the liveliest (the voice rises and falls
        most) wins."""
        takes = []
        for k in range(self.hook_takes):
            path = output.with_name(f"{output.stem}.take{k}{output.suffix}")
            settings = self.voice_settings if k == 0 else {**self.voice_settings, **self.take_settings}
            words, headers = self._one(text, path, settings)
            takes.append({"path": path, "words": words, "headers": headers, "take": k,
                          "seconds": self._duration(path), "life": liveliness(path)})
        report = pick_take(takes, len(text.split()))
        best = next(t for t in takes if t["take"] == report["chosen"])
        best["path"].replace(output)
        for t in takes:
            t["path"].unlink(missing_ok=True)
        return best["words"], best["headers"], report["takes"]

    def synthesize(self, script: str, output: Path, hook_takes: int | None = None) -> ProviderOutput:
        takes, self.hook_takes = self.hook_takes, self.hook_takes if hook_takes is None else max(1, hook_takes)
        try:
            return self._synthesize(script, output)
        finally:
            self.hook_takes = takes

    def _synthesize(self, script: str, output: Path) -> ProviderOutput:
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
        takes_report: list[dict] = []
        for i, part in enumerate(parts):
            piece = output.with_name(f"{output.stem}.part{i}{output.suffix}")
            if i == 0 and self.hook_takes > 1 and len(parts) > 1:
                part_words, headers, takes_report = self._best_take(part, piece)
                characters += (self.hook_takes - 1) * len(part)
            else:
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
        if words:
            # the read says the script once, start to end: same opening words, about the same number of words
            said = [re.sub(r"\W", "", str(w["word"])).lower() for w in words]
            script_words = [re.sub(r"\W", "", x).lower() for x in re.sub(r"\[[^\]]*\]", " ", text).split()]
            script_words = [x for x in script_words if x]
            said = [x for x in said if x]
            if said[:3] != script_words[:3] or abs(len(said) - len(script_words)) > max(3, len(script_words) // 10):
                raise RuntimeError("the voice read does not match the script (opening or length); stopped before the edit")
        return ProviderOutput(
            output,
            request_id,
            details={
                "provider": "elevenlabs",
                "model": self.model,
                "voice_id": self.voice_id,
                "characters": characters,
                "parts": len(parts),
                "hook_takes": takes_report,
                "duration_seconds": offset,
                "words": words,
            },
        )


def liveliness(audio: Path) -> float:
    """How much a read rises and falls: the spread of its pitch (in semitones) plus the spread of its loudness,
    over the voiced moments. A flat read scores low."""
    import subprocess

    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(audio), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         check=True, capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    frame, hop = 640, 320                        # 40 ms frames, 20 ms apart
    pitches, levels = [], []
    for start in range(0, len(x) - frame, hop):
        f = x[start:start + frame]
        rms = float(np.sqrt(np.mean(f * f)))
        if rms < 0.02:
            continue
        f = f - f.mean()
        ac = np.correlate(f, f, mode="full")[frame - 1:]
        lo, hi = 16000 // 400, 16000 // 70       # 70 to 400 Hz
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] > 0.3 * ac[0]:
            pitches.append(16000 / lag)
            levels.append(20 * np.log10(rms))
    if len(pitches) < 10:
        return 0.0
    semis = 12 * np.log2(np.array(pitches) / np.median(pitches))
    return round(float(np.std(np.clip(semis, -12, 12)) + 0.25 * np.std(levels)), 3)


def pick_take(takes: list[dict], words: int) -> dict:
    """The take to keep: of the reads whose length is believable (within 20% of the middle one: a read that
    dropped or invented words is much shorter or longer), the liveliest."""
    lengths = sorted(t["seconds"] for t in takes)
    middle = lengths[len(lengths) // 2] or 1.0
    report = []
    for t in takes:
        ok = abs(t["seconds"] - middle) <= 0.2 * middle and t["seconds"] >= words / 5.5
        report.append({"take": t["take"], "seconds": round(t["seconds"], 2), "liveliness": t["life"], "ok": ok})
    good = [r for r in report if r["ok"]] or [r for r in report if r["take"] == 0]
    chosen = max(good, key=lambda r: r["liveliness"])["take"]
    return {"chosen": chosen, "takes": [dict(r, chosen=r["take"] == chosen) for r in report]}
