from __future__ import annotations

import base64
from pathlib import Path

from .base import ProviderOutput
from .openai_client import client
from ..visual_identity import VisualIdentity


class OpenAIImageProvider:
    def __init__(self, model: str = "gpt-image-2", quality: str = "medium"):
        self.model = model
        self.quality = quality

    @staticmethod
    def _locked_prompt(prompt: str) -> str:
        """Apply the repository's locked visual identity to every generated image.

        This intentionally lives in the provider layer rather than only in one
        production prompt so automatic productions, thumbnails and future image
        call sites cannot silently forget the G$LIDE avatar rules.
        """
        policy_path = Path.cwd() / "config" / "visual-identity.json"
        if not policy_path.exists():
            raise RuntimeError(
                "locked G$LIDE visual identity config is missing; image generation is blocked"
            )
        return VisualIdentity(policy_path).apply(prompt)

    def create_image(self, prompt: str, output: Path, size: str, reference_images: list[Path] | None = None) -> ProviderOutput:
        prompt = self._locked_prompt(prompt)
        if reference_images:
            handles = [path.open("rb") for path in reference_images]
            try:
                response = client().images.edit(model=self.model, image=handles, prompt=prompt, size=size, quality=self.quality)
            finally:
                for handle in handles:
                    handle.close()
        else:
            response = client().images.generate(model=self.model, prompt=prompt, size=size, quality=self.quality)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(base64.b64decode(response.data[0].b64_json))
        usage = getattr(response, "usage", None)
        if usage and hasattr(usage, "model_dump"):
            usage = usage.model_dump()
        elif usage and not isinstance(usage, dict):
            usage = None
        return ProviderOutput(output, getattr(response, "id", None), details=usage)

    def create_thumbnail(self, prompt: str, output: Path, size: str = "1536x1024", reference_images: list[Path] | None = None) -> ProviderOutput:
        return self.create_image(prompt, output, size, reference_images)


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
        return ProviderOutput(words, getattr(response, "id", None))
