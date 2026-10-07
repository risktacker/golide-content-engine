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


# --------------------------------------------------------------------------
# Action sounds (owner request 2026-10-07): a sound only when the line
# describes that action, timed to the word. All synthesised here.
# --------------------------------------------------------------------------

def _t(seconds: float) -> np.ndarray:
    return np.arange(int(RATE * seconds)) / RATE


def _bell(freq: float, seconds: float, decay: float, partials=((1, 1.0), (2.76, 0.45), (5.4, 0.22))) -> np.ndarray:
    t = _t(seconds)
    tone = sum(a * np.sin(2 * np.pi * freq * m * t) * np.exp(-t * decay * (1 + 0.6 * i))
               for i, (m, a) in enumerate(partials))
    return tone * np.clip(t / 0.004, 0, 1)


def _place(track: np.ndarray, sound: np.ndarray, at: float) -> None:
    start = int(max(0.0, at) * RATE)
    end = min(len(track), start + len(sound))
    if end > start:
        track[start:end] += sound[: end - start]


def bling(seconds: float = 0.9) -> np.ndarray:
    """Something lights up: two bright bell notes and a little sparkle."""
    out = np.zeros(int(RATE * seconds))
    _place(out, _bell(1568, seconds, 5.5), 0.0)
    _place(out, _bell(2349, seconds - 0.06, 6.5) * 0.8, 0.06)
    sparkle = _lowpass(_noise(int(RATE * 0.35), 11), 0.9) * np.exp(-_t(0.35) * 14) * 0.12
    _place(out, sparkle * np.sin(2 * np.pi * 7000 * _t(0.35)), 0.02)
    return out


def chime(seconds: float = 1.4) -> np.ndarray:
    return _bell(1046.5, seconds, 2.6) + 0.5 * _bell(1568, seconds, 3.2)


def phone_ring(seconds: float = 1.3) -> np.ndarray:
    """A phone ringing: two short trilled bursts."""
    out = np.zeros(int(RATE * seconds))
    for at in (0.0, 0.55):
        t = _t(0.42)
        trill = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 18 * t))
        tone = (np.sin(2 * np.pi * 1250 * t) + 0.6 * np.sin(2 * np.pi * 1560 * t)) * trill
        _place(out, tone * np.clip(t / 0.01, 0, 1) * np.clip((0.42 - t) / 0.03, 0, 1), at)
    return out


def notify(seconds: float = 0.7) -> np.ndarray:
    out = np.zeros(int(RATE * seconds))
    _place(out, _bell(1318.5, 0.5, 9, ((1, 1.0), (3.0, 0.2))), 0.0)
    _place(out, _bell(1975.5, 0.55, 8, ((1, 1.0), (3.0, 0.2))), 0.11)
    return out


def door_open(seconds: float = 0.9) -> np.ndarray:
    """Latch click, then a short soft creak."""
    t = _t(seconds)
    jitter = _lowpass(_noise(len(t), 21), 0.002) * 40
    pitch = 150 + 110 * (t / seconds) + jitter
    saw = 2 * ((np.cumsum(pitch) / RATE) % 1.0) - 1
    creak = _lowpass(saw * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 23 * t))), 0.25)
    creak *= np.clip((t - 0.08) / 0.1, 0, 1) * np.clip((seconds - t) / 0.3, 0, 1) * 0.5
    click = np.zeros_like(t)
    _place(click, _lowpass(_noise(int(RATE * 0.03), 4), 0.6) * np.exp(-_t(0.03) * 120), 0.0)
    return creak + click


def door_shut(seconds: float = 0.7) -> np.ndarray:
    """A low thump with a latch: something closed or blocked."""
    t = _t(seconds)
    body = np.sin(2 * np.pi * (48 + 30 * np.exp(-t * 20)) * t) * np.exp(-t * 9)
    knock = _lowpass(_noise(len(t), 5), 0.15) * np.exp(-t * 30) * 0.8
    latch = np.zeros_like(t)
    _place(latch, _noise(int(RATE * 0.02), 6) * np.exp(-_t(0.02) * 200) * 0.4, 0.05)
    return body + knock + latch


