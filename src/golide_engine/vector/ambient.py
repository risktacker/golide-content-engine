"""The quiet atmosphere under the voice.

Not a music track and nothing licensed: a slow, soft pad synthesised here
(two open chords that breathe into each other) plus a thin airy shimmer, like
the bed under the reference videos. It sits roughly 12 dB under the voice and
is pushed down a little more while the owner is speaking (see render.py).
"""

from __future__ import annotations

import hashlib
import math
import wave
from pathlib import Path

import numpy as np

RATE = 48000
LEVEL_DB = -29.0  # RMS of the bed before ducking; the voice sits near -19 dB RMS

# Calm open voicings (Hz). Each video picks one pair from its title, so videos
# do not all sound identical but always stay soft and unresolved.
PROGRESSIONS = (
    ((73.42, 110.00, 146.83, 220.00, 329.63), (58.27, 87.31, 116.54, 174.61, 293.66)),   # D5 / Bb
    ((65.41, 98.00, 130.81, 196.00, 311.13), (55.00, 82.41, 110.00, 164.81, 261.63)),    # Cm / Am
    ((82.41, 123.47, 164.81, 246.94, 369.99), (65.41, 98.00, 130.81, 196.00, 329.63)),   # E5 / C
)
CYCLE_SECONDS = 18.0


def _pick(seed_text: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    digest = hashlib.sha256(seed_text.encode("utf-8")).digest()
    return PROGRESSIONS[digest[0] % len(PROGRESSIONS)]


def _band_noise(n: int, low: float, high: float, seed: int) -> np.ndarray:
    spectrum = np.fft.rfft(np.random.default_rng(seed).standard_normal(n))
    freqs = np.fft.rfftfreq(n, 1 / RATE)
    mask = np.clip((freqs - low) / (low * 0.5), 0, 1) * np.clip((high - freqs) / (high * 0.3), 0, 1)
    out = np.fft.irfft(spectrum * mask, n)
    return out / (np.max(np.abs(out)) or 1.0)


def ambient_bed(duration: float, seed_text: str = "golide") -> np.ndarray:
    n = int(RATE * (duration + 0.5))
    t = np.arange(n, dtype=np.float64) / RATE
    chord_a, chord_b = _pick(seed_text)
    # Smooth back-and-forth between the two chords, never a hard change.
    mix = 0.5 + 0.5 * np.cos(math.tau * t / CYCLE_SECONDS)
    bed = np.zeros(n)
    rng = np.random.default_rng(len(seed_text))
    for chord, weight in ((chord_a, mix), (chord_b, 1 - mix)):
        for i, freq in enumerate(chord):
            amp = 1.0 / (1 + i * 0.7)
            lfo = 0.75 + 0.25 * np.sin(math.tau * rng.uniform(0.03, 0.09) * t + rng.uniform(0, math.tau))
            for detune in (-0.0018, 0.0018):
                bed += weight * amp * lfo * np.sin(math.tau * freq * (1 + detune) * t + rng.uniform(0, math.tau))
    # Thin "air" on top, the way the reference has a faint high shimmer.
    air = _band_noise(n, 3500, 7500, 5) * (0.5 + 0.5 * np.sin(math.tau * 0.05 * t))
    bed = bed / (np.sqrt(np.mean(bed ** 2)) or 1.0) + 0.12 * air
    # Gentle fade in and out.
    fade_in = np.clip(t / 2.5, 0, 1)
    fade_out = np.clip((duration - t) / 3.0, 0, 1)
    bed *= (fade_in * fade_out) ** 2
    rms = np.sqrt(np.mean(bed[: int(RATE * duration)] ** 2)) or 1.0
    bed *= 10 ** (LEVEL_DB / 20) / rms
    return bed[: int(RATE * duration)]


def render_ambient(duration: float, output: Path, seed_text: str = "golide") -> Path:
    pcm = np.clip(ambient_bed(duration, seed_text), -1, 1)
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes((pcm * 32767).astype("<i2").tobytes())
    return output
