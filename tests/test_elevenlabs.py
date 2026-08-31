import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from golide_engine.providers.elevenlabs import ElevenLabsVoiceProvider, alignment_to_words


class _Headers(dict):
    pass


class _Response:
    def __init__(self, payload):
        self.payload = payload
        self.headers = _Headers({"request-id": "req-1"})

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ElevenLabsProviderTests(unittest.TestCase):
    def test_character_alignment_becomes_word_alignment(self):
        alignment = {
            "characters": list("One bit."),
            "character_start_times_seconds": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
            "character_end_times_seconds": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
        }
        self.assertEqual(
            [
                {"word": "One", "start": 0.0, "end": 0.3},
                {"word": "bit.", "start": 0.4, "end": 0.8},
            ],
            alignment_to_words(alignment),
        )

    def test_synthesis_writes_audio_and_returns_native_words(self):
        alignment = {
            "characters": list("Go."),
            "character_start_times_seconds": [0.0, 0.1, 0.2],
            "character_end_times_seconds": [0.1, 0.2, 0.3],
        }
        response = {
            "audio_base64": base64.b64encode(b"audio").decode("ascii"),
            "normalized_alignment": alignment,
        }
        provider = ElevenLabsVoiceProvider("eleven_multilingual_v2", "voice-id")
        with tempfile.TemporaryDirectory() as temp, patch.dict(
            os.environ, {"ELEVENLABS_API_KEY": "test-key"}
        ), patch(
            "golide_engine.providers.elevenlabs.urlopen", return_value=_Response(response)
        ):
            output = Path(temp) / "narration.mp3"
            result = provider.synthesize("Go.", output)
            self.assertEqual(b"audio", output.read_bytes())
            self.assertEqual("Go.", result.details["words"][0]["word"])
            self.assertEqual(3, result.details["characters"])
            self.assertEqual("req-1", result.request_id)

    def test_request_character_ceiling_fails_before_network(self):
        provider = ElevenLabsVoiceProvider(
            "eleven_multilingual_v2", "voice-id", max_characters_per_request=3
        )
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                provider.synthesize("Four", Path(temp) / "narration.mp3")


if __name__ == "__main__":
    unittest.main()
