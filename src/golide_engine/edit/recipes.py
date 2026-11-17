"""Recipe scenes (owner 2026-11-17): Futurepedia's 3D style recipes (assets/styles/futurepedia/*.txt), each a
complete three.js stage kit plus a reference scene, used the way they are meant to be used: for a beat that fits the
style, a model writes a NEW scene for that beat's content from the recipe ("rebuild the animation around my
content"), the engine checks it on three stills, renders it as a clip and the clip goes into the video at that beat.

The kit (assets/recipes/stage.js) and the reference scenes are copied unchanged. Our own rules on top: the scene is
one narrated beat (no title card, callouts only, events on the spoken words), sized for the frame it fills, and
one accent colour picked for the object or brand. A scene that fails its check twice is replaced by the house 3D.
"""

from __future__ import annotations

import base64
import functools
import http.server
import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
KIT = ROOT / "assets" / "recipes"
BOOK = ROOT / "assets" / "styles" / "futurepedia"

# the recipes wired in so far; one at a time, each checked against its own reference before the next
RECIPES: dict[str, dict[str, str]] = {
    "xray": {
        "file": "x-ray.txt", "name": "X-Ray",
        "fits": "what is INSIDE a real thing and how it works (a chip, a battery, a phone, an engine, a data-centre "
                "rack, a body part): up to three inner parts, each lit and named in turn, with a simple flow (heat, "
                "air, current, data, force) shown acting on them",
    },
}

CODE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "code": {"type": "string"},
        "accent": {"type": "string"},
        "events": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
            "t": {"type": "number"}, "what": {"type": "string", "enum": ["start", "scan", "part", "flow", "result"]},
            "label": {"type": "string"}}, "required": ["t", "what", "label"]}},
    },
    "required": ["code", "accent", "events"],
}

FRAME = {"long": (1600, 900), "short": (1000, 1000)}


def _section(text: str, start: str, end: str | None) -> str:
    a = text.find(start)
    if a < 0:
        return ""
    b = text.find(end, a + len(start)) if end else -1
    return text[a:b if b > 0 else len(text)].strip()


def recipe_text(key: str) -> str:
    """The parts of the recipe the writer follows, unchanged: its style rules, the style card, the stage kit and
    the reference scene. Left out: its storyboard and player steps (the engine does those) and its sound kit (the
    video has its own sound)."""
    text = (BOOK / RECIPES[key]["file"]).read_text(encoding="utf-8")
    rules = _section(text, "HOW TO STAY IN THE STYLE", "SOUND (")
    card_and_kit = _section(text, "STYLE CARD", "SOUND KIT (")
    reference = _section(text, "REFERENCE STYLE SOURCE", None)
    return "\n\n".join([rules, card_and_kit, reference])


def instructions(key: str) -> str:
    r = RECIPES[key]
    return f"""You write ONE scene of a GOLIDE video in the "{r['name']}" style, from the recipe below: its style rules,
style card, the stage kit it runs on and a complete reference scene. Follow the recipe's rules exactly: keep the
reference's materials, lighting, camera language, grade and the way things move; change the story, the objects
and the words to the content you are given; never reuse the reference's object (the reference shows the look, not
the story).

WHAT YOU WRITE
- One JavaScript block built exactly like the reference: `{{ content constants...; registerStyle({{ id, name, duration,
  fonts, render, build(S) {{ ... return {{ update(t), overlay(ctx, t, W, H) }} }} }}); }}`. A classic script: THREE, K and
  registerStyle are globals; no import, no fetch, no Math.random, Date or timers (use K.rng(seed)); build everything
  in code (no files, models, images or textures).
- duration = the scene length you are given, exactly. The frame is the size you are given: read S.W and S.H, scale
  every overlay size by H / 1080 like the reference, and frame the camera for that shape (it may be square).
- render: keep the reference's tone, exposure, bloom, vignette, grain, fov and background. samples is set by the
  engine.
- update(t) sets the WHOLE scene for time t; nothing builds up between calls (the kit renders each frame many times).

THIS SCENE IS ONE BEAT OF A NARRATED VIDEO
- The host's voice is already saying the words you are given and captions show them under the picture. So: NO
  title, overline or headline card. Labels are callouts only (a NAME of 1-3 words and a note of 2-5 words, both from
  what is said), at most 3, each appearing as its part lights up.
- Land every event on its spoken word, using the word times you are given (seconds from the start of this scene):
  the effect starting, each part lighting up, the flow arriving, the result.
- The first frame already shows the object (never an empty frame); the last half second holds the result.
- Everything that matters stays inside the frame with a 6% margin through the whole camera move; labels never cover
  each other or the part they name; text large enough to read on a phone.
- Colour: keep the style's palette rule. Set ACCENT to fit the object or brand in the story (e.g. Nvidia green for an
  Nvidia chip, a warning orange for a battery fire); still ONE accent. Before the effect, draw the object in its real
  materials and colours.
- Draw the subject accurately (real proportions, the parts the words name); simple forms beautifully lit beat
  complicated models that look wrong. Only facts from the words and brief you are given.
- No sound() is needed: the video has its own sound. Instead return `events`: every moment something lands (t in
  seconds, what, label).

Return JSON: code (the block), accent (#rrggbb), events.

========================= THE RECIPE =========================
{recipe_text(key)}"""


