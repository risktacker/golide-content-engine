from __future__ import annotations

import base64
import subprocess
import tempfile
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
    def _references_for(
        cls,
        prompt: str,
        supplied: list[Path] | None,
        *,
        thumbnail: bool,
    ) -> list[Path]:
        identity = cls._identity()
        references = list(supplied or [])
        # A thumbnail is a branded host surface: it must never invent a replacement
        # person. Explicit avatar scenes get the same treatment. Ordinary subject
        # visuals do not receive the avatar reference, so the model is not encouraged
        # to insert a person where the story calls for a mechanism/object/diagram.
        if thumbnail or identity.requests_avatar(prompt):
            canonical = identity.canonical_avatar_reference()
            canonical_resolved = canonical.resolve()
            references = [
                item for item in references
                if item.resolve() != canonical_resolved
            ]
            references.insert(0, canonical)
        return references

    @staticmethod
    def _normalize_edit_references(references: list[Path], temp_dir: Path) -> list[Path]:
        """Normalize edit references to RGB PNG for the Images API.

        Some otherwise-valid JPEG references can be rejected by the image-edit endpoint
        because of their encoded color mode. Converting only the request copy keeps the
        locked canonical source/checksum untouched while giving the API a deterministic
        supported representation. A legacy canonical JPEG snapshot is known to be
        missing a terminal EOI marker; if ffmpeg rejects it, repair only the temporary
        request copy by appending the marker and retry once.
        """
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
        references = self._references_for(prompt, reference_images, thumbnail=thumbnail)
        prompt = self._locked_prompt(prompt)
        if references:
            with tempfile.TemporaryDirectory(prefix="golide-image-ref-") as temp_name:
                normalized = self._normalize_edit_references(references, Path(temp_name))
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
        return self._create(
            prompt,
            output,
            size,
            reference_images,
            thumbnail=False,
        )

    def create_thumbnail(
        self,
        prompt: str,
        output: Path,
        size: str = "1536x1024",
        reference_images: list[Path] | None = None,
    ) -> ProviderOutput:
        return self._create(
            prompt,
            output,
            size,
            reference_images,
            thumbnail=True,
        )


class OpenAIVoiceProvider:
    def __init__(self, model: str = "gpt-4o-mini-tts", voice: str = "cedar", instructions: str = ""):
        self.model = model
        self.voice = voice
        self.instructions = instructions

    def synthesize(self, script: str, output: Path) -> ProviderOutput:
        output.parent.mkdir(parents=True, exist_ok=True)
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
        return ProviderOutput(words, getattr(response, "id", None)
        )