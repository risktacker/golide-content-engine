"""Stickman Shorts: the cartoon-short-kit (vendor/cartoon-short-kit) used the way its skill (cartoon-audio-short,
Stage 4) builds a video: timing -> shot plan -> world -> cast -> motion -> look check -> sound -> render -> finish.

The engine sections of main.js, the Pen library (toon.ts), roman.js, paint.js, motion.js, the synths, finish.sh and
the look stay exactly as given. Per Short the model writes only what the skill says to rewrite for a new story:
- the world (main.js between "// ---------- world ----------" and "// ---------- cards ----------"),
- worldState (its story parts),
- story.js (SHOTS, cameras, lens, lights, world state, actors, effects),
- extra cast code (outfits / props in the same style, appended to roman.js),
- the sound cue table (audio.py; the synths stay).

What we add: the word timings come from our engine (the kit's timing.py output format, from the spoken words);
the look check is automatic (page errors, blank or frozen frames on stills at every shot) with one retry; the kit's
Node renderer is driven the same way from Python (same flags, same JPEG quality) so it runs where our engine runs;
mix.py, which the skill describes but the kit does not include, is written to the skill's exact numbers.
"""

from __future__ import annotations

import base64
import functools
import http.server
import json
import math
import re
import shutil
import subprocess
import sys
import threading
import wave
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
KIT = ROOT / "vendor" / "cartoon-short-kit"
SKILL = ROOT / "vendor" / "cartoon-short-kit" / "SKILL.md"
FPS = 30

WORLD_A, WORLD_B = "// ---------- world ----------", "// ---------- cards ----------"


# ---------------------------------------------------------------- timing (the kit's work/phrases.json format)
def phrases(words: list[dict[str, Any]], duration: float) -> dict[str, Any]:
    """words.json + phrases.json as tools/timing.py writes them on its whisper path (phrases end at punctuation)."""
    ws = [{"w": str(w["word"]).strip(), "s": round(float(w["start"]), 3), "e": round(float(w.get("end", w["start"])), 3)}
          for w in words if str(w.get("word", "")).strip()]
    phr, cur = [], []
    for w in ws:
        cur.append(w)
        if re.search(r"[,.;:!?]$", w["w"]):
            phr.append({"text": " ".join(x["w"] for x in cur), "s": cur[0]["s"], "e": cur[-1]["e"]})
            cur = []
    if cur:
        phr.append({"text": " ".join(x["w"] for x in cur), "s": cur[0]["s"], "e": cur[-1]["e"]})
    return {"words": ws, "phrases": {"duration": duration, "frames30": int(round(duration * FPS)),
                                      "source": "golide-word-timings", "segments": [], "phrases": phr}}


# ---------------------------------------------------------------- the writer
CODE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "plan_md": {"type": "string"},
        "world_js": {"type": "string"},
        "world_state_js": {"type": "string"},
        "story_js": {"type": "string"},
        "cast_js": {"type": "string"},
        "music_end": {"type": "number"},
        "cues_py": {"type": "string"},
    },
    "required": ["plan_md", "world_js", "world_state_js", "story_js", "cast_js", "music_end", "cues_py"],
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _skill_body() -> str:
    text = _read(SKILL)
    return text[text.find("## Rules"):]


