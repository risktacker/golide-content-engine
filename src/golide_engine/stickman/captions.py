"""A caption layer on top of a finished Stickman long video (owner 2026-11-21): the same small captions as Inkee
(Poppins 800, each word lighting up as it is said, key numbers in gold), added over ReachMora's own picture and
sound. Nothing of the kit's editing is replaced: its cuts on beats, object sounds and chapter cards stay as they are;
this is one more layer, burned in after the kit (and after Goli, on Stickman + Goli).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
FONTS = ROOT / "assets" / "fonts" / "captions"         # Poppins ExtraBold (OFL), the Inkee caption face
MAX_WORDS = 7                                          # Inkee long: up to 7 words a line
SIZE = 50                                              # Inkee long caption size
TEXT, GOLD = "F4F1EA", "E8C268"
DIM = 0x9E                                             # unsaid words at 38% (Inkee: opacity .38)
# where the captions go: the whole frame (pure Stickman) or under the panel, clear of Goli (Stickman + Goli)
# full: in the strip under the floor (characters' feet stand at 1010; the kit's name card ends at 1004)
REGION = {"full": (120, 120, 10, 44), "beside": (64, 644, 40, SIZE),
          # owner 2026-11-22: Stickman Shorts get the Inkee captions too, like Ricks Clips and Afterhour Theory: a few
          # big words at a time in the lower middle, inside the phone crop (130 px left, 160 right)
          "short": (150, 180, 560, 84)}
FRAME = {"short": (1080, 1920)}
WORDS = {"short": 4}


def _shift(pauses: list[tuple[float, float]]):
    return lambda t: t + sum(d for v, d in pauses if v <= t + 1e-9)


def _key(word: str) -> bool:
    """Key terms in gold, as Inkee lights its key numbers: anything with a digit, money or a percent."""
    return bool(re.search(r"\d|[$€£%]", word))


def chunks(words: list[dict[str, Any]], pauses: list[tuple[float, float]] | None = None,
           max_words: int = MAX_WORDS) -> list[dict[str, Any]]:
    """The spoken words in caption lines: a line ends at a sentence's end or after max_words (split evenly), each
    word keeps its own time; the kit's silent chapter cards push the times like the voice."""
    shift = _shift(pauses or [])
    items = [(str(w.get("word") or w.get("text") or "").strip(), float(w["start"]), float(w.get("end", w["start"])))
             for w in words]
    items = [(t.replace("...", "").replace("…", ""), s, e) for t, s, e in items if t and t not in ("...", "…")]
    sentences, cur = [], []
    for it in items:
        cur.append(it)
        if re.search(r"[.!?]['\")\]]*$", it[0]):
            sentences.append(cur); cur = []
    if cur:
        sentences.append(cur)
    out: list[dict[str, Any]] = []
    for sent in sentences:
        n = -(-len(sent) // max_words); size = -(-len(sent) // n)
        for i in range(0, len(sent), size):
            part = sent[i:i + size]
            out.append({"words": [{"text": t, "at": round(shift(s), 3), "end": round(shift(e), 3)} for t, s, e in part],
                        "keys": [j for j, (t, _, _) in enumerate(part) if _key(t)]})
    for k, c in enumerate(out):
        c["start"] = round(max(0.0, c["words"][0]["at"] - 0.05), 3)
        nxt = out[k + 1]["words"][0]["at"] - 0.06 if k + 1 < len(out) else c["words"][-1]["end"] + 0.6
        c["end"] = round(min(nxt, c["words"][-1]["end"] + 1.2), 3)       # never two lines at once; no long hang
    return [c for c in out if c["end"] - c["start"] >= 0.15]


def _ts(t: float) -> str:
    cs = int(round(max(0.0, t) * 100)); h, cs = divmod(cs, 360000); m, cs = divmod(cs, 6000); s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _bgr(hexc: str, alpha: int = 0) -> str:
    return f"&H{alpha:02X}{hexc[4:6]}{hexc[2:4]}{hexc[0:2]}"


def ass(lines: list[dict[str, Any]], place: str = "full", width: int = 1920, height: int = 1080) -> str:
    left, right, bottom, size = REGION[place]
    head = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}\nWrapStyle: 0\n"
            "ScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
            "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
            "MarginR, MarginV, Encoding\n"
            f"Style: Cap,Poppins ExtraBold,{size},{_bgr(TEXT)},{_bgr(TEXT, DIM)},&H00000000,&H50000000,0,0,0,0,100,100,1,0,1,"
            f"{4 if place == 'short' else 2.2},3,2,{left},{right},{bottom},1\n\n[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    rows = []
    for c in lines:
        t0 = float(c["start"]); parts = []
        lead = max(0, int(round((c["words"][0]["at"] - t0) * 100)))
        if lead:
            parts.append(f"{{\\k{lead}}}")
        for j, w in enumerate(c["words"]):
            nxt = c["words"][j + 1]["at"] if j + 1 < len(c["words"]) else max(w["end"], w["at"] + .1)
            k = max(1, int(round((nxt - w["at"]) * 100)))
            text = w["text"].replace("{", "(").replace("}", ")").replace("\\", "/")
            if j in c["keys"]:
                parts.append(f"{{\\k{k}\\1c{_bgr(GOLD)}\\2c{_bgr(GOLD)}}}{text}{{\\1c{_bgr(TEXT)}\\2c{_bgr(TEXT)}}} ")
            else:
                parts.append(f"{{\\k{k}}}{text} ")
        rows.append(f"Dialogue: 0,{_ts(t0)},{_ts(float(c['end']))},Cap,,0,0,0,,{''.join(parts).rstrip()}")
    return head + "\n".join(rows) + "\n"


def add(video: Path, words: list[dict[str, Any]], pauses: list[tuple[float, float]] | None, place: str,
        folder: Path) -> Path:
    """Burn the caption layer into the finished video in place (its sound copied untouched)."""
    folder.mkdir(parents=True, exist_ok=True)
    lines = chunks(words, pauses, WORDS.get(place, MAX_WORDS))
    sub = folder / "captions.ass"
    sub.write_text(ass(lines, place, *FRAME.get(place, (1920, 1080))), encoding="utf-8")
    out = folder / "captioned.mp4"
    flt = f"ass='{sub.as_posix()}':fontsdir='{FONTS.as_posix()}'"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", flt, "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(out)], check=True)
    out.replace(video)
    return video
