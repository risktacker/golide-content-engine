"""The edit engine inside the daily production run (steps 1 to 5 of the 2026-11-11 plan).

Switched per format in config/edit-engine.json. When on, it replaces the drawn-illustration path
(visual plan, generated pictures, vector render) for that format; everything before (research,
script, the owner's recording) and after (thumbnail, metadata, upload) is unchanged.

Stages, each checkpointed like the rest of the run:
- sources-capture-v1: every research page opened, screenshotted, claims located, faces blurred.
- lipsync-v1: Goli's mouth cues from the recording.
- edit-plan-v1: the editor model call (one text call).
- render-edit-v1: HyperFrames render plus the audio mix.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]


def settings() -> dict[str, Any]:
    path = ROOT / "config/edit-engine.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def enabled(fmt: str, spec: dict[str, Any] | None = None) -> bool:
    """The owner's choice for this video (Studio: Video style) wins; otherwise the default for the format."""
    style = str((spec or {}).get("video_style") or "").lower()
    if style in ("goli", "illustration"):
        return style == "goli"
    return bool(settings().get(fmt))


def outfit_today() -> str:
    from .mascot import outfit_for

    return outfit_for(datetime.now(ZoneInfo("Africa/Lusaka")).date())


def logo_tile_maker(folder: Path):
    """brand name -> path of a glossy 3D logo tile (Simple Icons, CC0), or None when unknown."""
    folder.mkdir(parents=True, exist_ok=True)

    def make(name: str) -> Path | None:
        from ..vector import logos, thumb_styles

        icon = logos.find(name)
        if not icon:
            return None
        target = folder / f"{logos.slug(name)}.png"
        if not target.exists():
            image = thumb_styles.render_tiles({"w": 520, "h": 520, "fov": 30, "dist": 9,
                                               "items": [thumb_styles._tile(icon, pos=[0, 0, 0], rot=[10, -18, 0], size=3.4)]})
            image.crop(image.getbbox()).save(target)
        return target

    return make


