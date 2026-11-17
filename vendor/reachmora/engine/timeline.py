"""story.json + timing.json -> shot times on the output clock.
Spoken shots cover sentence ranges; a shot with no "s" is silent and inserts a pause (default 1.6 s)
into the timeline at that cut (the voice itself is never edited, only shifted)."""
import json, math
from .kit import FPS
from .timing import norm

TAIL = 1.0


def fr(t): return round(t * FPS) / FPS


def srange(sh):
    s = sh.get("s")
    if s is None: return None
    if isinstance(s, int): return (s, s)
    return (s[0], s[-1])


class Timeline:
    def __init__(self, story, timing):
        self.story = story; self.T = timing; self.S = {s["i"]: s for s in timing["sentences"]}
        self.warn = []; shots = story["shots"]; n = len(timing["sentences"]); exp = 0
        for k, sh in enumerate(shots):
            r = srange(sh)
            if r is None: continue
            if r[0] != exp: self.warn.append(f"shot {k}: starts at sentence {r[0]}, expected {exp}")
            exp = r[1] + 1
        if exp != n: self.warn.append(f"shots cover sentences up to {exp - 1}, script has {n - 1}")
        # cut points (voice clock) before each spoken shot
        spoken = [k for k, sh in enumerate(shots) if srange(sh)]
        cut = {}
        for j, k in enumerate(spoken):
            a = srange(shots[k])[0]
            if j == 0 or a not in self.S or (a - 1) not in self.S: cut[k] = 0.0 if j == 0 else self.S.get(a, {"start": 0})["start"] - .2; continue
            e = self.S[a - 1]["end"]; s0 = self.S[a]["start"]
            cut[k] = s0 - .03 if s0 - e < .1 else max((e + s0) / 2, s0 - .35)
        # walk shots, accumulate gaps
        self.shots = []; self.gaps = []; G = 0.0; vcur = 0.0
        for k, sh in enumerate(shots):
            r = srange(sh)
            if r is None:
                d = fr(float(sh.get("hold", 1.6))); t0 = vcur + G
                self.gaps.append((vcur, d)); G += d
                self.shots.append(dict(k=k, spec=sh, t0=t0, t1=t0 + d, sents=[], silent=True)); continue
            v0 = cut[k]; nxt = next((cut[j] for j in spoken if j > k), None)
            v1 = nxt if nxt is not None else timing["duration"] + TAIL
            self.shots.append(dict(k=k, spec=sh, t0=v0 + G, t1=None, v1=v1, sents=list(range(r[0], r[1] + 1)), silent=False)); vcur = v1
        for i, s in enumerate(self.shots):
            if s["t1"] is None:
                s["t1"] = self.shots[i + 1]["t0"] if i + 1 < len(self.shots) else s["v1"] + G_after(self.gaps, s["v1"])
        for i, s in enumerate(self.shots):
            s["f0"] = round(s["t0"] * FPS); s["f1"] = round(s["t1"] * FPS)
            if i: s["f0"] = self.shots[i - 1]["f1"]
            if s["f1"] - s["f0"] < 6: self.warn.append(f"shot {s['k']} is only {s['f1'] - s['f0']} frames")
        self.total_frames = self.shots[-1]["f1"]; self.duration = self.total_frames / FPS

    def out(self, v):  # voice time -> output time
        return v + G_after(self.gaps, v)

    def sent_span(self, i):
        s = self.S[i]; return self.out(s["start"]), self.out(s["end"])

    def cue(self, shot, at, default=0.0):
        """at: word/phrase from the shot's sentences, a fraction 0-1 of the shot, '+1.5' seconds after start, or None."""
        t0, t1 = shot["t0"], shot["t1"]
        if at is None: return t0 + default
        if isinstance(at, (int, float)): return t0 + (t1 - t0) * float(at) if at <= 1 else t0 + float(at)
        if isinstance(at, str) and at.startswith("+"): return t0 + float(at[1:])
        target = [norm(w) for w in str(at).split() if norm(w)]
        for si in shot["sents"]:
            ws = self.S[si]["words"]
            for j in range(len(ws) - len(target) + 1):
                if [w["n"] for w in ws[j:j + len(target)]] == target: return self.out(ws[j]["t"])
        for si in shot["sents"]:  # loose: prefix match on first word
            for w in self.S[si]["words"]:
                if target and w["n"].startswith(target[0][:5]): return self.out(w["t"])
        self.warn.append(f"shot {shot['k']}: cue '{at}' not found in its sentences, using 40%")
        return t0 + (t1 - t0) * .4

    def talk_spans(self, shot, talk):
        if not talk: return []
        ids = shot["sents"] if talk is True else [i for i in talk if i in self.S]
        return [self.sent_span(i) for i in ids]

    def voice_segments(self):
        """[(voice_a, voice_b, out_start)] pieces of the voice between inserted pauses."""
        segs = []; a = 0.0
        for (v, d) in self.gaps:
            if v > a: segs.append((a, v, self.out(a)))
            a = v
        segs.append((a, self.T["duration"], self.out(a) if a > 0 else G_after(self.gaps, 0.0)))
        return segs


def G_after(gaps, v):
    return sum(d for (g, d) in gaps if g <= v + 1e-9)
