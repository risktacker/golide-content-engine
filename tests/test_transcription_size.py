"""2026-10-10: a long recording over 25 MB must still be transcribed."""
import subprocess
from types import SimpleNamespace

from golide_engine.providers import openai_media


def test_long_recording_is_sent_small(tmp_path, monkeypatch):
    wav = tmp_path / "long.wav"   # 6 minutes of 48 kHz stereo 16-bit: about 69 MB
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=360",
                    "-ac", "2", "-ar", "48000", str(wav)], check=True)
    assert wav.stat().st_size > 25 * 1024 * 1024
    sent = {}

    def create(**kwargs):
        handle = kwargs["file"]
        handle.seek(0, 2)
        sent["bytes"] = handle.tell()
        return SimpleNamespace(words=[SimpleNamespace(word="hi", start=0.0, end=0.4)], id="t")

    fake = SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create)))
    monkeypatch.setattr(openai_media, "client", lambda: fake)
    provider = openai_media.__dict__[next(n for n, v in openai_media.__dict__.items()
                                          if isinstance(v, type) and hasattr(v, "transcribe_words"))]
    obj = provider.__new__(provider)
    obj.model = "test"
    out = obj.transcribe_words(wav)
    assert sent["bytes"] < 5 * 1024 * 1024
    assert out.value[0]["word"] == "hi"