def instructions() -> str:
    main = _read(KIT / "engine" / "main.js")
    return f"""You build one vertical animated cartoon Short with the cartoon-short-kit, exactly as its skill's Stage 4 says.
The voiceover is recorded; its phrase and word timings are given (30 fps; total frames given). Stages 1-3 (ideas,
script, recording) are done: the script is what the voice says. You write the parts the skill says to rewrite for a
new story, as code, and the engine sections stay as they are.

THE SKILL (follow it: rules, shot plan, world, cast, motion, look-check traps, sound):
{_skill_body()}

WHAT YOU RETURN (JSON):
- plan_md: work/PLAN.md, one row per shot (frames, words, setting, light, camera move, characters / poses /
  expressions, effects and SFX cue), written before the code, as 4.2 says.
- world_js: the code that replaces everything in main.js between the line "{WORLD_A}" and the line "{WORLD_B}"
  (both lines stay). Build the story's world there from primitives with painted textures (4.3). The fixed engine
  around it uses these names, so your world must define them: DECK (ground / deck height the cards stand on),
  waterU (an object with uniforms deep, shal, glint, t; define it even with no water: {{ t: {{value: 0}}, deep:
  {{value: new THREE.Color('#2f6f8f')}}, shal: {{value: new THREE.Color('#5fa8bf')}}, glint: {{value: new
  THREE.Color('#e9f6ff')}} }}), clouds (an array, may be the painted cloud billboards), and a function
  worldProps(W, f) the engine calls every frame after worldState (set props such as a lifted object from W; it may do
  nothing). Available there: THREE, T (toon.js), P (paint.js), scene, M (the material set), toon, texM, add, box,
  uvScale, tbox, rx, NOINK, waterNd, renderer, camera.
- world_state_js: the whole function `function worldState(S, f) {{ ... }}` (S = worldAt(f)): the story parts that
  drive set pieces from 0..1 progress; it must set waterU.t.value = f / 30.
- story_js: the whole web/story.js: export FPS, TOTAL (= total frames given), SHOTS, shotAt, camAt, dofAt, LIGHTS,
  lightFor, worldAt, actorsAt(f, T), fxAt(f, T), all pure functions of the frame. Import motion helpers with
  `import {{ M, camFromKeys, idle, blinkAt, walk, q, ramp, clamp, lerp, lerp3 }} from './motion.js';` when used.
  Characters are actors: the narrator speaks, nobody's mouth talks; they react, gesture, walk.
- cast_js: code appended after roman.js inside toon.js (same module scope as the Pen library and roman.js): add
  OUTFITS entries (Object.assign(OUTFITS, {{...}})), extra FACE expressions, props and fx drawers in the same style,
  and export any new drawing functions story.js calls through T. May be empty.
- music_end: the second the music bed stops (on the twist line, 4.7).
- cues_py: the story's cue table for audio.py: lines like `place(sfx, whoosh(0.6), F(18), 0.5)` using the synths
  thunk rumble crash cuckoo scrape ting sting creak snap splash whoosh snore leaves water, and F = frames to seconds.

Rules on top of the skill: real public figures in the story are generic cartoon characters (no likeness, never
named in diegetic text) and no brand logos; no captions; facts only as the script says them.

========================= THE ENGINE AND KIT CODE (read-only reference) =========================
--- engine/main.js (the worked example's world is between the markers) ---
{main}
--- engine/motion.js ---
{_read(KIT / "engine" / "motion.js")}
--- engine/paint.js ---
{_read(KIT / "engine" / "paint.js")}
--- engine/roman.js ---
{_read(KIT / "engine" / "roman.js")}
--- vendor/toon.ts (the Pen library; types are stripped before use) ---
{_read(KIT / "vendor" / "toon.ts")}
--- example/soldier/story.js (the worked example) ---
{_read(KIT / "example" / "soldier" / "story.js")}
--- example/soldier/audio.py (synths and the example cue table) ---
{_read(KIT / "example" / "soldier" / "audio.py")}"""


def request(title: str, timing: dict[str, Any], problems: str = "") -> str:
    p = timing["phrases"]
    rows = "\n".join(f"{x['s']:6.2f}-{x['e']:6.2f}  f{int(x['s'] * FPS):4d}-{int(x['e'] * FPS):4d}  {x['text']}" for x in p["phrases"])
    words = " ".join(f"{w['w']}@{w['s']:.2f}" for w in timing["words"])
    out = (f"TITLE: {title}\nDURATION: {p['duration']:.2f} s, TOTAL FRAMES: {p['frames30']}\n\nPHRASES:\n{rows}\n\n"
           f"WORDS (word@seconds): {words}\n")
    if problems:
        out += f"\nTHE LOOK CHECK FOUND THESE PROBLEMS IN YOUR LAST BUILD. Fix every one and send all the parts again:\n{problems}\n"
    return out


