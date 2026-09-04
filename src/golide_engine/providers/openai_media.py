from __future__ import annotations

import base64
import subprocess
import tempfile
import urllib.request
from contextlib import ExitStack
from pathlib import Path

from .base import ProviderOutput
from .openai_client import client
from ..visual_identity import VisualIdentity


class OpenAIImageProvider:
    def __init__(self, model: str = "gpt-image-2", quality: str = "medium"):
        self.model = model
        self.quality = quality

    @staticmethod
    def _identity() -> VisualIdentity:
        policy_path = Path.cwd() / "config" / "visual-identity.json"
        if not policy_path.exists():
            raise RuntimeError(
                "locked G$LIDE visual identity config is missing; image generation is blocked"
            )
        return VisualIdentity(policy_path)

    @classmethod
    def _locked_prompt(cls, prompt: str) -> str:
        """Apply the repository's locked visual identity to every generated image."""
        return cls._identity().apply(prompt)

    @classmethod
    def _download_identity_references(cls, temp_dir: Path) -> list[Path]:
        """Fetch stable Esiah identity references declared by visual identity policy.

        These references live in the public GOLIDE portfolio repo so unattended
        productions can always ground the GPT thumbnail in the same real identity.
        A network failure does not silently invent a person: the caller falls back
        to the locked repository canonical asset instead.
        """
        identity = cls._identity()
        urls = [str(x).strip() for x in identity.avatar.get("identity_reference_urls", []) if str(x).strip()]
        downloaded: list[Path] = []
        for index, url in enumerate(urls):
            if not url.startswith("https://raw.githubusercontent.com/risktacker/golide/"):
                raise RuntimeError(f"unapproved thumbnail identity reference URL: {url}")
            suffix = Path(url.split("?", 1)[0]).suffix.lower() or ".png"
            target = temp_dir / f"golide-avatar-identity-reference-{index:02d}{suffix}"
            try:
                with urllib.request.urlopen(url, timeout=30) as response:
                    payload = response.read()
            except Exception as exc:
                raise RuntimeError(f"unable to download locked Esiah identity reference: {url}") from exc
            if len(payload) < 1024:
                raise RuntimeError(f"downloaded Esiah identity reference is unexpectedly small: {url}")
            target.write_bytes(payload)
            downloaded.append(target)
        return downloaded

    @classmethod
    def _references_for(
        cls,
        prompt: str,
        supplied: list[Path] | None,
        *,
        thumbnail: bool,
        downloaded_identity: list[Path] | None = None,
    ) -> list[Path]:
        identity = cls._identity()
        references = list(supplied or [])

        if thumbnail:
            identity_refs = list(downloaded_identity or [])
            if identity_refs:
                # Stable real-person references are authoritative for thumbnail identity.
                # They come first; topic/style references follow.
                identity_resolved = {item.resolve() for item in identity_refs}
                references = [item for item in references if item.resolve() not in identity_resolved]
                references = identity_refs + references
                return references

        # Explicit avatar scenes, or thumbnails without downloadable identity refs,
        # retain the repository canonical fallback.
        if thumbnail or identity.requests_avatar(prompt):
            canonical = identity.canonical_avatar_reference()
            canonical_resolved = canonical.resolve()
            references = [item for item in references if item.resolve() != canonical_resolved]
            references.insert(0, canonical)
        return references

    @staticmethod
    def _normalize_edit_references(references: list[Path], temp_dir: Path) -> list[Path]:
        """Normalize JPEG edit references to RGB PNG for the Images API."""
        normalized: list[Path] = []
        for index, source in enumerate(references):
            if source.suffix.lower() not in {".jpg", ".jpeg"}:
                normalized.append(source)
                continue
            target = temp_dir / f"reference-{index:02d}.png"
            command = [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(source),
                "-vf",
                "format=rgb24",
                str(target),
            ]
            try:
                subprocess.run(command, check=True)
            except subprocess.CalledProcessError:
                payload = source.read_bytes()
                if payload.startswith(b"\xff\xd8") and not payload.endswith(b"\xff\xd9"):
                    repaired = temp_dir / f"reference-{index:02d}-repaired.jpg"
                    repaired.write_bytes(payload + b"\xff\xd9")
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-v",
                            "error",
                            "-y",
                            "-i",
                            str(repaired),
                            "-vf",
                            "format=rgb24",
                            str(target),
                        ],
                        check=True,
                    )
                else:
                    raise
            if not target.is_file() or target.stat().st_size == 0:
                raise RuntimeError(f"image reference normalization produced no output: {source}")
            normalized.append(target)
        return normalized

    def _create(
        self,
        prompt: str,
        output: Path,
        size: str,
        reference_images: list[Path] | None,
        *,
        thumbnail: bool,
    ) -> ProviderOutput:
        prompt = self._locked_prompt(prompt)
        with tempfile.TemporaryDirectory(prefix="golide-image-ref-") as temp_name:
            temp_dir = Path(temp_name)
            identity_refs: list[Path] = []
            if thumbnail:
                identity_refs = self._download_identity_references(temp_dir)
            references = self._references_for(
                prompt,
                reference_images,
                thumbnail=thumbnail,
                downloaded_identity=identity_refs,
            )
            if references:
                normalized = self._normalize_edit_references(references, temp_dir)
                with ExitStack() as stack:
                    handles = [stack.enter_context(path.open("rb")) for path in normalized]
                    response = client().images.edit(
                        model=self.model,
                        image=handles,
                        prompt=prompt,
                        size=size,
                        quality=self.quality,
                    )
            else:
                response = client().images.generate(
                    model=self.model,
                    prompt=prompt,
                    size=size,
                    quality=self.quality,
                )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(base64.b64decode(response.data[0].b64_json))
        usage = getattr(response, "usage", None)
        if usage and hasattr(usage, "model_dump"):
            usage = usage.model_dump()
        elif usage and not isinstance(usage, dict):
            usage = None
        return ProviderOutput(output, getattr(response, "id", None), details=usage)

    def create_image(
        self,
        prompt: str,
        output: Path,
        size: str,
        reference_images: list[Path] | None = None,
    ) -> ProviderOutput:
        return self._create(prompt, output, size, reference_images, thumbnail=False)

    def create_thumbnail(
        self,
        prompt: str,
        output: Path,
        size: str = "1536x1024",
        reference_images: list[Path] | None = None,
    ) -> ProviderOutput:
        return self._create(prompt, output, size, reference_images, thumbnail=True)


class OpenAIVoiceProvider:
    def __init__(self, model: str = "gpt-4o-mini-tts", voice: str = "cedar", instructions: str = ""):
        self.model = model
        self.voice = voice
        self.instructions = instructions

    def synthesize(self, script: str, output: Path) -> ProviderOutput:
        with client().audio.speech.with_streaming_response.create(
            model=self.model, voice=self.voice, input=script,
            instructions=self.instructions, response_format="wav",
        ) as response:
            response.stream_to_file(output)
        return ProviderOutput(output, None)


class OpenAICaptionProvider:
    def __init__(self, model: str = "whisper-1"):
        self.model = model

    def transcribe_words(self, audio: Path) -> ProviderOutput:
        with audio.open("rb") as handle:
            response = client().audio.transcriptions.create(
                model=self.model, file=handle, response_format="verbose_json",
                timestamp_granularities=["word"],
            )
        words = [
            {"word": item.word, "start": float(item.start), "end": float(item.end)}
            for item in response.words
        ]
        return ProviderOutput(words, getattr(response, "id", None))
