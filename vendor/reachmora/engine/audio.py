"""Audio: the user's voice (unedited, only shifted for silent cards), an original synthesized music bed,
SFX placed from shot events, a level-locked mix and loudness to -14 LUFS."""
import json, os, re, subprocess
import numpy as np, soundfile as sf
from scipy.signal import butter, lfilter, sosfilt

SR = 48000
rng = np.random.default_rng(5)


def lp(x, fc, o=2): b, a = butter(o, fc / (SR / 2), 'low'); return lfilter(b, a, x)
def hp(x, fc, o=2): b, a = butter(o, fc / (SR / 2), 'high'); return lfilter(b, a, x)
def bp(x, f1, f2): b, a = butter(2, [f1 / (SR / 2), f2 / (SR / 2)], 'band'); return lfilter(b, a, x)
def hz(n): return 440 * 2 ** ((n - 69) / 12)


def place(buf, x, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i < 0: x = x[-i:]; i = 0
    if x.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4) * 1.414, np.sin((pan + 1) * np.pi / 4) * 1.414; x = np.stack([x * l, x * r], 1)
    j = min(i + len(x), len(buf))
    if i < len(buf): buf[i:j] += x[:j - i] * gain


# ---------------------------------------------------------------- instruments
def pluck(f, dur=0.34, amp=0.5, decay=10):
    n = int(dur * SR); t = np.arange(n) / SR; env = np.exp(-t * decay) * (1 - np.exp(-t * 500))
    return amp * env * (np.sin(2 * np.pi * f * t) + .5 * np.sin(4 * np.pi * f * t) + .22 * np.sin(6 * np.pi * f * t) + .1 * np.sin(8 * np.pi * f * t))
def bass(f, dur=0.42, amp=0.6):
    n = int(dur * SR); t = np.arange(n) / SR; env = np.exp(-t * 6) * (1 - np.exp(-t * 300))
    return amp * env * lp(np.sin(2 * np.pi * f * t) + .6 * np.sin(4 * np.pi * f * t) + .25 * np.sin(6 * np.pi * f * t), 900)
def vibes(f, dur=0.9, amp=0.2):
    n = int(dur * SR); t = np.arange(n) / SR; env = np.exp(-t * 4.5) * (1 - np.exp(-t * 900))
    return amp * env * (np.sin(2 * np.pi * f * t) + .3 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 14)) * (1 + .25 * np.sin(2 * np.pi * 5.5 * t))
def pad(freqs, dur, amp=0.05, lo=300, hi=3200, buzz=0.5):
    n = int(dur * SR); t = np.arange(n) / SR; out = np.zeros(n)
    for f in freqs:
        for d in (-1.8, 0, 2.1):
            ph = ((f + d) * t) % 1; out += (2 * ph - 1) + buzz * np.sign(np.sin(2 * np.pi * (f + d) * t))
    out = bp(out, lo, hi); env = np.minimum(1, t / .12) * np.minimum(1, (dur - t) / .2) * (1 + .12 * np.sin(2 * np.pi * 5 * t))
    return amp * out * env / len(freqs)
def brush(amp=0.06, dur=0.07):
    n = int(dur * SR); return amp * hp(rng.standard_normal(n), 5500) * np.exp(-np.arange(n) / SR * 55)
def kick(amp=0.4):
    n = int(.22 * SR); t = np.arange(n) / SR; return amp * np.sin(2 * np.pi * (48 + 70 * np.exp(-t * 34)) * t) * np.exp(-t * 15)
def snap(amp=.12):
    n = int(.12 * SR); t = np.arange(n) / SR; return amp * bp(rng.standard_normal(n), 1200, 6000) * np.exp(-t * 40)