# ---------------------------------------------------------------- the project (tools/setup.sh, without network)
def _strip_types(ts: Path, out: Path) -> None:
    js = ("const m=require('node:module'),fs=require('fs');"
          f"fs.writeFileSync({json.dumps(str(out))},m.stripTypeScriptTypes(fs.readFileSync({json.dumps(str(ts))},'utf8'),{{mode:'transform'}}))")
    subprocess.run(["node", "-e", js], check=True, capture_output=True)


def splice(main: str, world_js: str, world_state_js: str) -> str:
    a, b = main.index(WORLD_A) + len(WORLD_A), main.index(WORLD_B)
    main = main[:a] + "\n" + world_js.strip() + "\n\n" + main[b:]
    s0 = main.index("function worldState(S, f) {")
    s1 = main.index("function drawActors(")
    main = main[:s0] + world_state_js.strip() + "\n\n" + main[s1:]
    h0 = main.index("const helmetState = (h) => {")
    h1 = main.index("const swapForNd")
    main = main[:h0] + main[h1:]
    return main.replace("helmetState(W_.helmet);", "worldProps(W_, f);")


def build_project(project: Path, parts: dict[str, Any], timing: dict[str, Any]) -> Path:
    web = project / "web"
    (web / "lib").mkdir(parents=True, exist_ok=True)
    for sub in ("work", "stills", "out", "frames"):
        (project / sub).mkdir(exist_ok=True)
    for f in ("motion.js", "paint.js", "roman.js", "index.html"):
        shutil.copy(KIT / "engine" / f, web / f)
    shutil.copy(KIT / "vendor" / "lib" / "three.module.js", web / "lib" / "three.module.js")
    if not (web / "toonbase.js").exists():     # toon.ts with its types stripped, as tools/setup.sh makes it
        shutil.copy(KIT / "vendor" / "toonbase.js", web / "toonbase.js")
    (web / "toon.js").write_text(_read(web / "toonbase.js") + "\n" + _read(web / "roman.js") + "\n"
                                 + str(parts.get("cast_js") or "") + "\n", encoding="utf-8")
    (web / "main.js").write_text(splice(_read(KIT / "engine" / "main.js"), parts["world_js"], parts["world_state_js"]),
                                 encoding="utf-8")
    (web / "story.js").write_text(parts["story_js"], encoding="utf-8")
    (project / "work" / "PLAN.md").write_text(str(parts.get("plan_md") or ""), encoding="utf-8")
    (project / "work" / "words.json").write_text(json.dumps(timing["words"], indent=1), encoding="utf-8")
    (project / "work" / "phrases.json").write_text(json.dumps(timing["phrases"], indent=1), encoding="utf-8")
    for f in ("finish.sh", "sheet.py"):
        shutil.copy(KIT / "tools" / f, project / f)
    (project / "audio.py").write_text(audio_py(parts, timing["phrases"]["frames30"]), encoding="utf-8")
    return project


# ---------------------------------------------------------------- driving the page (tools/render.mjs, from Python)
CHROMIUM_ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]


class _Quiet(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript"}

    def log_message(self, *args):  # noqa: D401
        pass


def frames(project: Path, frame_list: list[int], outdir: Path, quality: float = 0.96, resume: bool = True) -> list[str]:
    """What tools/render.mjs does: open web/index.html, wait for window.ready, renderFrame(f), save
    toDataURL('image/jpeg', q) as fNNNN.jpg. Returns page errors."""
    from playwright.sync_api import sync_playwright

    outdir.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(project / "web")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=CHROMIUM_ARGS)
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{server.server_address[1]}/index.html")
            page.wait_for_function("() => window.ready || window.err", timeout=180000)
            err = page.evaluate("() => window.err || null")
            if err or errors:
                return errors + ([err] if err else [])
            for f in frame_list:
                target = outdir / f"f{f:04d}.jpg"
                if resume and target.exists():
                    continue
                data = page.evaluate("([f, q]) => { window.renderFrame(f); return document.getElementById('c').toDataURL('image/jpeg', q); }",
                                     [f, quality])
                target.write_bytes(base64.b64decode(data.split(",", 1)[1]))
                if errors:
                    break
            browser.close()
    finally:
        server.shutdown()
    return errors


