"""Rendering a 3D Short across many GitHub machines (owner plan 2026-11-22, step 5).

On one runner, several software-WebGL browsers fight for the same 4 cores (4 browsers were slower than 1), so a Short
is split across runner JOBS, one browser each (.github/workflows/shorts3d-render.yml). The production job hands over a
bundle in R2 (the repaired storyboard and the word timings), starts the render, and waits for the joined picture:

    shorts3d/<production_id>/bundle.json      storyboard + words            (production -> render)
    shorts3d/<production_id>/report.json      the director's report         (render check job)
    shorts3d/<production_id>/sheet.jpg        stills sheet, captions burned (render check job)
    shorts3d/<production_id>/part-<i>.mp4     frames i/N                    (render matrix jobs)
    shorts3d/<production_id>/picture.mp4      the joined picture, no sound  (render join job)
    shorts3d/<production_id>/done.json | failed.json                       (render result)
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

WORKFLOW = "shorts3d-render.yml"
PARTS = 12                    # 60 s = 1,800 frames: about 150 frames a machine, ~10 minutes each plus setup
WAIT_MINUTES = 100


def key(pid: str, name: str) -> str:
    return f"shorts3d/{pid}/{name}"


def _store():
    from ..storage.r2 import r2_store_from_environment
    store = r2_store_from_environment()
    if store is None:
        raise RuntimeError("3D Short: R2 storage is not configured (the render machines take their work from it)")
    return store


def put(pid: str, name: str, data: bytes, kind: str = "application/octet-stream") -> None:
    _store().put_object(key(pid, name), data, kind)


def get(pid: str, name: str) -> bytes | None:
    try:
        with urllib.request.urlopen(_store().resolve(f"r2://{key(pid, name)}", expires_seconds=600), timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def start(pid: str, parts: int = PARTS) -> None:
    """Start the render workflow (the production job's GITHUB_TOKEN may dispatch workflows: permissions actions: write)."""
    repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not repo or not token:
        raise RuntimeError("3D Short: GITHUB_REPOSITORY and GITHUB_TOKEN are needed to start the render machines")
    body = json.dumps({"ref": os.environ.get("GITHUB_REF_NAME") or "main",
                       "inputs": {"production_id": pid, "parts": str(parts)}}).encode()
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW}/dispatches", data=body,
                                 method="POST", headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30):
        pass


def render(pid: str, board: dict, words: list[dict], out: Path, parts: int = PARTS, wait_minutes: int = WAIT_MINUTES,
           poll_seconds: int = 30) -> Path:
    """Hand the storyboard to the render machines and wait for the joined picture (written to ``out``)."""
    if get(pid, "done.json") is None:                      # a finished render is never redone
        for stale in ("failed.json",):
            if get(pid, stale) is not None:
                put(pid, stale, b"{}")                     # cleared by overwriting: a rerun starts clean
        put(pid, "bundle.json", json.dumps({"board": board, "words": words}).encode(), "application/json")
        start(pid, parts)
        print(json.dumps({"status": "shorts3d_render_started", "production_id": pid, "parts": parts}), flush=True)
        deadline = time.time() + wait_minutes * 60
        while time.time() < deadline:
            time.sleep(poll_seconds)
            if get(pid, "done.json") is not None:
                break
            failed = get(pid, "failed.json")
            if failed and failed.strip() not in (b"", b"{}"):
                raise RuntimeError("3D Short render stopped: " + failed.decode("utf-8", "replace")[:800])
        else:
            raise RuntimeError(f"3D Short render did not finish in {wait_minutes} minutes")
    data = get(pid, "picture.mp4")
    if not data:
        raise RuntimeError("3D Short: the render reported done but the picture is missing")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return out


def main(argv: list[str] | None = None) -> int:
    """Used by the render workflow: fetch the bundle, upload results."""
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["fetch", "put", "done", "failed"])
    ap.add_argument("--pid", required=True)
    ap.add_argument("--file", type=Path)
    ap.add_argument("--name")
    ap.add_argument("--message", default="")
    a = ap.parse_args(argv)
    if a.action == "fetch":
        data = get(a.pid, "bundle.json")
        if not data:
            raise SystemExit(f"no bundle for {a.pid}")
        a.file.parent.mkdir(parents=True, exist_ok=True)
        b = json.loads(data)
        a.file.write_text(json.dumps(b["board"]), encoding="utf-8")
        a.file.with_name("words.json").write_text(json.dumps(b["words"]), encoding="utf-8")
    elif a.action == "put":
        kind = {"mp4": "video/mp4", "jpg": "image/jpeg", "json": "application/json"}.get(a.file.suffix[1:], "application/octet-stream")
        put(a.pid, a.name or a.file.name, a.file.read_bytes(), kind)
    elif a.action == "done":
        put(a.pid, "done.json", json.dumps({"ok": True}).encode(), "application/json")
    else:
        put(a.pid, "failed.json", json.dumps({"error": a.message or "a render job failed"}).encode(), "application/json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
