"""The quiet atmosphere under the voice.

Not a music track and nothing licensed: every bed is synthesised here, so it
costs nothing and can never be claimed. Owner direction 2026-10-07: keep the
sound, but do not use the same bed on every video. There are four beds with
the same calm character and different texture, and each one is played in a
different key per video:

* drift  - two open chords breathing into each other, a faint high shimmer
           (the bed the owner approved on 5 Oct)
* pulse  - a slow, soft arpeggio over a thin pad, like a tech documentary
* glass  - sparse bell tones from a pentatonic scale over a warm low pad
* tide   - a slow three-chord minor progression with gentle swells of air

The bed sits under the voice and is pushed down a little more while the owner
speaks (sidechain in render.py).
"""

from __future__ import annotations

import hashlib
import math
import wave
from pathlib import Path

import numpy as np

RATE = 48000
# Owner review 2026-10-05: at -29 dB the bed vanished on phones; -16 dB (~9 dB
# under the voice) was right. Owner review 2026-10-07: "just a little back off",
# so 1.5 dB lower (~10.5 dB under the voice). Owner review 2026-10-22: "just a
# little bit" again, music only (the pops and effects stay as they are): 1.5 dB lower.
# Owner review 2026-10-29: "reduce it a bit more, these are explanation videos, the sound
# and music don't need to be colliding... just make sure it's audible": 3 dB lower (about
# 13.5 dB under the voice), and the dip under the voice is a little deeper (render.py).
LEVEL_DB = -22.0
# Owner review 2026-11-04: "bring back a bit of music" on long videos: the dip under the voice
# is now about 12 dB (render.py), so the bed is heard softly all the way through.
# Owner review 2026-11-01: levels are separate for shorts and long videos. Long videos
# are for listening ("it needs hearability"): the bed sits a little lower and render.py
# ducks it to almost nothing under the voice, so it is heard only in the pauses. Shorts:
# "just reduce a bit", 1.5 dB.
LEVELS_DB = {"long": -21.0, "short": -23.5}   # 2026-11-05 (owner): long up a few bits, 3 dB

# 2026-11-05 (owner): "multi symphony, not one throughout". Chapters rotate through instruments
# that sound clearly different: synth pad, piano-like keys, arpeggio, strings, bells, plucks, swell.
BEDS = ("drift", "keys", "pulse", "strings", "glass", "pluck", "tide")
# Roots (Hz) a bed can be played in; picked per video so two videos on the same
# bed still differ.
ROOTS = (146.83, 155.56, 164.81, 174.61, 196.00, 220.00)  # D, Eb, E, F, G, A (one octave up for phones)

CYCLE_SECONDS = 18.0


def _digest(seed_text: str) -> bytes:
    return hashlib.sha256(seed_text.encode("utf-8")).digest()


def choose_bed(seed_text: str, variant: int | None = None) -> tuple[str, float]:
    """(bed name, root Hz). ``variant`` rotates beds in order; otherwise the title picks."""
    digest = _digest(seed_text)
    index = variant % len(BEDS) if variant is not None else digest[0] % len(BEDS)
    return BEDS[index], ROOTS[digest[1] % len(ROOTS)]


def _band_noise(n: int, low: float, high: float, seed: int) -> np.ndarray:
    spectrum = np.fft.rfft(np.random.default_rng(seed).standard_normal(n))
    freqs = np.fft.rfftfreq(n, 1 / RATE)
    mask = np.clip((freqs - low) / (low * 0.5), 0, 1) * np.clip((high - freqs) / (high * 0.3), 0, 1)
    out = np.fft.irfft(spectrum * mask, n)
    return out / (np.max(np.abs(out)) or 1.0)


def _ratio(semitones: float) -> float:
    return 2 ** (semitones / 12)


def _pad(t: np.ndarray, freqs, rng, weight=1.0) -> np.ndarray:
    out = np.zeros_like(t)
    for i, freq in enumerate(freqs):
        amp = 1.0 / (1 + i * 0.35)
        lfo = 0.75 + 0.25 * np.sin(math.tau * rng.uniform(0.03, 0.09) * t + rng.uniform(0, math.tau))
        for detune in (-0.0018, 0.0018):
            out += amp * lfo * np.sin(math.tau * freq * (1 + detune) * t + rng.uniform(0, math.tau))
    return out * weight


def _note(freq: float, length: float, decay: float, bright: float = 0.0) -> np.ndarray:
    """A soft struck tone: sine plus a little octave, exponential decay, no click."""
    n = int(RATE * length)
    tt = np.arange(n) / RATE
    env = np.exp(-tt / decay) * np.clip(tt / 0.012, 0, 1)
    tone = np.sin(math.tau * freq * tt) + bright * np.sin(math.tau * freq * 2.0 * tt)
    return env * tone


def _place(buffer: np.ndarray, note: np.ndarray, at: float, gain: float) -> None:
    start = int(at * RATE)
    if start >= len(buffer):
        return
    end = min(len(buffer), start + len(note))
    buffer[start:end] += gain * note[: end - start]


