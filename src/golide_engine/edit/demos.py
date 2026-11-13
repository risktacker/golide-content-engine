"""Real runs on screen (owner 2026-11-13, modelled on Outskill): when a story is about a tool, a repo or a model,
the engine RUNS it and shows the real run in a terminal: the command typed, the real output streaming in with its
real timing, the line that matters highlighted. Nothing is mocked: the output is whatever the run printed.

Safety: the commands come from a model, so only a short list of read-only forms is allowed (cloning a public GitHub
repo and reading it, a package's --help or --version, one AI model question through our own key). No pipes, no
redirects, no chaining; each runs in an empty temp folder with a stripped environment and a time limit.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

DEMO_SCHEMA = {
    "type": "object",
    "properties": {"demos": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "purpose": {"type": "string"},
            "commands": {"type": "array", "items": {"type": "string"}},
            "highlight": {"type": "string"},
        },
        "required": ["purpose", "commands", "highlight"], "additionalProperties": False}}},
    "required": ["demos"], "additionalProperties": False,
}

INSTRUCTIONS = (
    "You plan real terminal demos for a YouTube explainer, so the viewer sees the thing the story talks about "
    "actually working, not a description of it. Plan 0 to 3 demos, each 1 to 4 commands run in an empty folder, "
    "using ONLY these forms (anything else is refused):\n"
    "- git clone --depth 1 https://github.com/OWNER/REPO   (a public repo the story or research names)\n"
    "- ls [-la] [PATH] | find PATH -maxdepth 2 -type f | cat FILE | head -n N FILE | wc -l FILE | grep -n WORD FILE "
    "(inside what was cloned)\n"
    "- pip install PACKAGE  then  PACKAGE-COMMAND --help | --version\n"
    "- npx --yes PACKAGE --help | --version\n"
    "- ai MODEL \"QUESTION\"   (asks an OpenAI model one short question and prints its real answer; only when the "
    "story is about that model or about what such a model can do; at most one per video)\n"
    "No pipes, redirects, &&, ; or $(). purpose: what the viewer sees, in 4 to 8 words (\"Cloning the REA toolkit\"). "
    "highlight: a short piece of text you expect in the output that proves the point (a file name, a version, a "
    "word of the answer). Plan none when nothing in the story can honestly be run.")

ALLOWED_MODELS = ("gpt-",)
LINE_LIMIT, COLS = 60, 140


def request(title: str, script: str, research: dict[str, Any]) -> str:
    claims = "\n".join(f"- {c.get('claim', '')} ({c.get('source_url', '')})" for c in (research.get("claims") or [])[:30])
    return f"TITLE: {title}\n\nSCRIPT\n{script}\n\nRESEARCH\n{claims}"


def allowed(command: str) -> list[str] | None:
    """The command as arguments when it is one of the allowed read-only forms, else None."""
    if re.search(r"[|;&<>`$\\]", command):
        return None
    try:
        a = shlex.split(command)
    except ValueError:
        return None
    if not a:
        return None
    safe = lambda s: bool(re.fullmatch(r"[\w./@:+-]+", s)) and ".." not in s and not s.startswith("/")
    head = a[0]
    if head == "git":
        return a if (len(a) == 5 and a[1:4] == ["clone", "--depth", "1"]
                     and re.fullmatch(r"https://github\.com/[\w.-]+/[\w.-]+(\.git)?", a[4])) else None
    if head == "ls":
        return a if len(a) <= 3 and all(safe(x) for x in a[1:]) else None
    if head == "find":
        return a if (len(a) == 6 and safe(a[1]) and a[2:5] == ["-maxdepth", "2", "-type"] and a[5] == "f") else None
    if head in ("cat", "wc"):
        rest = a[1:] if head == "cat" else [x for x in a[1:] if x != "-l"]
        return a if len(rest) == 1 and safe(rest[0]) else None
    if head == "head":
        return a if len(a) == 4 and a[1] == "-n" and a[2].isdigit() and int(a[2]) <= 60 and safe(a[3]) else None
    if head == "grep":
        return a if len(a) == 4 and a[1] == "-n" and re.fullmatch(r"[\w .:-]{1,40}", a[2]) and safe(a[3]) else None
    if head == "pip":
        return a if len(a) == 3 and a[1] == "install" and re.fullmatch(r"[\w.-]{1,60}", a[2]) else None
    if head == "npx":
        return a if (len(a) == 4 and a[1] == "--yes" and re.fullmatch(r"(@[\w.-]+/)?[\w.-]{1,60}", a[2])
                     and a[3] in ("--help", "--version")) else None
    if head == "ai":
        return a if len(a) == 3 and a[1].startswith(ALLOWED_MODELS) and len(a[2]) <= 300 else None
    if len(a) == 2 and a[1] in ("--help", "--version") and re.fullmatch(r"[\w.-]{1,40}", head):
        return a                    # the command a package just installed
    return None


def _ask(model: str, question: str, ask) -> list[str]:
    answer = ask(model, question)
    out = []
    for para in str(answer).splitlines():
        while len(para) > COLS:
            cut = para.rfind(" ", 0, COLS)
            out.append(para[:cut if cut > 40 else COLS])
            para = para[cut if cut > 40 else COLS:].lstrip()
        out.append(para)
    return out[:LINE_LIMIT]


def run(demos: list[dict[str, Any]], ask=None, per_command: float = 90.0) -> list[dict[str, Any]]:
    """Run the planned demos for real and keep what they printed, line by line with the time it appeared."""
    done = []
    ai_used = False
    for demo in demos[:3]:
        folder = Path(tempfile.mkdtemp(prefix="golide-demo-"))
        venv = folder / ".venv"
        env = {"PATH": f"{venv / 'bin'}:/usr/local/bin:/usr/bin:/bin", "HOME": str(folder), "LANG": "C.UTF-8",
               "TERM": "dumb", "NO_COLOR": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "npm_config_yes": "true"}
        steps = []
        try:
            for command in demo.get("commands", [])[:4]:
                args = allowed(command)
                if args is None:
                    steps = []
                    break
                start = time.monotonic()
                lines: list[dict[str, Any]] = []
                ok = True
                if args[0] == "ai":
                    if ai_used or ask is None:
                        steps = []
                        break
                    ai_used = True
                    try:
                        answer = _ask(args[1], args[2], ask)
                    except Exception:  # noqa: BLE001 - an unknown model or a failed call: this demo is dropped
                        steps = []
                        break
                    for text in answer:
                        lines.append({"t": round(time.monotonic() - start, 3), "text": text})
                else:
                    if args[0] not in ("git", "ls", "find", "cat", "wc", "head", "grep", "pip", "npx") and \
                            not (venv / "bin" / args[0]).exists():
                        steps = []           # a --help/--version only for a command this demo just installed
                        break
                    if args[0] == "pip" and not venv.exists():
                        subprocess.run(["python3", "-m", "venv", str(venv)], check=True, capture_output=True)
                    if args[0] == "pip":
                        args = [str(venv / "bin" / "pip")] + args[1:]
                    proc = subprocess.Popen(args, cwd=folder, env=env, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, text=True, errors="replace")
                    try:
                        for raw in proc.stdout:      # type: ignore[union-attr]
                            if time.monotonic() - start > per_command:
                                proc.kill()
                                break
                            if len(lines) < LINE_LIMIT:
                                lines.append({"t": round(time.monotonic() - start, 3), "text": raw.rstrip()[:COLS]})
                        ok = proc.wait(timeout=10) == 0
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        ok = False
                steps.append({"command": command, "lines": lines, "seconds": round(time.monotonic() - start, 2),
                              "ok": ok})
                if not ok:
                    break
        finally:
            shutil.rmtree(folder, ignore_errors=True)
        if steps and any(s["lines"] for s in steps):
            done.append({"purpose": demo.get("purpose", ""), "highlight": demo.get("highlight", ""), "steps": steps,
                         "ok": all(s["ok"] for s in steps)})
    return done


def listing(demos: list[dict[str, Any]]) -> str:
    """The real runs, for the editor (it places them on the beats they prove)."""
    rows = []
    for i, d in enumerate(demos):
        out = [ln["text"] for s in d["steps"] for ln in s["lines"] if ln["text"].strip()]
        rows.append(f"[{i}] {d['purpose']} ({'worked' if d['ok'] else 'stopped'}): "
                    + " | ".join(f"$ {s['command']}" for s in d["steps"])
                    + "\n    output: " + " / ".join(out[:8])[:400])
    return "\n".join(rows)


def scene_data(demo: dict[str, Any], phrase: str | None) -> dict[str, Any]:
    want = (phrase or demo.get("highlight") or "").lower()
    rows, mark = [], None
    for s in demo["steps"]:
        rows.append({"kind": "cmd", "text": s["command"], "t": 0.0})
        for ln in s["lines"]:
            rows.append({"kind": "out", "text": ln["text"], "t": ln["t"]})
            if want and want in ln["text"].lower():
                mark = len(rows) - 1          # the last line that shows it: the one still on screen
    return {"title": demo["purpose"], "rows": rows, "mark": mark, "ok": demo["ok"]}


def openai_asker():
    """One short question to an OpenAI model through our own key (printed as the real answer)."""
    from openai import OpenAI
    client = OpenAI()

    def ask(model: str, question: str) -> str:
        r = client.responses.create(model=model, input=question, max_output_tokens=300)
        return r.output_text
    return ask


def save(demos: list[dict[str, Any]], path: Path) -> None:
    path.write_text(json.dumps(demos, indent=2) + "\n", encoding="utf-8")
