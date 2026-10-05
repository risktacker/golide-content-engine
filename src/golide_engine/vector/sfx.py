"""Small sound effects timed to the visuals and the narration.

No music. Every sound is synthesised here (so there is nothing to license)
and kept well under the voice: a soft whoosh when the scene changes, a light
tick on key words, a gentle rise while a drawing or chart builds, a short
scratch on a cross-out and a low hit on the closing logo.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from .align import Group, TimedLine

RATE = 48000
DATA_RISE = {"bar_chart", "line_chart", "spike_vs_curve", "staircase", "ladder", "gauge", "checklist"}


def _env(n: int, attack: float, release: float) -> np.ndarray:
    t = np.linspace(0, 1, n, endpoint=False)
    a = max(1e-3, attack)
    rise = np.clip(t / a, 0, 1)
    fall = np.clip((1 - t) / max(1e-3, release), 0, 1)
    return np.minimum(rise, fall) ** 1.5


def _noise(n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal(n)


def _lowpass(x: np.ndarray, alpha: np.ndarray | float) -> np.ndarray:
    y = np.empty_like(x)
    acc = 0.0
    alphas = np.broadcast_to(alpha, x.shape)
    for i, (v, a) in enumerate(zip(x, alphas)):
        acc += a * (v - acc)
        y[i] = acc
    return y


def whoosh(seed: int = 0, seconds: float = 0.45) -> np.ndarray:
    n = int(RATE * seconds)
    sweep = np.linspace(0.02, 0.25, n) ** 1.2
    x = _lowpass(_noise(n, seed), sweep) * 3.0
    return x * _env(n, 0.55, 0.45)


def tick(seconds: float = 0.05) -> np.ndarray:
    n = int(RATE * seconds)
    t = np.arange(n) / RATE
    return np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 90)


def pop(seconds: float = 0.12) -> np.ndarray:
    n = int(RATE * seconds)
    t = np.arange(n) / RATE
    freq = 900 * np.exp(-t * 18) + 380
    return np.sin(2 * np.pi * np.cumsum(freq) / RATE) * np.exp(-t * 28)


def rise(seconds: float = 0.8) -> np.ndarray:
    n = int(RATE * seconds)
    t = np.arange(n) / RATE
    freq = 320 + 520 * (t / seconds) ** 1.6
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    tone = 0.6 * np.sin(phase) + 0.25 * np.sin(2 * phase)
    return tone * _env(n, 0.85, 0.15)


def shimmer(seconds: float = 0.6) -> np.ndarray:
    n = int(RATE * seconds)
    t = np.arange(n) / RATE
    tone = sum(np.sin(2 * np.pi * f * t) / (i + 1) for i, f in enumerate((1760, 2637, 3520)))
    return tone * _env(n, 0.2, 0.8) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t))


def scratch(seed: int = 3, seconds: float = 0.18) -> np.ndarray:
    n = int(RATE * seconds)
    return _lowpass(_noise(n, seed), 0.35) * 2.0 * _env(n, 0.1, 0.6)


def hit(seconds: float = 1.0) -> np.ndarray:
    n = int(RATE * seconds)
    t = np.arange(n) / RATE
    body = np.sin(2 * np.pi * (55 + 40 * np.exp(-t * 9)) * t) * np.exp(-t * 4)
    air = _lowpass(_noise(n, 7), 0.08) * np.exp(-t * 7) * 1.5
    return body + 0.4 * air


# Peak level of each sound relative to full scale (the voice sits near 0 dB
# after loudness normalisation, so these stay well underneath it).
LEVELS = {"whoosh": 0.16, "tick": 0.07, "pop": 0.11, "rise": 0.07,
          "shimmer": 0.05, "scratch": 0.12, "hit": 0.22}


def _emphasis_time(line: TimedLine) -> float | None:
    target = {w.lower().strip(".,!?;:'\"") for w in line.emphasis.split()}
    for word in line.words:
        if word.text.lower().strip(".,!?;:'\"") in target:
            return word.start
    return None


# Owner review 2026-10-05: the whooshes, ticks and swells on every change were
# distracting ("making noise"); only the ambient bed stays. Sounds listed here
# are the only ones rendered; empty means the effects track is silent.
ENABLED: frozenset[str] = frozenset()


def plan_events(groups: list[Group]) -> list[tuple[float, str]]:
    return [(at, kind) for at, kind in _all_events(groups) if kind in ENABLED]


def _all_events(groups: list[Group]) -> list[tuple[float, str]]:
    events: list[tuple[float, str]] = []
    for index, group in enumerate(groups):
        if index > 0:
            events.append((max(0.0, group.start - 0.18), "whoosh"))
        if group.visual.startswith("icon_"):
            events.append((group.start + 0.1, "shimmer"))
        elif group.visual in DATA_RISE:
            events.append((group.start + 0.05, "rise"))
        elif group.visual == "cross_out":
            events.append((group.start + 0.4, "scratch"))
        elif group.visual == "logo_end":
            events.append((group.start + 0.05, "hit"))
        for line in group.lines:
            at = _emphasis_time(line)
            if at is None:
                continue
            strong = line.section in {"claim", "reframe", "cta"}
            events.append((at, "pop" if strong else "tick"))
    return sorted(events)


SOUNDS = {"whoosh": whoosh, "tick": tick, "pop": pop, "rise": rise,
          "shimmer": shimmer, "scratch": scratch, "hit": hit}


def render_sfx(groups: list[Group], duration: float, output: Path) -> Path:
    track = np.zeros(int(RATE * (duration + 1.5)), dtype=np.float64)
    last: dict[str, float] = {}
    for at, kind in plan_events(groups):
        if kind in {"tick", "pop"} and at - last.get("tick", -9) < 1.2:
            continue  # keep accents sparse
        if kind in {"tick", "pop"}:
            last["tick"] = at
        sound = SOUNDS[kind]()
        sound = sound / (np.max(np.abs(sound)) or 1.0) * LEVELS[kind]
        start = int(max(0.0, at) * RATE)
        end = min(len(track), start + len(sound))
        track[start:end] += sound[: end - start]
    track = track[: int(RATE * duration)]
    pcm = np.clip(track, -1, 1)
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes((pcm * 32767).astype("<i2").tobytes())
    return output