def _drift(t, root, rng):
    chord_a = [root * _ratio(s) for s in (0, 7, 12, 19, 26)]
    chord_b = [root * _ratio(s) for s in (-4, 3, 8, 15, 22)]
    mix = 0.5 + 0.5 * np.cos(math.tau * t / CYCLE_SECONDS)
    bed = _pad(t, chord_a, rng, mix) + _pad(t, chord_b, rng, 1 - mix)
    return bed, 0.18


def _pulse(t, root, rng):
    pad = _pad(t, [root * _ratio(s) for s in (0, 7, 15)], rng) * 0.35
    notes = np.zeros_like(t)
    pattern = (0, 7, 12, 15, 12, 7)  # minor arpeggio up and down
    step, at, k = 0.92, 0.6, 0
    duration = len(t) / RATE
    while at < duration:
        bar = int(at / (step * len(pattern)))
        shift = (0, -2, 3, -4)[bar % 4]  # the arpeggio moves through four roots
        freq = root * 2 * _ratio(pattern[k % len(pattern)] + shift)
        _place(notes, _note(freq, 2.4, 0.55, bright=0.12), at, 0.55)
        at += step
        k += 1
    return pad + notes, 0.10


def _glass(t, root, rng):
    pad = _pad(t, [root * 0.5 * _ratio(s) for s in (0, 7, 12)], rng) * 0.55
    bells = np.zeros_like(t)
    scale = (0, 2, 4, 7, 9, 12, 14, 16)  # major pentatonic over two octaves
    at = 1.5
    duration = len(t) / RATE
    while at < duration:
        freq = root * 2 * _ratio(scale[int(rng.integers(len(scale)))])
        _place(bells, _note(freq, 5.0, 1.6, bright=0.3), at, 0.45)
        if rng.random() < 0.35:  # an occasional soft answer a fifth below
            _place(bells, _note(freq * 2 / 3, 5.0, 1.8), at + 0.45, 0.25)
        at += float(rng.uniform(2.2, 4.2))
    return pad + bells, 0.08


def _tide(t, root, rng):
    chords = ([0, 3, 7, 12], [-4, 0, 3, 8], [-2, 2, 5, 10])  # i - VI - VII, minor and open
    cycle = 24.0
    bed = np.zeros_like(t)
    phase = (t / cycle) % 1.0
    for index, chord in enumerate(chords):
        # each chord owns a third of the cycle with long crossfades
        centre = (index + 0.5) / len(chords)
        distance = np.minimum(np.abs(phase - centre), 1 - np.abs(phase - centre))
        weight = np.clip(1.2 - distance * len(chords) * 1.4, 0, 1) ** 2
        bed += _pad(t, [root * _ratio(s) for s in chord], rng, weight)
    swell = 0.6 + 0.4 * np.sin(math.tau * t / 11.0)
    return bed * swell, 0.24


def _rich(freq: float, length: float, decay: float, harmonics, attack: float = 0.006) -> np.ndarray:
    """A tone from a few harmonics, each fading at its own speed (higher ones faster)."""
    n = int(RATE * length)
    tt = np.arange(n) / RATE
    out = np.zeros(n)
    for k, amp in enumerate(harmonics, start=1):
        out += amp * np.exp(-tt * k / decay) * np.sin(math.tau * freq * k * tt)
    return out * np.clip(tt / attack, 0, 1)


def _keys(t, root, rng):
    """Piano-like chords, one every bar, through a calm minor progression."""
    out = np.zeros_like(t)
    progression = ((0, 3, 7, 12), (-4, 0, 3, 8), (-7, -3, 0, 5), (-2, 2, 5, 10))
    bar, at, k = 3.6, 0.4, 0
    duration = len(t) / RATE
    while at < duration:
        for j, s in enumerate(progression[k % len(progression)]):
            _place(out, _rich(root * _ratio(s), 3.4, 2.6, (1, 0.5, 0.25, 0.12)), at + j * 0.03, 0.5)
        if k % 2:   # a soft melody note on the off-bar
            _place(out, _rich(root * 2 * _ratio((7, 10, 12, 15)[int(rng.integers(4))]), 2.0, 1.2, (1, 0.3)), at + bar / 2, 0.3)
        at += bar
        k += 1
    return out, 0.05


def _strings(t, root, rng):
    """A bowed string section: rich harmonics, slow swell, gentle vibrato."""
    out = np.zeros_like(t)
    vibrato = 1 + 0.003 * np.sin(math.tau * 5.2 * t)
    swell = 0.55 + 0.45 * np.sin(math.tau * t / 14.0 - 1.2)
    for s in (0, 7, 12, 15):
        f = root * 0.5 * _ratio(s)
        for k in range(1, 7):
            out += (1 / k) * np.sin(math.tau * f * k * t * vibrato + rng.uniform(0, math.tau))
    return out * swell, 0.06


