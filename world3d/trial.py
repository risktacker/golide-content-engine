"""TRIAL: one real script through World 3D with the real text model, stills only.
Never touches production. Output: a contact sheet, the blueprints and a cost report.
python world3d/trial.py world3d/trials/run.json --blender-python PATH --out DIR"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from world3d.explain3d import stage  # noqa: E402
from world3d.explain3d.openai_text import LunaText  # noqa: E402

WORDS_PER_SECOND = 2.6  # normal speaking pace; the script was never recorded
STILL_POINTS = (0.15, 0.5, 0.85)


def script_lines(path: Path) -> list[str]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw and not re.fullmatch(r"\[.*\]", raw):
            lines.append(raw)
    return lines


def paced(lines: list[str]):
    words, times, t = [], [], 0.0
    for line in lines:
        start = t
        for w in line.split():
            words.append({"word": re.sub(r"[^\w']", "", w).lower() or w, "start": round(t, 2),
                          "end": round(t + 0.8 / WORDS_PER_SECOND, 2)})
            t += 1 / WORDS_PER_SECOND
        t += 0.3
        times.append((round(start, 2), round(t, 2)))
    return words, times


def contact_sheet(stills: list[tuple[str, Path]], out: Path, title: str) -> None:
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font, big = ImageFont.truetype(font_path, 22), ImageFont.truetype(font_path, 34)
    tw, th, pad = 640, 360, 16
    cols = len(STILL_POINTS)
    rows = (len(stills) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, 80 + rows * (th + 44 + pad)), (14, 14, 18))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 22), title, font=big, fill=(233, 196, 106))
    for i, (caption, path) in enumerate(stills):
        x, y = pad + (i % cols) * (tw + pad), 80 + (i // cols) * (th + 44 + pad)
        sheet.paste(Image.open(path).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS), (x, y))
        d.text((x, y + th + 8), caption, font=font, fill=(244, 244, 245))
    sheet.save(out, quality=92)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("request")
    ap.add_argument("--blender-python", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    req = json.loads(Path(a.request).read_text(encoding="utf-8"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lines = script_lines(HERE / req["script"])
    words, times = paced(lines)
    text = LunaText(cap_dollars=float(req.get("cap_dollars", 0.5)))
    records = []
    still_frames: dict[str, list[int]] = {}

    def render(shot_path, folder, quality):
        shot = json.loads(Path(shot_path).read_text(encoding="utf-8"))
        total = int(shot["duration"] * shot.get("fps", 24))
        frames = [min(total - 1, int(total * p)) for p in STILL_POINTS]
        still_frames[str(folder)] = frames
        subprocess.run([a.blender_python, str(HERE / "render_shot.py"), shot_path, "--out", str(folder),
                        "--quality", req.get("quality", "video"), "--stills", ",".join(map(str, frames))], check=True)
        subprocess.run([sys.executable, str(HERE / "post.py"), str(folder)], check=True)

    clips = stage.run(out / "3d", req.get("format", "long"), lines, times, words, "\n".join(lines), text,
                      lambda name, output: records.append({"stage": name, "value": output.value}), render=render)

    stills = []
    for clip in clips:
        final = Path(clip["frames"])
        for f in still_frames.get(str(final.parent), []):
            png = final / f"f{f:05d}.png"
            if png.exists():
                stills.append((f"{clip['subject']}  ·  {clip['start']:.0f}-{clip['end']:.0f}s  ·  frame {f}", png))
    if stills:
        contact_sheet(stills, out / "contact-sheet.jpg", f"TRIAL · World 3D · {req['title']}")
    for bp in (out / "3d" / "blueprints").glob("*.json"):
        shutil.copy(bp, out / f"blueprint-{bp.name}")
    report = {"trial": True, "title": req["title"], "shots_rendered": len(clips),
              "subjects": [c["subject"] for c in clips], "stills": len(stills),
              "spent_dollars": round(text.spent, 4), "calls": text.calls, "records": records}
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("shots_rendered", "subjects", "stills", "spent_dollars")}))
    if not stills:
        sys.exit("TRIAL FAILED: no shot rendered")


if __name__ == "__main__":
    main()
