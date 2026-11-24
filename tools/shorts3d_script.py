"""A 3D Short from a script the owner hands over (owner 2026-11-24: "Here is the script... run the full short").

The production path of a 3D Short (orchestration/production.py _shorts3d_short) for a script that did not come from a
queue slot: the AI voice reads it once (ElevenLabs, saved in R2 and never read twice), Sol writes ONE storyboard
(board.write, at most board.COST_CAP_USD, saved under the same fingerprint as production, never paid twice), the
free repairs, the render machines, the lessons, the finish. With --board a hand-written storyboard replaces Sol's
(a free trial) and --until cuts the voice to its first seconds.

    python tools/shorts3d_script.py --script s.txt --slug pirates [--board b.json --until 9] --out out/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golide_engine.shorts3d import board as board3d, build as build3d, lessons as lessons3d, remote as remote3d  # noqa: E402
from golide_engine.storage.r2 import r2_store_from_environment  # noqa: E402


def _get(store, key: str) -> bytes | None:
    try:
        with urllib.request.urlopen(store.resolve(f"r2://{key}", expires_seconds=600), timeout=60) as r:
            return r.read()
    except Exception:  # noqa: BLE001 - not there yet
        return None


def voice(store, slug: str, script: str, out: Path) -> tuple[Path, list[dict]]:
    """The one AI read of the script: from R2 when it was read before, else ElevenLabs once."""
    mp3, wj = out / "narration-ai.mp3", out / "words.json"
    base = f"shorts3d-script/{slug}-{hashlib.sha256(script.encode()).hexdigest()[:12]}"
    a, w = _get(store, f"{base}/narration-ai.mp3"), _get(store, f"{base}/words.json")
    if a and w:
        mp3.write_bytes(a); wj.write_bytes(w)
        print(json.dumps({"status": "voice_reused", "key": base}))
    else:
        from golide_engine.providers.registry import ProviderRegistry
        res = ProviderRegistry(ROOT / "config/providers.json").voice(live=True).synthesize(script, mp3)
        words = res.details["words"]
        if not words:
            raise SystemExit("the voice came back without word timings")
        wj.write_text(json.dumps(words), encoding="utf-8")
        store.put_object(f"{base}/narration-ai.mp3", mp3.read_bytes(), "audio/mpeg")
        store.put_object(f"{base}/words.json", wj.read_bytes(), "application/json")
        print(json.dumps({"status": "voice_read", "characters": res.details["characters"],
                          "seconds": round(res.details["duration_seconds"], 2), "key": base}))
    return mp3, json.loads(wj.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", type=Path, required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--board", type=Path, help="hand-written storyboard (free trial) in place of Sol's")
    ap.add_argument("--until", type=float, help="use only the first seconds of the voice (trials)")
    ap.add_argument("--parts", type=int, default=remote3d.PARTS)
    ap.add_argument("--voice-only", action="store_true")
    ap.add_argument("--out", type=Path, default=Path("out"))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store = r2_store_from_environment()
    if store is None:
        raise SystemExit("R2 is not configured")
    script = a.script.read_text(encoding="utf-8").strip()
    mp3, timed = voice(store, a.slug, script, a.out)
    seconds = build3d._seconds(mp3)
    words = build3d.scene_words(timed, a.until)
    (a.out / "scene-words.json").write_text(json.dumps(words, indent=0), encoding="utf-8")
    (a.out / "sentences.json").write_text(json.dumps(board3d.sentences(words), indent=1), encoding="utf-8")
    if a.voice_only:
        print(json.dumps({"status": "voice_only", "seconds": round(seconds, 2), "words": len(words)}))
        return 0
    if a.until is None and not 45.0 <= seconds <= 75.0:          # owner 2026-11-18: every Short is 45-75 s
        raise SystemExit(f"the read is {seconds:.1f} s; a Short is 45-75 s")

    learned = lessons3d.for_sol(lessons3d.load(store))
    print(json.dumps({"status": "lessons_read", "lessons": learned}))
    if a.board:
        raw = json.loads(a.board.read_text(encoding="utf-8"))
        print(json.dumps({"status": "hand_board", "file": str(a.board), "cost_usd": 0}))
    else:
        mark = hashlib.sha256(json.dumps([[w["word"], round(w["start"], 2)] for w in words]
                                         + [round(float(seconds), 2)]).encode()).hexdigest()[:24]
        key = f"shorts3d-board-v2/{mark}.json"
        saved = _get(store, key)
        if saved:
            raw = json.loads(saved)
            print(json.dumps({"status": "board_reused", "key": key, "cost_usd": 0}))
        else:
            from golide_engine.edit.pipeline import settings
            from golide_engine.providers.openai_text import OpenAITextProvider
            conf = settings().get("shorts3d") or {}
            writer = OpenAITextProvider(conf.get("model", "gpt-5.6-sol"), conf.get("reasoning_effort", "medium"))
            t0 = time.time()
            raw, out = board3d.write(writer, a.title or a.slug, words, learned)
            store.put_object(key, json.dumps(raw).encode("utf-8"), "application/json")      # saved at once
            cost = out.input_tokens * board3d.PRICE_IN + out.output_tokens * board3d.PRICE_OUT
            print(json.dumps({"status": "board_written", "key": key, "input_tokens": out.input_tokens,
                              "cached_input_tokens": out.cached_input_tokens, "output_tokens": out.output_tokens,
                              "cost_usd": round(cost, 4), "seconds": round(time.time() - t0, 1),
                              "board_kb": round(len(json.dumps(raw)) / 1024, 1)}))
    (a.out / "board.json").write_text(json.dumps(raw, indent=1), encoding="utf-8")
    fixed, notes = board3d.repair(raw, words)
    cover = board3d.coverage(fixed, words)
    print(json.dumps({"status": "repaired", "notes": notes}))
    print(json.dumps({"status": "sentences", "coverage": cover}))
    (a.out / "board-fixed.json").write_text(json.dumps(fixed, indent=1), encoding="utf-8")
    pid = f"script-{a.slug}-{int(time.time())}"
    report = None
    try:
        picture = remote3d.render(pid, fixed, words, a.out / "picture.mp4", parts=a.parts, wait_minutes=110)
    finally:
        rep = remote3d.get(pid, "report.json")
        report = json.loads(rep) if rep else None
        if not a.board:                               # a hand trial teaches nothing about Sol
            print(json.dumps({"status": "lessons", **lessons3d.learn(store, notes, report, cover, fixed)}))
        for name in ("sheet.jpg", "report.json"):
            data = remote3d.get(pid, name)
            if data:
                (a.out / name).write_bytes(data)
    if a.until:
        import subprocess
        cut = a.out / "voice-cut.mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-t", f"{words[-1]['end'] + 0.3:.2f}", str(cut)], check=True)
        mp3 = cut
    build3d.finish(picture, words, mp3, a.out / "finish", a.out / "clip.mp4")
    print(json.dumps({"status": "clip", "seconds": build3d._seconds(a.out / "clip.mp4"), "production_id": pid}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