def car(seconds: float = 1.8) -> np.ndarray:
    """A car passing by: engine and road noise swelling, then the pitch drops."""
    t = _t(seconds)
    x = (t / seconds - 0.5) * 2  # -1 .. 1, closest at the middle
    pitch = 95 * (1 + 0.12 * np.tanh(-x * 3))
    phase = np.cumsum(pitch) / RATE
    engine = sum(np.sin(2 * np.pi * phase * h) / h for h in range(1, 6))
    road = _lowpass(_noise(len(t), 9), 0.08) * 1.5
    level = 1 / (1 + 6 * x * x)
    return (0.6 * engine + road) * level


def blips(seconds: float = 0.6) -> np.ndarray:
    """'tu-tu-tu-tu': a computer or AI at work."""
    out = np.zeros(int(RATE * seconds))
    rng = np.random.default_rng(3)
    for k in range(6):
        t = _t(0.045)
        freq = float(rng.choice((1100, 1320, 1480, 1760)))
        tone = np.sign(np.sin(2 * np.pi * freq * t)) * 0.5 + 0.5 * np.sin(2 * np.pi * freq * t)
        _place(out, _lowpass(tone, 0.35) * np.clip((0.045 - t) / 0.01, 0, 1), k * 0.085)
    return out


def coin(seconds: float = 0.6) -> np.ndarray:
    out = np.zeros(int(RATE * seconds))
    _place(out, _bell(987.8, 0.12, 25, ((1, 1.0), (2, 0.3))), 0.0)
    _place(out, _bell(1318.5, 0.5, 7, ((1, 1.0), (2, 0.3), (3, 0.1))), 0.08)
    return out


def typing(seconds: float = 0.9) -> np.ndarray:
    out = np.zeros(int(RATE * seconds))
    rng = np.random.default_rng(8)
    at = 0.0
    while at < seconds - 0.05:
        n = int(RATE * 0.025)
        click = _lowpass(_noise(n, int(at * 1000)), 0.5) * np.exp(-_t(0.025) * 160)
        _place(out, click * rng.uniform(0.6, 1.0), at)
        at += float(rng.uniform(0.06, 0.13))
    return out


def clock(seconds: float = 2.0) -> np.ndarray:
    out = np.zeros(int(RATE * seconds))
    for k, at in enumerate(np.arange(0.0, seconds - 0.1, 0.5)):
        _place(out, _bell(2600 if k % 2 == 0 else 2000, 0.05, 90, ((1, 1.0),)), float(at))
    return out


def camera(seconds: float = 0.25) -> np.ndarray:
    out = np.zeros(int(RATE * seconds))
    for at in (0.0, 0.07):
        _place(out, _lowpass(_noise(int(RATE * 0.03), 2), 0.5) * np.exp(-_t(0.03) * 110), at)
    return out


ACTION_SOUNDS = {"bling": bling, "chime": chime, "phone_ring": phone_ring, "notify": notify,
                 "door_open": door_open, "door_shut": door_shut, "car": car, "blips": blips,
                 "coin": coin, "typing": typing, "clock": clock, "camera": camera}
ACTION_LEVELS = {"bling": 0.07, "chime": 0.06, "phone_ring": 0.07, "notify": 0.07, "door_open": 0.08,
                 "door_shut": 0.10, "car": 0.08, "blips": 0.06, "coin": 0.07, "typing": 0.07,
                 "clock": 0.06, "camera": 0.08}

# Fallback when a plan carries no sound cues: words that name an action.
ACTION_WORDS = {
    "phone_ring": ("call", "calls", "calling", "ring", "rings", "ringing"),
    "notify": ("notification", "notifications", "message", "messages", "text", "alert", "email", "ping"),
    "door_shut": ("blocked", "blocks", "shut", "shuts", "closed", "locked", "banned", "rejected"),
    "door_open": ("open", "opens", "opened", "unlock", "unlocks", "enter", "enters", "door"),
    "car": ("car", "cars", "drive", "drives", "driving", "road", "truck", "traffic"),
    "coin": ("pay", "pays", "paid", "money", "price", "cash", "dollars", "buy", "buys", "sale", "checkout"),
    "blips": ("ai", "robot", "agent", "algorithm", "computer", "scan", "scans", "searches", "loading"),
    "typing": ("type", "types", "typing", "keyboard", "prompt", "prompts"),
    "clock": ("clock", "minutes", "hours", "deadline", "waiting", "wait"),
    "camera": ("photo", "photos", "camera", "picture", "selfie"),
    "bling": ("lights", "light", "idea", "shine", "shines", "glow", "spark", "wins", "win"),
}
COOLDOWN = 3.0  # seconds between action sounds, so they stay special