def request(key: str, brief: str, words: list[dict[str, Any]], duration: float, size: tuple[int, int],
            problems: str = "") -> str:
    said = " ".join(f"{w['text']}@{w['t']:.2f}" for w in words)
    out = (f"STYLE: {RECIPES[key]['name']}\nSCENE LENGTH: {duration:.2f} s\nFRAME: {size[0]}x{size[1]} px\n"
           f"WHAT TO SHOW: {brief}\nWHAT THE VOICE SAYS (word@seconds from the scene start): {said}\n")
    if problems:
        out += f"\nYOUR LAST VERSION FAILED ITS CHECK. Fix this and send the whole block again:\n{problems}\n"
    return out


# ---------------------------------------------------------------- running a scene in headless Chromium
CHROMIUM_ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]


def stage_folder(code: str, folder: Path) -> Path:
    """A folder the player can run from: the player, the kit, three.js 0.187.0, the fonts and the written scene."""
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("player.html", "stage.js"):
        shutil.copy(KIT / name, folder / name)
    for sub in ("three", "fonts"):
        shutil.copytree(KIT / sub, folder / sub, dirs_exist_ok=True)
    (folder / "style.js").write_text(code, encoding="utf-8")
    return folder


class _Quiet(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript"}

    def log_message(self, *args):  # noqa: D401
        pass


def _serve(folder: Path):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(folder)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def frames(folder: Path, size: tuple[int, int], samples: int, times: list[float], out: Path,
           timeout_ms: int = 180000, boxes: list | None = None) -> list[str]:
    """Render the scene at the given times into out/NNNNN.jpg (numbered by position in `times`). Returns the page's
    errors (empty when it ran clean). `boxes`, when given, gets the words written on screen at each time with their
    boxes (from the player's record of the overlay)."""
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    server = _serve(folder)
    errors: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=CHROMIUM_ARGS)
            page = browser.new_page(viewport={"width": 640, "height": 360})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{server.server_address[1]}/player.html?w={size[0]}&h={size[1]}&n={samples}")
            page.wait_for_function("window.ready === true", timeout=timeout_ms)
            errors += page.evaluate("window.errors")
            if not errors:
                for i, t in enumerate(times):
                    data = page.evaluate("(t) => { window.seek(t); return document.getElementById('c').toDataURL("
                                         "'image/jpeg', 0.94); }", t)
                    (out / f"{i:05d}.jpg").write_bytes(base64.b64decode(data.split(",", 1)[1]))
                    if boxes is not None:
                        boxes.append(page.evaluate("window.boxes"))
                errors += page.evaluate("window.errors")
            browser.close()
    finally:
        server.shutdown()
    return errors


def check(code: str, folder: Path, size: tuple[int, int], duration: float) -> tuple[list[Path], str]:
    """Three stills (start, middle, end) at a low sample count. Returns the stills and the problems found, if any:
    page errors, an empty or black frame, a frame with nothing moving between start and end."""
    from PIL import Image, ImageChops, ImageStat

    stage_folder(code, folder)
    times = [min(0.4, duration * 0.1), duration * 0.5, max(0.0, duration - 0.15), duration * 0.75]
    words: list = []
    errors = frames(folder, size, 2, times, folder / "check", boxes=words)
    if errors:
        return [], "The page threw errors:\n" + "\n".join(e[:600] for e in errors[:5])
    stills = [folder / "check" / f"{i:05d}.jpg" for i in range(3)]
    problems = []
    images = [Image.open(s).convert("L") for s in stills]
    for name, im in zip(("first", "middle", "last"), images):
        st = ImageStat.Stat(im.resize((160, 90)))
        if st.stddev[0] < 7 or st.mean[0] < 4:
            problems.append(f"the {name} frame is empty (nearly one flat colour): the object or the camera is wrong")
    if ImageStat.Stat(ImageChops.difference(images[0], images[2]).resize((160, 90))).mean[0] < 1.0:
        problems.append("nothing changes between the first and last frame: the scene does not move")
    for t, found in zip(times, words):
        problems += label_problems(found, size, t)
    return stills[:3], "\n".join(dict.fromkeys(problems))