def run(production, spec: dict[str, Any], work: Path, production_id: str, plan: dict[str, Any],
        timed_words: list[dict[str, Any]], narration: Path, narration_seconds: float, video_path: Path,
        text, text_model: str, research: dict[str, Any]) -> dict | None:
    """Make the day's video with the edit engine. Returns the music track used (for the ledger)."""
    from ..operations.costs import Usage
    from ..vector.align import align_lines
    from ..vector.chapters import chapter_marks
    from ..vector.music_bed import pick as pick_music
    from . import editor
    from .render import lipsync, render

    fmt = str(spec["format"])
    folder = work / "edit"
    folder.mkdir(parents=True, exist_ok=True)
    capture_dir = folder / "sources"
    sources_log = capture_dir / "sources.json"

    def capture_stage():
        from ..engine.source_capture import capture
        capture(research, capture_dir)

    production.runner.run(production_id, "sources-capture-v1", capture_stage, attempts=1)
    sources = json.loads(sources_log.read_text(encoding="utf-8")) if sources_log.exists() else []

    # 2026-11-13 (owner, modelled on Outskill): the tool the story is about, really run and shown in a terminal
    demos_path = folder / "demos.json"

    def demo_stage():
        from . import demos as demo_runs
        if fmt != "long":
            demo_runs.save([], demos_path)
            return
        content = demo_runs.request(str(spec.get("title", "")), str(plan.get("voice_script") or ""), research)
        production._reserve(spec, text_model, Usage(input_tokens=len(content) // 3 + 1500, output_tokens=2000))
        output = text.generate_json(demo_runs.INSTRUCTIONS, content, demo_runs.DEMO_SCHEMA, max_output_tokens=3000)
        production._record_text(production_id, "demo-plan", output)
        try:
            ask = demo_runs.openai_asker()
        except Exception:  # noqa: BLE001 - no OpenAI client: the AI demo is skipped, the rest still run
            ask = None
        ran = demo_runs.run(list(output.value.get("demos") or []), ask)
        demo_runs.save(ran, demos_path)
        print(json.dumps({"status": "demos", "planned": len(output.value.get("demos") or []), "ran": len(ran),
                          "what": [d["purpose"] for d in ran]}))

    try:
        production.runner.run(production_id, "demos-v1", demo_stage, attempts=1)
    except Exception as error:  # noqa: BLE001 - a demo that cannot run never stops the video
        print(json.dumps({"status": "demos_failed", "error": str(error)[:300]}))
    demo_list = json.loads(demos_path.read_text(encoding="utf-8")) if demos_path.exists() else []

    cues_path = folder / "mouth-cues.json"
    production.runner.run(production_id, "lipsync-v1", lambda: lipsync(narration, cues_path), attempts=1)
    cues = json.loads(cues_path.read_text(encoding="utf-8"))

    lines = align_lines(plan, timed_words, narration_seconds)
    marks = chapter_marks(plan, lines) if plan.get("chapters") else []
    (work / "chapters.json").write_text(json.dumps(
        [{"start": m.start, "number": m.number, "title": m.title} for m in marks], indent=2) + "\n", encoding="utf-8")
    spoken = [line for line in plan.get("lines", []) if str(line.get("text", "")).strip()]
    follow_lines = {i for i, line in enumerate(spoken) if line.get("follow") is True}
    # 2026-11-11 (owner): a picture per beat of about two seconds, each showing what that beat says
    beat_lines = editor.beats(lines, fmt)
    follow = {b.index for b in beat_lines for i in follow_lines
              if i < len(lines) and lines[i].start - 0.01 <= b.start <= lines[i].end}
    raw_path = folder / "edit-plan-raw-v2.json"     # v2: planned per beat (2026-11-11)

    def plan_stage():
        production._require_absent(raw_path, "edit-plan")
        content = editor.request(str(spec.get("title", "")), beat_lines, sources, marks, follow, demo_list)
        out_tokens = min(60000, 6000 + 260 * len(beat_lines))
        production._reserve(spec, text_model, Usage(input_tokens=len(content) // 3 + 3000, output_tokens=out_tokens))
        output = text.generate_json(editor.instructions(fmt), content, editor.EDIT_SCHEMA, max_output_tokens=out_tokens)
        production._record_text(production_id, "edit-plan", output)
        raw_path.write_text(json.dumps(output.value, indent=2) + "\n", encoding="utf-8")

    production.runner.run(production_id, "edit-plan-v2", plan_stage)
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    bookends = None
    if fmt == "long":        # 2026-11-12 (owner): seven openings, five endings, never the same as the last videos
        picked = folder / "bookends.json"
        if not picked.exists():
            used = []
            for path in (ROOT / "data" / "production-records").glob("*.json"):
                try:
                    params = json.loads(path.read_text(encoding="utf-8")).get("generation_parameters") or {}
                    rec = json.loads(path.read_text(encoding="utf-8")).get("recorded_at", "")
                except (OSError, ValueError, AttributeError):
                    continue
                if isinstance(params, dict) and params.get("intro"):
                    used.append((str(rec), params["intro"], params.get("outro", "")))
            used.sort(reverse=True)
            intro, outro = editor.pick_bookends(str(spec.get("title", "")), [u[1] for u in used], [u[2] for u in used],
                                                len(used))
            picked.write_text(json.dumps({"intro": intro, "outro": outro}) + "\n", encoding="utf-8")
        chosen = json.loads(picked.read_text(encoding="utf-8"))
        bookends = (chosen["intro"], chosen["outro"])
        print(json.dumps({"status": "edit_bookends", **chosen}))
    edit = editor.build(raw, beat_lines, narration_seconds, fmt, sources, capture_dir, cues, marks,
                        logo_tile_maker(folder / "logos"), bookends=bookends, demos=demo_list)
    edit["title"] = str(spec.get("title", ""))
    editor.save(edit, folder / "edit-list.json")
    for note in edit["notes"]:
        print(f"::notice title=Editor::{note}")
    print(json.dumps({"status": "edit_list", "scenes": len(edit["scenes"]),
                      "types": sorted({s["type"] for s in edit["scenes"]})}))

    track_path = work / "music.json"

    def render_stage():
        rendered_before = production.database.rows(
            "SELECT COUNT(DISTINCT production_id) n FROM stage_runs WHERE stage IN ('render-vector-v1','render-edit-v1') "
            "AND status='completed' AND production_id<>?", (production_id,))
        n = int(rendered_before[0]["n"]) if rendered_before else None
        track = pick_music(fmt, n, f"{plan.get('title', '')} {spec.get('title', '')}")
        track_path.write_text(json.dumps(track or {}) + "\n", encoding="utf-8")
        outfit = outfit_today()
        print(json.dumps({"status": "edit_render", "outfit": outfit, "music": (track or {}).get("title", "bed")}))
        render(edit, folder, narration, video_path, outfit, track)

    production.runner.run(production_id, "render-edit-v1", render_stage, attempts=1)

    def remix_stage():
        """2026-11-12: the sound is mixed again over the finished pictures (no new render) with the
        -2 dBFS limiter, so a video rendered before that change still passes the loudness check."""
        from .render import mix
        track = json.loads(track_path.read_text(encoding="utf-8")) if track_path.exists() else None
        mix(edit, folder, narration, video_path, video_path, track or None, copy_video=True)

    production.runner.run(production_id, "mix-edit-v3", remix_stage, attempts=1)   # v3: true-peak safe
    labels = video_path.with_name("visual-labels.srt")
    if not labels.exists():
        from ..captions import words_to_srt
        labels.write_text(words_to_srt([{"word": s["type"].replace("_", " ").upper(), "start": s["start"],
                                         "end": s["start"] + s["duration"]} for s in edit["scenes"]]), encoding="utf-8")
    return json.loads(track_path.read_text(encoding="utf-8")) if track_path.exists() else None
