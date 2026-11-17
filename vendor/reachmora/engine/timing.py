"""Script -> sentences, and voiceover -> per-word / per-sentence timing.
Primary: sherpa-onnx Parakeet word timestamps aligned to the script text.
Fallback (no model): energy-based speech detection + syllable-proportional placement snapped to pauses."""
import json, os, re, subprocess, difflib
import numpy as np

SPLIT = re.compile(r"(?<=[.!?…])[\"”’)]*\s+")
ABBR = re.compile(r"\b(Mr|Mrs|Ms|Dr|St|vs|Jr|Sr|U\.S|e\.g|i\.e|No|Inc|Co|Mt)\.$", re.I)


def sentences(text):
    text = text.replace('\r', '')
    out = []
    for para in re.split(r"\n", text):
        para = para.strip()
        if not para or para.startswith('#'): continue
        parts = [s.strip() for s in SPLIT.split(para) if s.strip()]
        merged = []
        for p in parts:
            if merged and ABBR.search(merged[-1]): merged[-1] += " " + p
            else: merged.append(p)
        out += merged
    return out


def norm(w):
    w = w.lower().replace("’", "'")
    w = re.sub(r"[^a-z0-9']+", "", w)
    return w.strip("'")


def words_of(s): return [w for w in (norm(x) for x in s.split()) if w]


def syllables(w):
    w = norm(w)
    if not w: return 1
    if w.isdigit(): return max(1, len(w) * 2)
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith('e') and n > 1 and not w.endswith('le'): n -= 1
    return max(1, n)


def load_audio(path, sr=16000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def speech_mask(x, sr=16000, hop=0.01):
    n = int(sr * hop); m = len(x) // n
    e = np.sqrt(np.mean(x[:m * n].reshape(m, n) ** 2, axis=1) + 1e-12); db = 20 * np.log10(e)
    ref = np.percentile(db, 95); thr = max(ref - 32, np.percentile(db, 10) + 6)
    on = db > thr
    k = int(0.12 / hop)  # close short gaps < 120 ms
    idx = np.where(on)[0]
    if len(idx):
        gaps = np.diff(idx)
        for a, g in zip(idx[:-1], gaps):
            if 1 < g <= k: on[a:a + g] = True
    return on, hop


def find_model():
    cands = [os.environ.get("RM_ASR", ""), os.path.expanduser("~/models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"),
             os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8")]
    for c in cands:
        if c and os.path.exists(os.path.join(c, "encoder.int8.onnx")): return c
    return None


def asr_words(x, sr, model):
    import sherpa_onnx
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(encoder=f"{model}/encoder.int8.onnx", decoder=f"{model}/decoder.int8.onnx",
                                                        joiner=f"{model}/joiner.int8.onnx", tokens=f"{model}/tokens.txt",
                                                        num_threads=max(1, min(8, os.cpu_count() or 2)), model_type="nemo_transducer")
    on, hop = speech_mask(x, sr)
    # chunk at silences, ~20 s per chunk
    cuts = [0]; L = len(x) / sr; t = 0.0
    while t + 24 < L:
        lo, hi = int((t + 16) / hop), int(min(t + 24, L) / hop)
        seg = on[lo:hi]; off = np.where(~seg)[0]
        c_ = (lo + off[len(off) // 2]) * hop if len(off) else (t + 20)
        cuts.append(c_); t = c_
    cuts.append(L); words = []
    for a, b in zip(cuts, cuts[1:]):
        st = rec.create_stream(); st.accept_waveform(sr, x[int(a * sr):int(b * sr)]); rec.decode_stream(st); r = st.result
        cur = None
        for tok, ts in zip(r.tokens, r.timestamps):
            new = tok.startswith(" ") or tok.startswith("▁") or cur is None
            piece = tok.replace("▁", " ").strip()
            if not piece: continue
            if new:
                cur = [piece, a + ts]; words.append(cur)
            else:
                cur[0] += piece
    return [(norm(w), t) for w, t in words if norm(w)]


def align(script_sents, audio_path):
    x = load_audio(audio_path); sr = 16000; L = len(x) / sr
    on, hop = speech_mask(x, sr)
    sw = []  # (sentence idx, word)
    for i, s in enumerate(script_sents):
        for w in s.split():
            if norm(w): sw.append((i, w))
    model = find_model(); method = "asr"; times = [None] * len(sw)
    if model:
        aw = asr_words(x, sr, model)
        sm = difflib.SequenceMatcher(a=[norm(w) for _, w in sw], b=[w for w, _ in aw], autojunk=False)
        for blk in sm.get_matching_blocks():
            for k in range(blk.size): times[blk.a + k] = aw[blk.b + k][1]
        matched = sum(t is not None for t in times) / max(1, len(times))
        if matched < 0.35: method = "fallback"; times = [None] * len(sw)
    else:
        method = "fallback"; matched = 0.0
    if method == "fallback":
        # place words on speech time proportionally to syllables
        st = np.where(on)[0] * hop; syl = np.cumsum([0] + [syllables(w) for _, w in sw]); tot = syl[-1]
        for k in range(len(sw)):
            j = int(min(len(st) - 1, syl[k] / tot * len(st))); times[k] = float(st[j]) if len(st) else k * .35
    # interpolate gaps
    known = [k for k, t in enumerate(times) if t is not None]
    if not known: raise SystemExit("alignment failed: no words found")
    for k in range(len(times)):
        if times[k] is None:
            prev = max([j for j in known if j < k], default=None); nxt = min([j for j in known if j > k], default=None)
            if prev is None: times[k] = max(0.0, times[nxt] - .3 * (nxt - k))
            elif nxt is None: times[k] = times[prev] + .3 * (k - prev)
            else: times[k] = times[prev] + (times[nxt] - times[prev]) * (k - prev) / (nxt - prev)
    for k in range(1, len(times)): times[k] = max(times[k], times[k - 1])
    # sentence spans; end = end of speech run after the last word
    out = []
    for i, s in enumerate(script_sents):
        ks = [k for k, (si, _) in enumerate(sw) if si == i]
        if not ks: continue
        t0 = times[ks[0]]; tl = times[ks[-1]]
        j = int(tl / hop) + 5
        while j < len(on) and on[j]: j += 1
        t1 = min(L, j * hop + .05)
        nxt = times[ks[-1] + 1] if ks[-1] + 1 < len(times) else L
        t1 = max(tl + .15, min(t1, nxt - .02))
        out.append(dict(i=i, text=s, start=round(max(0, t0 - .06), 3), end=round(t1, 3),
                        words=[dict(w=sw[k][1], n=norm(sw[k][1]), t=round(times[k], 3)) for k in ks]))
    if method == "fallback":  # snap sentence starts to speech onsets near the estimate
        for s in out:
            j = int(s["start"] / hop)
            for d in range(0, 60):
                for jj in (j - d, j + d):
                    if 0 < jj < len(on) and on[jj] and not on[jj - 1]:
                        s["start"] = round(jj * hop - .04, 3); break
                else: continue
                break
    return dict(duration=round(L, 3), method=method, matched=round(matched, 3), sentences=out)