# ---------------------------------------------------------------- moods (original progressions)
MOODS = {
    # bpm, chords [(root midi, [chord midi])], bass walk offsets, motifs, pad (lo, hi, buzz), drums
    "mystery": dict(bpm=104, prog=[(45, [57, 60, 64]), (41, [53, 57, 60]), (38, [50, 53, 57]), (40, [52, 56, 59])],
                    walk=[[0, 3, 7, 3], [0, 4, 7, 4], [0, 3, 7, 10], [0, 4, 7, 11]],
                    motifs=[[76, None, 75, 76, None, 72, None, None], [None, 69, None, 72, 71, None, 69, None], [77, None, 76, 74, None, 72, None, 74], [None, 71, 72, None, 76, None, 80, None]],
                    pad=(300, 3200, .5), drums="swing"),
    "upbeat": dict(bpm=112, prog=[(48, [60, 64, 67]), (43, [55, 59, 62]), (45, [57, 60, 64]), (41, [53, 57, 60])],
                   walk=[[0, 7, 12, 7], [0, 7, 12, 7], [0, 7, 12, 7], [0, 7, 12, 7]],
                   motifs=[[72, None, 76, None, 79, None, 76, None], [74, None, 79, None, 83, None, 79, 77], [76, None, 72, None, 69, None, 72, None], [77, 76, 74, None, 72, None, None, None]],
                   pad=(400, 4000, .2), drums="pop"),
    "dramatic": dict(bpm=84, prog=[(38, [50, 53, 57]), (46, [58, 62, 65]), (41, [53, 57, 60]), (45, [57, 61, 64])],
                     walk=[[0, 0, 12, 0], [0, 0, 12, 0], [0, 0, 12, 0], [0, 0, 12, 7]],
                     motifs=[[74, None, None, 72, None, None, 69, None], [None, None, 74, None, 77, None, None, None], [72, None, None, 69, None, None, 65, None], [None, None, 73, None, 76, None, 73, None]],
                     pad=(200, 2200, .2), drums="heavy"),
    "calm": dict(bpm=76, prog=[(41, [53, 57, 60, 64]), (43, [55, 59, 62, 65]), (45, [57, 60, 64, 67]), (38, [50, 53, 57, 60])],
                 walk=[[0, 7, 12, 7], [0, 7, 12, 7], [0, 7, 12, 7], [0, 7, 12, 7]],
                 motifs=[[72, None, 76, None, 79, None, 76, None], [74, None, 77, None, 81, None, 77, None], [76, None, 79, None, 83, None, 79, None], [72, None, 77, None, 81, None, 77, None]],
                 pad=(250, 2400, .1), drums="none"),
    "tense": dict(bpm=96, prog=[(40, [52, 55, 59]), (40, [52, 55, 60]), (41, [53, 56, 60]), (39, [51, 55, 58])],
                  walk=[[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                  motifs=[[None, 76, None, None, 75, None, None, None], [None, None, 79, None, None, 78, None, None], [None, 77, None, None, 76, None, None, None], [None, None, 75, None, 74, None, 71, None]],
                  pad=(180, 1800, .3), drums="pulse"),
}


def music_bed(L, mood, mutes):
    M = MOODS.get(mood, MOODS["mystery"]); beat = 60 / M["bpm"]; e8 = beat / 2; bar = 4 * beat
    out = np.zeros((int((L + 3) * SR), 2)); t = 0.0; bi = 0
    while t < L:
        sec = (bi // 8) % 6  # arrangement: every 8 bars change texture
        root, ch = M["prog"][bi % 4]; muted = any(a - bar * .5 < t < b - .1 for a, b in mutes)
        if not muted:
            lo, hi, bz = M["pad"]
            place(out, pad([hz(n) for n in ch], bar * .98, 0.05 if sec != 3 else .035, lo, hi, bz), t, 1.0, -0.2)
            if sec != 3:
                for i, off in enumerate(M["walk"][bi % 4]): place(out, bass(hz(root + off), beat * .95, .55), t + i * beat)
            if M["drums"] != "none" and sec not in (0, 3):
                for i in (1, 3): place(out, sum(pluck(hz(n + 12), .2, .16) for n in ch[:3]), t + i * beat, 1.0, 0.25)
            if (bi % 2 == 0 and sec in (1, 2, 4)) or sec == 5:
                mot = M["motifs"][(bi + sec) % 4]
                for i, n in enumerate(mot):
                    if n: place(out, vibes(hz(n), .8, .14), t + i * e8, 1.0, -0.3 + .08 * i)
            d = M["drums"]
            if d != "none" and sec not in (0, 3):
                for i in range(8): place(out, brush(.06 if i % 2 == 0 else .035), t + i * e8 + (0.03 if (i % 2 and d == "swing") else 0), 1.0, 0.3)
                for i in ((0, 2) if d in ("swing", "pop") else (0,) if d == "heavy" else (0, 1, 2, 3)): place(out, kick(.32 if d != "pulse" else .2), t + i * beat)
                if d == "pop":
                    for i in (1, 3): place(out, snap(.1), t + i * beat, 1.0, .1)
        t += bar; bi += 1
    return out


# ---------------------------------------------------------------- SFX
def whoosh(dur=0.5):
    n = int(dur * SR); x = rng.standard_normal(n); out = np.zeros(n); seg = 600
    for i in range(0, n, seg):
        u = i / n; fc = 350 + 5200 * np.sin(np.pi * u) ** 1.3; y = bp(x[i:i + seg], max(fc * .55, 120), min(fc * 1.6, 16000)); out[i:i + len(y)] = y
    return out * np.sin(np.pi * np.arange(n) / n) ** 2 * 1.3
def popfx(f0=340): n = int(.13 * SR); t = np.arange(n) / SR; return np.sin(2 * np.pi * (f0 + 900 * np.exp(-t * 42)) * t) * np.exp(-t * 34) * .6
def thud(big=True):
    n = int(.7 * SR); t = np.arange(n) / SR
    out = np.sin(2 * np.pi * (42 + 95 * np.exp(-t * 26)) * t) * np.exp(-t * 8) + lp(rng.standard_normal(n), 2800) * np.exp(-t * 38) * .7
    if big: out += hp(rng.standard_normal(n), 3500) * np.exp(-t * 7) * .22
    return out * .9
def tick(): n = int(.016 * SR); return hp(rng.standard_normal(n), 2800) * np.exp(-np.arange(n) / SR * 280) * .5
def step(): n = int(.09 * SR); t = np.arange(n) / SR; return lp(rng.standard_normal(n), 1400) * np.exp(-t * 60) * .8 + np.sin(2 * np.pi * 150 * t) * np.exp(-t * 50) * .5
def shutter():
    out = np.zeros(int(.45 * SR)); a = tick() * 2.2; out[:len(a)] += a; k = int(.07 * SR); out[k:k + len(a)] += a
    t = np.arange(len(out)) / SR; out += hp(rng.standard_normal(len(out)), 6000) * np.exp(-t * 12) * .12; return out
def scribble(dur=.42): n = int(dur * SR); t = np.arange(n) / SR; return bp(rng.standard_normal(n), 1400, 5200) * (0.5 + 0.5 * np.sin(2 * np.pi * 13 * t)) * .26
def boom(): n = int(1.6 * SR); t = np.arange(n) / SR; return np.sin(2 * np.pi * 36 * t) * np.exp(-t * 2.4) * .8 + lp(rng.standard_normal(n), 180) * np.exp(-t * 3) * .4
def ding(): n = int(.9 * SR); t = np.arange(n) / SR; return (np.sin(2 * np.pi * 2637 * t) + .5 * np.sin(2 * np.pi * 3951 * t)) * np.exp(-t * 7) * .25
def paper(): n = int(.35 * SR); t = np.arange(n) / SR; return bp(rng.standard_normal(n), 900, 7000) * np.sin(np.pi * t / .35) ** 2 * .35
def sting():
    out = np.zeros(int(1.8 * SR))
    for n, g in ((45, .3), (57, .25), (64, .22), (68, .18), (72, .15)): out += np.pad(vibes(hz(n), 1.6, g) + pluck(hz(n), 1.6, .2, 4), (0, int(.2 * SR)))[:len(out)]
    return out
SFX = dict(pop=lambda: popfx(rng.uniform(320, 440)), thud=thud, whoosh=lambda: whoosh(.45), tick=tick, shutter=shutter, scribble=scribble,
           boom=boom, ding=ding, paper=paper, step=step, sting=sting)


def build(P, mood=None, music_db=-17.0, sfx_db=-9.0):
    from .render import setup, _G, whip_flags
    from .shots import build as build_shot
    setup(P); tl = _G["tl"]; story = _G["story"]; mood = mood or story.get("mood", "mystery")
    from .render import voice_path
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", voice_path(P), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    vx = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)
    L = tl.duration; N = int(L * SR) + SR; voice = np.zeros((N, 2))
    for (a, b, o) in tl.voice_segments(): place(voice, vx[int(a * SR):int(b * SR)], o)
    mutes = [(s["t0"], s["t1"]) for s in tl.shots if s["silent"] and s["spec"].get("kind") == "title"]
    music = music_bed(L, mood, mutes)[:N]; sfx = np.zeros((N, 2)); whips = whip_flags(tl)
    for (a, b) in mutes: place(sfx, boom(), a, .6)
    for i, s in enumerate(tl.shots):
        if whips[i]: place(sfx, whoosh(.45), s["t1"] - .3, .45, rng.uniform(-.3, .3))
        if s["spec"].get("kind") == "title" and not s["silent"]: place(sfx, boom(), s["t0"], .4)
        shot = build_shot(s, tl, _G["cast"], _G["env"]) if True else None
        for name, t in shot.sfx_events():
            if name == "steps":
                walk_d = (s["t1"] - s["t0"]) if any(a.walk for a in shot.actors) else 1.1
                for k in range(int(walk_d / .285)): place(sfx, step(), t + .1 + k * .285, .35, -.4 + .03 * k)
            elif name == "tick":
                for k in range(18): place(sfx, tick(), t + .05 + k * .07, .35, .2)
            elif name in SFX: place(sfx, SFX[name](), t, .8 if name != "thud" else 1.0, rng.uniform(-.3, .3))
        if shot.pol: place(sfx, sting(), shot.pol["t"], .5)
    sfx += (lp(rng.standard_normal(N), 400) * 0.003)[:, None]
    # ---- level lock (gated RMS of the voice is the reference; the voice itself is untouched)
    vm = np.abs(voice).mean(1); env = lp(vm, 6, 1); gate = env > np.percentile(env[env > 0], 40) * .5 if (env > 0).any() else env > 0
    vref = np.sqrt(np.mean(voice[gate] ** 2)) if gate.any() else .1
    mref = np.sqrt(np.mean(music[np.abs(music).mean(1) > 1e-5] ** 2)) + 1e-9
    music *= vref * 10 ** (music_db / 20) / mref
    speech = np.clip(env / (np.percentile(env[gate], 50) + 1e-9), 0, 1) if gate.any() else np.zeros(N)
    duck = 1 - .45 * lp(speech, 3, 1).clip(0, 1); music *= duck[:, None]
    tt = np.arange(N) / SR; music *= np.minimum(1, tt / .4)[:, None] * np.clip((L - .2 - tt) / 1.2, 0, 1)[:, None]
    srms = np.sqrt(np.mean(sfx[np.abs(sfx).mean(1) > 1e-3] ** 2)) + 1e-9 if (np.abs(sfx).mean(1) > 1e-3).any() else 1.0
    sfx *= vref * 10 ** (sfx_db / 20) / srms; vpk = np.abs(voice).max() + 1e-9; spk = np.abs(sfx).max()
    if spk > .7 * vpk: sfx *= .7 * vpk / spk
    mix = voice + music + sfx
    os.makedirs(os.path.join(P, "work"), exist_ok=True); rawp = os.path.join(P, "work", "mix_raw.wav"); sf.write(rawp, mix[:int(L * SR)].astype(np.float32), SR)
    for nm, x in (("voice", voice), ("music", music), ("sfx", sfx)): sf.write(os.path.join(P, "work", f"stem_{nm}.wav"), x[:int(L * SR)].astype(np.float32), SR)
    db = lambda x: 20 * np.log10(np.sqrt(np.mean(x[gate] ** 2)) + 1e-12)
    print(f"levels in speech: voice {db(voice):.1f} dBFS, music {db(music) - db(voice):+.1f} dB, sfx peak {20 * np.log10(np.abs(sfx).max() / vpk + 1e-9):+.1f} dB vs voice peak")
    return rawp


def loudness(src, dst, target=-14.0):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr)
    if not m: raise SystemExit("loudness measurement failed:\n" + r.stderr[-800:])
    js = json.loads(m[-1]); gain = target - float(js["input_i"])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false", "-ar", str(SR), dst], check=True)
    print(f"loudness: input {js['input_i']} LUFS -> gain {gain:+.1f} dB"); return dst


def mux(P, title="final"):
    v = os.path.join(P, "work", "video.mp4"); a = os.path.join(P, "work", "mix.wav")
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", title).strip("_") or "final"; os.makedirs(os.path.join(P, "out"), exist_ok=True)
    if os.environ.get("RM_RES", "1080") != "1080": safe += f"_{os.environ['RM_RES']}p"
    out = os.path.join(P, "out", f"{safe}.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", v, "-i", a, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out], check=True)
    print("final ->", out); return out
