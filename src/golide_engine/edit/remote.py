"""Filming an edit-engine video across many GitHub machines (owner 2026-11-26: "do your CPU modification to minimise
run time; GitHub runs are free, we are public").

One machine films every frame of a long video in a software-WebGL browser: with the living studio and the 3D blocks
that took over four hours. The composition is built once by the production job (layout checks included), handed over
in R2, and filmed in spans by a matrix of machines (.github/workflows/edit-render.yml), one span each, through
HyperFrames' own --start/--end; a join job trims each span to its exact frames and stitches the picture. The
production job waits and goes on with the sound mix as before. Any failure falls back to filming on the one machine.

    editrender/<job>/bundle.tgz       the composition folder              (production -> machines)
    editrender/<job>/meta.json        duration, fps, parts
    editrender/<job>/part-<i>.mp4     frames of span i                    (matrix jobs)
    editrender/<job>/picture.mp4      the joined picture, no sound        (join job)
    editrender/<job>/done.json | failed.json
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

WORKFLOW = "edit-render.yml"
FPS = 30
SPAN_SECONDS = 20            # one machine per ~20 s of video (living-studio frames are slow in software WebGL)
MAX_PARTS = 16               # GitHub runs 20 jobs at once on a free public repository
WAIT_MINUTES = 150
HYPERFRAMES = "hyperframes@0.9.32"


def key(job: str, name: str) -> str:
    return f"editrender/{job}/{name}"


def _store():
    from ..storage.r2 import r2_store_from_environment
    store = r2_store_from_environment()
    if store is None:
        raise RuntimeError("split render: R2 storage is not configured")
    return store


def put(job: str, name: str, data: bytes, kind: str = "application/octet-stream") -> None:
    _store().put_object(key(job, name), data, kind)


def get(job: str, name: str) -> bytes | None:
    try:
        with urllib.request.urlopen(_store().resolve(f"r2://{key(job, name)}", expires_seconds=900), timeout=600) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def parts_for(duration: float) -> int:
    return max(2, min(MAX_PARTS, math.ceil(duration / SPAN_SECONDS)))


def spans(duration: float, parts: int, fps: int = FPS) -> list[tuple[int, int]]:
    """Frame ranges [first, last) of each part: every frame of the film exactly once."""
    frames = round(duration * fps)
    return [(i * frames // parts, (i + 1) * frames // parts) for i in range(parts)]


def wanted(duration: float) -> bool:
    """Split the filming when it runs on GitHub with R2 and a token to start the machines, and the video is long
    enough to gain (a short one films faster than machines start)."""
    if os.environ.get("GOLIDE_SPLIT_RENDER", "1") == "0" or os.environ.get("GITHUB_ACTIONS") != "true":
        return False
    if not (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")) or not os.environ.get("GITHUB_REPOSITORY"):
        return False
    if not all(os.environ.get(k) for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")):
        return False
    return duration >= 50


def bundle(comp: Path) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", compresslevel=3) as tar:
        tar.add(comp, arcname="composition")
    return buf.getvalue()


def start(job: str, parts: int, which: list[int] | None = None) -> None:
    repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    todo = list(range(parts)) if which is None else which
    body = json.dumps({"ref": os.environ.get("GITHUB_REF_NAME") or "main",
                       "inputs": {"job": job, "parts": json.dumps(todo or [0])}}).encode()
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW}/dispatches", data=body,
                                 method="POST", headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30):
        pass


def render(comp: Path, duration: float, out: Path, label: str = "video", wait_minutes: int = WAIT_MINUTES,
           poll_seconds: int = 30) -> Path:
    """Hand the composition to the machines and wait for the joined picture (written to ``out``)."""
    data = bundle(comp)
    job = f"{label}-{hashlib.sha256(data + f"lead{LEAD}".encode()).hexdigest()[:12]}"
    parts = parts_for(duration)
    if get(job, "done.json") is None:                       # the same composition is never filmed twice
        if get(job, "failed.json") not in (None, b"{}"):
            put(job, "failed.json", b"{}", "application/json")
        # owner 2026-11-26 ("don't reset, resume where it left off"): spans already filmed for this same composition
        # are kept; only the missing ones go to the machines
        meta = get(job, "meta.json")
        if meta is None or json.loads(meta).get("parts") != parts:
            put(job, "bundle.tgz", data, "application/gzip")
            put(job, "meta.json", json.dumps({"duration": duration, "fps": FPS, "parts": parts}).encode(), "application/json")
        missing = [i for i in range(parts) if get(job, f"part-{i}.ok") is None]
        start(job, parts, missing)
        print(json.dumps({"status": "split_render_started", "job": job, "parts": parts, "to_film": missing,
                          "bundle_mb": round(len(data) / 1e6, 1)}), flush=True)
        t0, deadline = time.time(), time.time() + wait_minutes * 60
        while time.time() < deadline:
            time.sleep(poll_seconds)
            if get(job, "done.json") is not None:
                break
            failed = get(job, "failed.json")
            if failed and failed.strip() not in (b"", b"{}"):
                raise RuntimeError("split render stopped: " + failed.decode("utf-8", "replace")[:600])
        else:
            raise RuntimeError(f"split render did not finish in {wait_minutes} minutes")
        print(json.dumps({"status": "split_render_done", "job": job, "minutes": round((time.time() - t0) / 60, 1)}), flush=True)
    picture = get(job, "picture.mp4")
    if not picture:
        raise RuntimeError("split render reported done but the picture is missing")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(picture)
    return out


# 2026-11-27 (owner's 0.5 s review): the first two frames a machine films come out without the 3D studio (its first draw
# lands a frame late), a flicker at every span's start. Each span is filmed from a few frames earlier and those are cut.
LEAD = 3


def lead_frames(f0: int) -> int:
    return min(LEAD, f0)


def film_part(job: str, part: int, work: Path) -> Path:
    """On a render machine: fetch the composition, film span ``part``, upload it (a span already filmed is kept)."""
    meta = json.loads(get(job, "meta.json") or b"{}")
    if get(job, f"part-{part}.ok") is not None:
        return work / f"part-{part}.mp4"
    data = get(job, "bundle.tgz")
    if not data or not meta:
        raise SystemExit(f"no bundle for {job}")
    work.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        tar.extractall(work, filter="data")
    f0, f1 = spans(meta["duration"], meta["parts"], meta["fps"])[part]
    f0 -= lead_frames(f0)                     # a few frames before the span: the 3D's warm-up, cut at the join
    out = work / f"part-{part}.mp4"
    env = dict(os.environ)
    if os.environ.get("CHROME"):
        env["HYPERFRAMES_BROWSER_PATH"] = os.environ["CHROME"]
    # a frame or two past the span's end is filmed and trimmed at the join, so nothing is ever short
    subprocess.run(["npx", "-y", HYPERFRAMES, "render", str(work / "composition"), "-o", str(out), "--fps", str(meta["fps"]),
                    "--quality", "high", "--start", f"{f0 / meta['fps']:.4f}",
                    "--end", f"{min(meta['duration'], (f1 + 2) / meta['fps']):.4f}", "--keyframe-interval", "1", "--quiet"],
                   check=True, env=env)
    put(job, out.name, out.read_bytes(), "video/mp4")
    put(job, f"part-{part}.ok", b"1", "text/plain")             # this span is done: a rerun keeps it
    return out


def frames_of(path: Path) -> int:
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_packets", "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return int(r.stdout.strip().split(",")[0])


def join(job: str, work: Path) -> Path:
    """Each span trimmed to exactly its frames, then stitched without re-encoding."""
    meta = json.loads(get(job, "meta.json") or b"{}")
    work.mkdir(parents=True, exist_ok=True)
    lst = []
    for i, (f0, f1) in enumerate(spans(meta["duration"], meta["parts"], meta["fps"])):
        raw = work / f"part-{i}.mp4"
        raw.write_bytes(get(job, raw.name) or b"")
        if raw.stat().st_size == 0:
            raise RuntimeError(f"part {i} missing")
        lead = lead_frames(f0)
        need, have = f1 - f0, frames_of(raw)
        if have < need + lead:
            raise RuntimeError(f"part {i} has {have} frames, needs {need + lead}")
        cut = work / f"cut-{i}.mp4"
        # every frame is a keyframe (--keyframe-interval 1): the warm-up frames are skipped without re-encoding
        # (an output-side seek: packets before it are dropped, exact to the frame; checked against frame checksums)
        skip = ["-ss", f"{(lead - 0.25) / meta['fps']:.5f}"] if lead else []
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), *skip, "-frames:v", str(need), "-c", "copy", "-an",
                        str(cut)], check=True)
        if frames_of(cut) != need:
            raise RuntimeError(f"part {i} cut to {frames_of(cut)} frames, needs {need}")
        lst.append(cut)
    (work / "list.txt").write_text("".join(f"file '{p.resolve()}'\n" for p in lst), encoding="utf-8")
    picture = work / "picture.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(work / "list.txt"), "-c", "copy",
                    "-movflags", "+faststart", str(picture)], check=True)
    total = round(meta["duration"] * meta["fps"])
    if abs(frames_of(picture) - total) > 1:
        raise RuntimeError(f"joined picture has {frames_of(picture)} frames, the film has {total}")
    put(job, picture.name, picture.read_bytes(), "video/mp4")
    put(job, "done.json", json.dumps({"ok": True}).encode(), "application/json")
    return picture


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["part", "join", "failed"])
    ap.add_argument("--job", required=True)
    ap.add_argument("--part", type=int, default=0)
    ap.add_argument("--work", type=Path, default=Path("work"))
    ap.add_argument("--message", default="")
    a = ap.parse_args(argv)
    if a.action == "part":
        film_part(a.job, a.part, a.work)
    elif a.action == "join":
        join(a.job, a.work)
    elif a.action == "failed":
        put(a.job, "failed.json", json.dumps({"error": a.message or "a render job failed"}).encode(), "application/json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
