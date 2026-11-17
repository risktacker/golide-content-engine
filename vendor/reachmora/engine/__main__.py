"""ReachMora 2D long-form engine CLI.  python3 -m engine <command> <project_dir> [options]

  sentences <P> [--minutes M]   number the sentences of P/script.txt (use these indices in story.json)
  join      <P> a.mp3 b.mp3 ..  join voiceover parts into P/voice.wav (0.45 s pauses)
  align     <P>                 voice.* + script.txt -> P/timing.json (word-level timing)
  plan      <P>                 check story.json against the timing; print the shot table
  stills    <P> [--shots 0,5,9] [--fracs .3,.7]   contact sheets in P/work/sheet_*.jpg
  render    <P> [--jobs N] [--shots ...] [--res 720]   render shot segments (resumable) + concat
            (--res 720 = fast 1280x720 draft/final; the default is 1920x1080. Use the same --res for final.)
  audio     <P> [--mood M]      music + SFX + mix + loudness -> P/work/mix.wav
  final     <P> [--title T]     mux -> P/out/<title>.mp4
  all       <P>                 align (if needed), plan, render, audio, final
"""
import json, os, sys, time

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); __package__ = "engine"


def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name); return sys.argv[i + 1]
    return default


def ints(s): return [int(x) for x in s.split(",")] if s else None


def main():
    if len(sys.argv) < 3: print(__doc__); return
    cmd, P = sys.argv[1], os.path.abspath(sys.argv[2])
    if arg("--res"): os.environ["RM_RES"] = arg("--res")  # must be set before the kit is imported (workers inherit it)
    from .timing import sentences, align
    if cmd == "join":  # join numbered voice parts into P/voice.wav with 0.45 s pauses
        import subprocess
        parts = sys.argv[3:]; lst = os.path.join(P, "parts.txt"); gap = os.path.join(P, "gap.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "0.45", gap], check=True)
        norm_ = []
        for i, p in enumerate(parts):
            q = os.path.join(P, f"part{i:02d}.wav"); subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-ac", "1", "-ar", "48000", q], check=True); norm_.append(q)
        with open(lst, "w") as fh:
            for i, q in enumerate(norm_): fh.write(("" if i == 0 else f"file '{gap}'\n") + f"file '{q}'\n")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, os.path.join(P, "voice.wav")], check=True)
        for q in norm_ + [gap, lst]: os.remove(q)
        print("joined", len(parts), "parts ->", os.path.join(P, "voice.wav")); return
    if cmd == "sentences":
        ss = sentences(open(os.path.join(P, "script.txt"), encoding="utf-8").read()); nw = sum(len(s.split()) for s in ss)
        for i, s in enumerate(ss): print(f"{i:3d}  {s}")
        print(f"\n{len(ss)} sentences, {nw} words, about {nw / 150:.1f} min at 150 wpm ({nw / 140:.1f}-{nw / 160:.1f} min)"); return
    if cmd in ("align", "all") and (cmd == "align" or not os.path.exists(os.path.join(P, "timing.json"))):
        from .render import voice_path
        ss = sentences(open(os.path.join(P, "script.txt"), encoding="utf-8").read()); t = time.time()
        T = align(ss, voice_path(P)); json.dump(T, open(os.path.join(P, "timing.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"aligned {len(T['sentences'])} sentences, {T['duration']:.1f} s of voice, method={T['method']} matched={T['matched']:.0%} ({time.time() - t:.0f}s)")
        if T["method"] == "fallback": print("WARNING: no speech model; timing is estimated from pauses. Check the plan carefully.")
        bad = [s for s in T["sentences"] if s["end"] - s["start"] < .25]
        if bad: print("very short sentences (check):", [s["i"] for s in bad])
        if cmd == "align": return
    if cmd in ("plan", "all"):
        from .render import load_project, whip_flags
        story, tl, cast = load_project(P); wh = whip_flags(tl)
        for s, w in zip(tl.shots, wh):
            sp = s["spec"]; rng_ = f"{s['sents'][0]}-{s['sents'][-1]}" if s["sents"] else "silent"
            print(f"#{s['k']:3d} {sp.get('kind', 'wide'):9s} {sp.get('set', ''):8s} {s['t0']:7.2f}-{s['t1']:7.2f} ({s['t1'] - s['t0']:4.1f}s) sents {rng_:9s}{' whip' if w else ''}")
        print(f"\n{len(tl.shots)} shots, {tl.duration / 60:.2f} min, {tl.total_frames} frames")
        for w in tl.warn: print("WARNING:", w)
        # build every shot once so cue warnings and bad params surface before rendering
        from .render import setup, _G
        from .shots import build
        setup(P); n0 = len(tl.warn)
        for s in _G["tl"].shots: build(s, _G["tl"], _G["cast"], _G["env"])
        for w in _G["tl"].warn[n0:]: print("WARNING:", w)
        if cmd == "plan": return
    if cmd == "stills":
        from .render import stills
        fr = [float(x) for x in arg("--fracs", ".5").split(",")]; stills(P, ints(arg("--shots")), fr); return
    if cmd in ("render", "all"):
        from .render import render_all
        j = arg("--jobs"); render_all(P, int(j) if j else None, ints(arg("--shots")))
        if cmd == "render": return
    if cmd in ("audio", "all"):
        from .audio import build, loudness
        raw = build(P, arg("--mood"), float(arg("--music-db", -17)), float(arg("--sfx-db", -9)))
        loudness(raw, os.path.join(P, "work", "mix.wav"))
        if cmd == "audio": return
    if cmd in ("final", "all"):
        from .audio import mux
        story = json.load(open(os.path.join(P, "story.json"), encoding="utf-8"))
        mux(P, arg("--title", story.get("title", "final"))); return
    if cmd not in ("all",): print(__doc__)


if __name__ == "__main__":
    main()
