"""Can the engine read YouTube transcripts from GitHub's servers? (2026-10-29)

The script stage is moving to modelling the transcripts of videos that worked. Before
building on that, this checks two ways of getting them from a GitHub runner and reports
which ones YouTube lets through. Results go to production-queue/transcript-probe.json and
to the owner by email.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from email.message import EmailMessage
from pathlib import Path

VIDEOS = sys.argv[1:] or ["mhFozOsKZLU", "VPOC47eTE-E", "Me5U1p85VW0"]


def via_api(video_id: str) -> dict:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        fetched = YouTubeTranscriptApi().fetch(video_id, languages=["en", "en-US", "en-GB"])
        text = " ".join(s.text for s in fetched)
        return {"ok": bool(text.strip()), "words": len(text.split()), "start": text[:300]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:300]}"}


def via_ytdlp(video_id: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        cmd = ["yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs", "--sub-langs", "en.*",
               "--sub-format", "vtt", "-o", f"{tmp}/%(id)s.%(ext)s", f"https://www.youtube.com/watch?v={video_id}"]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        files = list(Path(tmp).glob("*.vtt"))
        if not files:
            return {"ok": False, "error": (run.stderr or run.stdout)[-300:]}
        lines = [l for l in files[0].read_text(errors="ignore").splitlines()
                 if l and "-->" not in l and not l.startswith(("WEBVTT", "Kind:", "Language:"))]
        text = " ".join(dict.fromkeys(l.strip() for l in lines))
        return {"ok": bool(text.strip()), "words": len(text.split()), "start": text[:300]}


def via_engine(video_id: str) -> dict:
    """What the engine itself gets (Supadata when SUPADATA_API_KEY is set)."""
    from golide_engine.youtube.transcripts import fetch
    text = fetch(f"https://www.youtube.com/watch?v={video_id}")
    return {"ok": bool(text), "words": len(text.split()), "start": text[:300]} if text else {"ok": False, "error": "no transcript"}


def main() -> None:
    results = {v: {"engine": via_engine(v)} for v in VIDEOS}
    out = Path("production-queue/transcript-probe.json")
    out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    lines = []
    for v, r in results.items():
        for method, res in r.items():
            lines.append(f"{v} via {method}: " + (f"OK, {res['words']} words" if res["ok"] else f"BLOCKED ({res.get('error', '')[:120]})"))
    msg = EmailMessage()
    msg["Subject"] = "GOLIDE: transcript test from GitHub's servers"
    msg.set_content("Can the engine read YouTube transcripts from GitHub?\n\n" + "\n".join(lines))
    from golide_engine.operations.email import _send
    _send(msg)


if __name__ == "__main__":
    main()