def _pluck(t, root, rng):
    """Plucked, guitar-like notes walking a pentatonic pattern over a low drone."""
    drone = _pad(t, [root * 0.5, root * 0.5 * _ratio(7)], rng) * 0.25
    out = np.zeros_like(t)
    scale = (0, 3, 5, 7, 10, 12, 15)
    at, step = 0.3, 0.46
    duration = len(t) / RATE
    k = 0
    while at < duration:
        if (k % 8) not in (3, 7):   # rests keep it from feeling mechanical
            s = scale[int(rng.integers(len(scale)))]
            _place(out, _rich(root * _ratio(s), 1.6, 0.35, (1, 0.6, 0.35, 0.2, 0.1), 0.002), at, 0.55)
        at += step
        k += 1
    return drone + out, 0.07


_BUILDERS = {"drift": _drift, "pulse": _pulse, "glass": _glass, "tide": _tide,
             "keys": _keys, "strings": _strings, "pluck": _pluck}


def ambient_bed(duration: float, seed_text: str = "golide", variant: int | None = None,
                level_db: float = LEVEL_DB) -> np.ndarray:
    n = int(RATE * (duration + 0.5))
    t = np.arange(n, dtype=np.float64) / RATE
    name, root = choose_bed(seed_text, variant)
    rng = np.random.default_rng(int.from_bytes(_digest(seed_text)[2:6], "big"))
    bed, air_amount = _BUILDERS[name](t, root, rng)
    # Thin "air" on top, the faint high shimmer of the reference.
    air = _band_noise(n, 3500, 7500, 5) * (0.5 + 0.5 * np.sin(math.tau * 0.05 * t))
    bed = bed / (np.sqrt(np.mean(bed ** 2)) or 1.0) + air_amount * air
    fade_in = np.clip(t / 2.5, 0, 1)
    fade_out = np.clip((duration - t) / 3.0, 0, 1)
    bed *= (fade_in * fade_out) ** 2
    rms = np.sqrt(np.mean(bed[: int(RATE * duration)] ** 2)) or 1.0
    bed *= 10 ** (level_db / 20) / rms
    return bed[: int(RATE * duration)]


CROSSFADE_SECONDS = 2.0     # 2026-11-04: the music changes at each chapter, blended over 2 s
DIP_DB, DIP_SECONDS = -8.0, 1.0   # ... and breathes in for a moment at the chapter card


def sectioned_bed(duration: float, starts: list[float], seed_text: str = "golide",
                  variant: int | None = None, level_db: float = LEVEL_DB) -> np.ndarray:
    """A different bed for each section (owner 2026-11-04: "one music sound the whole 7 minutes
    is boring"). Section k plays bed (first + k), each at the same loudness, crossfaded over
    CROSSFADE_SECONDS, with a short dip where each new section starts."""
    n = int(RATE * duration)
    bounds = sorted({0.0, *[float(s) for s in starts if 0.5 < float(s) < duration - 1.0]})
    if len(bounds) < 2:
        return ambient_bed(duration, seed_text, variant, level_db)
    first = variant if variant is not None else _digest(seed_text)[0]
    t = np.arange(n, dtype=np.float64) / RATE
    out = np.zeros(n)
    for k, start in enumerate(bounds):
        end = bounds[k + 1] if k + 1 < len(bounds) else duration
        idx = (first + k) % len(BEDS)
        # Each instrument is only made for its own section plus the crossfades (fast to render).
        lo = max(0.0, start - CROSSFADE_SECONDS)
        hi = min(duration, end + CROSSFADE_SECONDS)
        part = ambient_bed(hi - lo, f"{seed_text}#{idx}", idx, level_db)
        i0 = int(lo * RATE)
        seg = t[i0:i0 + len(part)]
        rise = np.clip((seg - start + CROSSFADE_SECONDS / 2) / CROSSFADE_SECONDS, 0, 1) if k else np.ones(len(seg))
        fall = np.clip((end + CROSSFADE_SECONDS / 2 - seg) / CROSSFADE_SECONDS, 0, 1) if k + 1 < len(bounds) else np.ones(len(seg))
        out[i0:i0 + len(seg)] += part[:len(seg)] * np.sqrt(np.minimum(rise, fall))   # equal-power crossfade
    dip = np.ones(n)
    for start in bounds[1:]:
        d = np.clip(1 - np.abs(t - start) / (DIP_SECONDS / 2), 0, 1)
        dip *= 1 - (1 - 10 ** (DIP_DB / 20)) * d
    return out * dip


def render_ambient(duration: float, output: Path, seed_text: str = "golide", variant: int | None = None,
                   level_db: float = LEVEL_DB, starts: list[float] | None = None) -> Path:
    bed = (sectioned_bed(duration, starts, seed_text, variant, level_db) if starts
           else ambient_bed(duration, seed_text, variant, level_db))
    pcm = np.clip(bed, -1, 1)
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes((pcm * 32767).astype("<i2").tobytes())
    return output