def shot_frames(project: Path) -> list[int]:
    """The middle of every shot plus the cuts between shots (4.6), read from story.js SHOTS."""
    text = _read(project / "web" / "story.js")
    spans = [(int(a), int(b)) for a, b in re.findall(r"\ba:\s*(\d+)\s*,\s*b:\s*(\d+)", text)]
    out = set()
    for a, b in spans:
        out |= {(a + b) // 2, min(b, a + 3)}
    return sorted(out)


def look_check(project: Path) -> tuple[list[Path], str]:
    """Stills at every shot's middle and just after each cut. Problems: page errors, a frame that is one flat colour,
    two shots in a row that render the same picture (the story did not move)."""
    from PIL import Image, ImageChops, ImageStat

    picks = shot_frames(project)
    if not picks:
        return [], "story.js has no SHOTS with a: and b: frame numbers"
    stills = project / "stills" / "check"
    if stills.exists():
        shutil.rmtree(stills)
    errors = frames(project, picks, stills, resume=False)
    if errors:
        return [], "The page threw errors:\n" + "\n".join(e[:600] for e in errors[:5])
    paths = [stills / f"f{f:04d}.jpg" for f in picks]
    problems = []
    images = [Image.open(p).convert("L").resize((108, 192)) for p in paths]
    for f, im in zip(picks, images):
        st = ImageStat.Stat(im)
        if st.stddev[0] < 8:
            problems.append(f"frame {f} is nearly one flat colour: the camera is inside or behind something, or nothing is lit")
    for (f0, a), (f1, b) in zip(zip(picks, images), list(zip(picks, images))[1:]):
        if ImageStat.Stat(ImageChops.difference(a, b)).mean[0] < 1.0:
            problems.append(f"frames {f0} and {f1} are the same picture: nothing moves between them")
    sheet = project / "stills" / "sheet.jpg"
    subprocess.run([sys.executable, str(project / "sheet.py"), str(stills), str(sheet)], check=False, capture_output=True)
    return paths, "\n".join(problems)


def render(project: Path, total: int, workers: int = 3) -> None:
    """All frames, split across browsers side by side (resumable, like RESUME=1)."""
    import os

    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT / "src"), os.environ.get("PYTHONPATH", "")]))
    chunks = [(k * total // workers, (k + 1) * total // workers - 1) for k in range(workers)]
    procs = [subprocess.Popen([sys.executable, "-m", "golide_engine.stickman.short", "frames", str(project), str(a), str(b)],
                              env=env) for a, b in chunks if b >= a]
    if any(p.wait() != 0 for p in procs):
        raise RuntimeError("a Stickman frame worker failed")
    missing = [f for f in range(total) if not (project / "frames" / f"f{f:04d}.jpg").exists()]
    if missing:
        raise RuntimeError(f"Stickman frames missing: {missing[:10]}")


# ---------------------------------------------------------------- sound (audio.py stems -> mix.py -> finish.sh)
def audio_py(parts: dict[str, Any], total: int) -> str:
    """The kit's audio.py with this story's cue table and music stop; it writes stems only (music.wav, sfx.wav), as
    the skill says. The synths are the example's, unchanged."""
    src = _read(KIT / "example" / "soldier" / "audio.py")
    head = src[:src.index("MUSIC_END = 14.15")]
    head = head.replace("DUR = 592 / 30", f"DUR = {total} / 30")
    body = src[src.index("bar = 0; tt = 0.0"):src.index("F = lambda f: f / 30")]
    stems = '''
def write(name, x):
    peak = float(np.max(np.abs(x))) or 1.0
    pcm = (np.clip(x / peak * 0.9, -1, 1) * 32767).astype(np.int16)
    with wave.open(name, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
write("music.wav", music); write("sfx.wav", sfx)
print("stems ok", N / SR)
'''
    return (head + f"MUSIC_END = {float(parts['music_end']):.2f}\n" + body + "F = lambda f: f / 30\n"
            + str(parts["cues_py"]).strip() + "\n" + stems)


def _read_wav(path: Path, sr: int = 48000):
    import numpy as np

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def gated_rms(x, sr: int = 48000, win: float = 0.4, gate_db: float = -40.0) -> float:
    """RMS over the parts that are actually sounding: 400 ms windows within 40 dB of the loudest."""
    import numpy as np

    n = int(win * sr)
    if len(x) < n:
        return float(np.sqrt(np.mean(x ** 2) + 1e-12))
    m = len(x) // n
    e = np.mean(x[:m * n].reshape(m, n) ** 2, axis=1)
    keep = e[e > e.max() * 10 ** (gate_db / 10)]
    return float(np.sqrt(np.mean(keep) + 1e-12))


def mix(project: Path, voice: Path) -> dict[str, float]:
    """mix.py as the skill specifies it: music at exactly 50 % of the voice's gated RMS (-6 dB), SFX at 50 % with
    peaks capped at 0.7x the voice peak, no ducking or compression; one linear gain plus a peak limiter on the whole
    mix. Writes mix_raw.wav (finish.sh takes it from there) and returns the measured levels."""
    import numpy as np

    sr = 48000
    v = _read_wav(voice, sr)
    mu = _read_wav(project / "music.wav", sr)
    fx = _read_wav(project / "sfx.wav", sr)
    n = len(v)
    mu, fx = (np.pad(a[:n], (0, max(0, n - len(a)))) for a in (mu, fx))
    rv = gated_rms(v)
    mu *= 0.5 * rv / max(gated_rms(mu), 1e-9)
    if np.abs(fx).max() > 0:
        fx *= min(0.5 * rv / max(gated_rms(fx), 1e-9), 0.7 * float(np.abs(v).max()) / float(np.abs(fx).max()))
    out = v + mu + fx
    peak = float(np.abs(out).max()) or 1.0
    out *= min(1.0, 0.98 / peak)                                    # one linear gain
    lim = 0.89
    over = np.abs(out) > lim                                         # peak limiter (soft knee above -1 dBFS)
    out[over] = np.sign(out[over]) * (lim + (1 - lim) * np.tanh((np.abs(out[over]) - lim) / (1 - lim)))
    pcm = (np.clip(out, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(project / "mix_raw.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
    db = lambda a: 20 * math.log10(max(a, 1e-9) / max(rv, 1e-9))
    levels = {"music_db_vs_voice": round(db(gated_rms(mu)), 2), "sfx_db_vs_voice": round(db(gated_rms(fx)), 2) if fx.any() else None}
    print(json.dumps({"status": "stickman_mix", **levels}))
    return levels


def finish(project: Path, voice: Path) -> Path:
    subprocess.run([sys.executable, "audio.py"], cwd=project, check=True, capture_output=True)
    mix(project, voice)
    result = subprocess.run(["bash", "finish.sh", "stickman"], cwd=project, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Stickman finish failed: {result.stderr[-1200:]}")
    print(json.dumps({"status": "stickman_qa", "report": result.stdout[-800:]}))
    return project / "out" / "stickman.mp4"


# ---------------------------------------------------------------- the whole Short
def make(text, project: Path, title: str, words: list[dict[str, Any]], duration: float, voice: Path,
         workers: int = 3, record=None) -> Path | None:
    """Write (one retry with the look check's problems), render and finish one Short. None when it failed twice."""
    timing = phrases(words, duration)
    total = timing["phrases"]["frames30"]
    problems = ""
    for attempt in (1, 2):
        out = text.generate_json(instructions(), request(title, timing, problems), CODE_SCHEMA, max_output_tokens=60000)
        if record:
            record(f"stickman-short-{attempt}", out)
        parts = out.value
        try:
            build_project(project, parts, timing)
            _, problems = look_check(project)        # a script that does not parse shows up as a page error here
        except Exception as error:  # noqa: BLE001 - a broken build goes back to the writer once (timeouts too)
            problems = str(error)[:1500]
        print(json.dumps({"status": "stickman_look_check", "attempt": attempt, "ok": not problems, "problems": problems[:300]}))
        if not problems:
            shutil.copy(voice, project / f"voice{voice.suffix.lower()}")
            render(project, total, workers)
            return finish(project, voice)
    return None


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "frames":
    _p, _a, _b = Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    errs = frames(_p, list(range(_a, _b + 1)), _p / "frames")
    if errs:
        print(json.dumps({"status": "stickman_frames_failed", "errors": errs[:3]}))
        raise SystemExit(1)
