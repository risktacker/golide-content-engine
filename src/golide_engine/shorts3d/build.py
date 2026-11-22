"""GOLIDE Shorts on the 3D Shorts engine (owner 2026-11-22: "Bingo. Now this is the direction").

The engine is thuann-vn/claude-3d-animated-shorts (MIT), cloned at a pinned commit (ENGINE_COMMIT) at build time; its
cast, rig, office/home sets, lights and grade are used as they ship. Our scenes and director live in assets/shorts3d/
and are wired in by assets/shorts3d/hook.py (one branch at its skit). Free: code plus CC0 assets, no model calls.

    python -m golide_engine.shorts3d.build --engine ~/c3d/engine --scene chipmaker-open \
        --words timed-words.json --voice narration.mp3 --out out/ --mode stills|video [--parts 4]

stills: the director's report, one clean sheet with the captions burned in (what the owner sees) and a debug sheet with
        the safe crop, caption band and every person's box. A shot the director cannot repair stops the build.
video:  frames rendered in parallel browsers, joined, captions burned in ("short3d"), the voice levelled and the one
        Shorts track (Discipline Finishes) as one steady bed under it.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "assets" / "shorts3d"
ENGINE_REPO = "https://github.com/thuann-vn/claude-3d-animated-shorts"
ENGINE_COMMIT = "f5b4c4aebfc5eeb7acc51fac1f29bfef10389ff5"     # the commit the owner saw render on 2026-11-22
W, H, FPS = 1080, 1920, 30
VOICE_LUFS = -16.0


def install(engine: Path) -> None:
    """Copy our scene modules into the engine and add the hook (refuses if the engine's skit branch moved)."""
    dest = engine / "golide"
    dest.mkdir(exist_ok=True)
    for f in ASSETS.glob("*.js"):
        shutil.copy2(f, dest / f.name)
    main = engine / "main.js"
    if "golide/scene.js" not in main.read_text(encoding="utf-8"):
        subprocess.run([sys.executable, str(ASSETS / "hook.py"), str(main)], check=True)


def use_board(engine: Path, board_data: dict, words: list[dict]) -> list[str]:
    """Repair a storyboard for free and hand it to the board scene; returns what was repaired."""
    global SET_QUERY
    from .board import repair
    fixed, notes = repair(board_data, words)
    (engine / "golide" / "board.json").write_text(json.dumps(fixed), encoding="utf-8")
    (engine / "golide" / "board.words.json").write_text(json.dumps(words), encoding="utf-8")
    SET_QUERY = "&set=home" if fixed["set"] == "home" else ""
    for n in notes:
        print("storyboard repaired:", n)
    return notes


def scene_words(words: list[dict], until: float | None) -> list[dict]:
    """The spoken words the scene acts to (word, start, end), cut at ``until`` seconds."""
    out = [{"word": str(w.get("word") or w.get("text")), "start": float(w["start"]), "end": float(w["end"])} for w in words]
    return [w for w in out if until is None or w["start"] < until]


SET_QUERY = ""                                               # &set=home when the storyboard is set at home


def _node(engine: Path, scene: str, out: Path, *args: str) -> subprocess.Popen:
    # absolute paths: the browser runner works inside the engine folder
    import os
    return subprocess.Popen(["node", str(ASSETS / "render.cjs"), str(engine.resolve()), scene, str(out.resolve()), str(W), str(H), str(FPS), *args],
                            cwd=engine, env={**os.environ, "XQ": SET_QUERY})


def _report(out: Path) -> dict:
    return json.loads((out / "report.json").read_text(encoding="utf-8"))


def _burn_still(still: Path, t: float, ass: Path, dest: Path) -> None:
    from ..stickman.captions import FONTS
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(still), "-vf",
                    f"setpts=PTS+{t:.3f}/TB,ass='{ass.as_posix()}':fontsdir='{FONTS.as_posix()}'", "-frames:v", "1", str(dest)], check=True)


def _ass(words: list[dict], folder: Path) -> Path:
    from ..stickman import captions
    lines = captions.chunks(words, None, captions.WORDS["short3d"])
    p = folder / "captions.ass"
    p.write_text(captions.ass(lines, "short3d", *captions.FRAME["short3d"]), encoding="utf-8")
    return p


def stills(engine: Path, scene: str, words: list[dict], out: Path) -> dict:
    """Director report plus the clean and debug sheets: per shot its first, middle and last moment."""
    raw, dbg = out / "stills-raw", out / "stills-debug"
    if _node(engine, scene, dbg, "stills", "", "debug").wait() not in (0, 3):
        raise RuntimeError("the 3D engine page failed before the director ran (see the log above)")
    rep = _report(dbg)
    times = [round(t, 2) for s in rep["shots"] for t in (s["t0"] + 0.05, (s["t0"] + s["t1"]) / 2, s["t1"] - 0.05)]
    code = _node(engine, scene, raw, "stills", ",".join(f"{t:.2f}" for t in times)).wait()
    if code not in (0, 3):
        raise RuntimeError("rendering the clean stills failed")
    ass = _ass(words, out)
    cap = out / "stills"
    cap.mkdir(parents=True, exist_ok=True)
    for t in times:
        _burn_still(raw / f"still-{t:06.2f}.jpg", t, ass, cap / f"still-{t:06.2f}.jpg")
    for src, name in ((cap, "sheet.jpg"), (dbg, "sheet-debug.jpg")):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-pattern_type", "glob", "-i", str(src / "still-*.jpg"),
                        "-vf", f"scale=360:640,tile=6x{-(-len(times) // 6)}:padding=6:color=white", "-frames:v", "1",
                        str(out / name)], check=True)
    return rep