def _word(text: str) -> str:
    return text.lower().strip(".,!?;:'\"")


def action_cues(lines: list[TimedLine], scenes: list[dict], fade_lights: list[float] | None = None,
                follow: tuple[float, float] | None = None) -> list[tuple[float, str]]:
    """When each action sound plays.

    * Scene cues from the storyboard ("sound" + "sound_word"), timed to that word.
    * Plans without cues: the first word in a scene that names an action.
    * A soft bling when a faded-in picture's accent lights up, if that scene has
      no other sound.
    * The follow pill: a bling as it appears and a chime when it turns to the check.
    """
    cues: list[tuple[float, str]] = []
    by_index = {line.index: line for line in lines}
    for scene in scenes:
        first, last = int(scene.get("first_line", 0)), int(scene.get("last_line", -1))
        words = [w for i in range(first, last + 1) if i in by_index for w in by_index[i].words]
        kind = scene.get("sound")
        at = None
        if kind and kind != "none" and kind in ACTION_SOUNDS:
            target = _word(str(scene.get("sound_word", "")))
            at = next((w.start for w in words if target and _word(w.text) == target), None)
            if at is None and first in by_index:
                at = by_index[first].start + 0.4
        elif "sound" not in scene:
            for w in words:
                hit = next((name for name, keys in ACTION_WORDS.items() if _word(w.text) in keys), None)
                if hit:
                    kind, at = hit, w.start
                    break
        if at is not None and kind:
            cues.append((at, kind))
    taken = [at for at, _ in cues]
    for at in fade_lights or []:
        if all(abs(at - other) > COOLDOWN for other in taken):
            cues.append((at, "bling"))
    cues.sort()
    kept: list[tuple[float, str]] = []
    for at, kind in cues:
        if kept and at - kept[-1][0] < COOLDOWN:
            continue
        kept.append((at, kind))
    if follow is not None:
        kept = [c for c in kept if not (follow[0] - 0.5 <= c[0] <= follow[1] + 1.0)]
        kept += [(follow[0], "bling"), (follow[1], "chime")]
    return sorted(kept)


# Peak level of each sound relative to full scale (the voice sits near 0 dB
# after loudness normalisation, so these stay well underneath it).
LEVELS = {"whoosh": 0.07, "tick": 0.07, "pop": 0.11, "rise": 0.07,
          "shimmer": 0.05, "scratch": 0.12, "hit": 0.12}


def _emphasis_time(line: TimedLine) -> float | None:
    target = {w.lower().strip(".,!?;:'\"") for w in line.emphasis.split()}
    for word in line.words:
        if word.text.lower().strip(".,!?;:'\"") in target:
            return word.start
    return None


# Owner review 2026-10-05: the whooshes, ticks and swells on every change were
# distracting ("making noise"); only the ambient bed stays. Sounds listed here
# are the only ones rendered; empty means the effects track is silent.
# Second review: keep only sounds that mark a real moment, soft, under the
# bed: a gentle whoosh when a new illustration scene begins and the closing
# hit. No ticks, pops, swells or scratches.
ENABLED: frozenset[str] = frozenset({"whoosh", "hit"})


def plan_events(groups: list[Group]) -> list[tuple[float, str]]:
    return [(at, kind) for at, kind in _all_events(groups) if kind in ENABLED]


def _all_events(groups: list[Group]) -> list[tuple[float, str]]:
    events: list[tuple[float, str]] = []
    for index, group in enumerate(groups):
        # Only real scene changes (a new illustration), not every line.
        if index > 0 and group.visual in {"illustration", "logo_end"}:
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


def render_sfx(groups: list[Group], duration: float, output: Path,
               cues: list[tuple[float, str]] | None = None) -> Path:
    track = np.zeros(int(RATE * (duration + 2.5)), dtype=np.float64)
    for at, kind in cues or []:
        sound = ACTION_SOUNDS[kind]()
        _place(track, sound / (np.max(np.abs(sound)) or 1.0) * ACTION_LEVELS[kind], at)
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