def label_problems(found: list[dict], size: tuple[int, int], t: float, pad: float = 6, margin: float = 0.025) -> list[str]:
    """Words on screen that touch each other (with a small gap) or leave the frame."""
    out = []
    w, h = size
    for b in found:
        if b["x0"] < w * margin or b["y0"] < h * margin or b["x1"] > w * (1 - margin) or b["y1"] > h * (1 - margin):
            out.append(f'at {t:.1f} s the label "{b["text"]}" leaves the frame: keep labels inside it')
    for i, a in enumerate(found):
        for b in found[i + 1:]:
            if a["text"] == b["text"]:
                continue
            if min(a["x1"], b["x1"]) + pad > max(a["x0"], b["x0"]) and min(a["y1"], b["y1"]) + pad > max(a["y0"], b["y0"]):
                out.append(f'at {t:.1f} s the labels "{a["text"]}" and "{b["text"]}" overlap: move one so they never touch')
    return out


def render_clip(code: str, folder: Path, size: tuple[int, int], duration: float, video: Path, samples: int = 5,
                fps: int = 30, workers: int = 3) -> Path:
    """The whole scene as an MP4, the frames split across `workers` browsers running side by side."""
    stage_folder(code, folder)
    n = max(1, int(round(duration * fps)))
    chunks = [(k * n // workers, (k + 1) * n // workers) for k in range(workers)]
    import os
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT / "src"), os.environ.get("PYTHONPATH", "")]))
    procs = [subprocess.Popen([sys.executable, "-m", "golide_engine.edit.recipes", "frames", str(folder), str(size[0]),
                               str(size[1]), str(samples), str(fps), str(a), str(b)], env=env)
             for a, b in chunks if b > a]
    if any(p.wait() != 0 for p in procs):
        raise RuntimeError("a recipe frame worker failed")
    video.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(folder / "frames" / "%05d.jpg"),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-an", str(video)],
                   check=True)
    return video


def _worker(argv: list[str]) -> None:
    folder, w, h, samples, fps, a, b = argv
    a, b, fps = int(a), int(b), int(fps)
    tmp = Path(folder) / f"part-{a}"
    errors = frames(Path(folder), (int(w), int(h)), int(samples), [i / fps for i in range(a, b)], tmp)
    if errors:
        print(json.dumps({"status": "recipe_frames_failed", "errors": errors[:3]}))
        raise SystemExit(1)
    final = Path(folder) / "frames"
    final.mkdir(exist_ok=True)
    for i in range(a, b):
        (tmp / f"{i - a:05d}.jpg").replace(final / f"{i:05d}.jpg")


def make(text, key: str, brief: str, words: list[dict[str, Any]], duration: float, fmt: str, folder: Path,
         samples: int = 5, workers: int = 3, record=None) -> dict[str, Any] | None:
    """Write, check (one retry with the problems fed back) and render one recipe scene. Returns {video, accent,
    events, stills} or None when it failed twice (the caller shows the house 3D instead)."""
    size = FRAME[fmt]
    problems = ""
    for attempt in (1, 2):
        output = text.generate_json(instructions(key), request(key, brief, words, duration, size, problems),
                                    CODE_SCHEMA, max_output_tokens=24000)
        if record:
            record(f"recipe-{key}-{attempt}", output)
        value = output.value
        stills, problems = check(value["code"], folder / f"try{attempt}", size, duration)
        print(json.dumps({"status": "recipe_check", "recipe": key, "attempt": attempt, "ok": not problems,
                          "problems": problems[:300]}))
        if not problems:
            video = render_clip(value["code"], folder / f"try{attempt}", size, duration, folder / f"{key}.mp4",
                                samples=samples, workers=workers)
            (folder / "style.js").write_text(value["code"], encoding="utf-8")
            return {"video": str(video), "accent": value.get("accent", ""), "events": value.get("events") or [],
                    "stills": [str(s) for s in stills], "size": list(size)}
    return None


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "frames":
    _worker(sys.argv[2:])