def part(engine: Path, scene: str, out: Path, i: int, n: int) -> Path:
    """Frames i/n of the Short, one browser (a render machine of the matrix)."""
    code = _node(engine, scene, out, "video", str(i), str(n)).wait()
    if code:
        raise RuntimeError(f"part {i}/{n} failed (exit {code}; 3 = the director stopped a shot)")
    return out / f"part-{i}.mp4"


def join(folder: Path, n: int, picture: Path) -> Path:
    """The parts, in order, as one picture (no sound)."""
    lst = folder / "list.txt"
    missing = [i for i in range(n) if not (folder / f"part-{i}.mp4").exists()]
    if missing:
        raise RuntimeError(f"parts missing: {missing}")
    lst.write_text("".join(f"file '{(folder / f'part-{i}.mp4').resolve()}'\n" for i in range(n)), encoding="utf-8")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(picture)], check=True)
    return picture


def _seconds(path: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True, check=True).stdout)


def finish(picture: Path, words: list[dict], voice: Path, out: Path, final: Path) -> Path:
    """Captions burned in ("short3d"), the voice only levelled (never processed), the one Shorts track (Discipline
    Finishes) as one steady bed under it."""
    from ..stickman import captions
    from ..vector.ambient import LEVELS_DB
    from ..vector.music_bed import pick, render as bed
    out.mkdir(parents=True, exist_ok=True)
    work = out / "picture-captioned.mp4"
    work.write_bytes(picture.read_bytes())
    captions.add(work, words, None, "short3d", out / "cap")
    dur = _seconds(work)
    track = pick("short", None)
    if not track or "discipline" not in track["file"]:
        raise RuntimeError("the Shorts track (Discipline Finishes) is not the picked Short music")
    music = bed(track, dur, out / "bed.wav", LEVELS_DB["short"])
    final.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(work), "-i", str(voice), "-i", str(music), "-filter_complex",
                    f"[1:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,loudnorm=I={VOICE_LUFS}:TP=-1.5:LRA=11,aresample=48000[v];"
                    "[2:a]aresample=48000[b];[v][b]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.79[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}",
                    "-movflags", "+faststart", str(final)], check=True)
    return final


def video(engine: Path, scene: str, words: list[dict], voice: Path, out: Path, parts: int) -> Path:
    """All parts on this machine (trials); production splits them across machines (remote.py)."""
    frames = out / "parts"
    procs = [_node(engine, scene, frames, "video", str(i), str(parts)) for i in range(parts)]
    codes = [p.wait() for p in procs]
    if any(codes):
        raise RuntimeError(f"rendering failed (exit codes {codes}); a 3 means the director stopped a shot, see report.json")
    picture = join(frames, parts, out / "picture.mp4")
    return finish(picture, words, voice, out, out / "clip.mp4")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--engine", type=Path, required=True)
    ap.add_argument("--scene", default="board")
    ap.add_argument("--board", type=Path, help="a storyboard (board.json): built by the generic board scene")
    ap.add_argument("--words", type=Path, required=True)
    ap.add_argument("--voice", type=Path)
    ap.add_argument("--until", type=float)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mode", choices=["stills", "video", "part"], default="stills")
    ap.add_argument("--part", type=int, default=0)
    ap.add_argument("--parts", type=int, default=4)
    a = ap.parse_args(argv)
    install(a.engine)
    data = json.loads(a.words.read_text(encoding="utf-8"))
    words = scene_words(data.get("words", data) if isinstance(data, dict) else data, a.until)
    (a.engine / "golide" / f"{a.scene}.words.json").write_text(json.dumps(words), encoding="utf-8")
    if a.board:
        use_board(a.engine, json.loads(a.board.read_text(encoding="utf-8")), words)
    a.out.mkdir(parents=True, exist_ok=True)
    if a.mode == "part":                                   # a render machine: its frames only (the check job ran the director)
        print("part:", part(a.engine, a.scene, a.out, a.part, a.parts))
        return 0
    rep = stills(a.engine, a.scene, words, a.out)
    for s in rep["shots"]:
        print(("OK  " if s["ok"] else "FAIL"), s["name"], "| found:", "; ".join(s["found"]) or "-", "| repair:", s.get("repair"))
    if not rep["ok"]:
        print("director: stopped, a shot could not be repaired (report.json)")
        return 3
    if a.mode == "video":
        if not a.voice:
            ap.error("--voice is needed for a video")
        print("clip:", video(a.engine, a.scene, words, a.voice, a.out, a.parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
