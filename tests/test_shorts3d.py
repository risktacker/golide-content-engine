"""3D Shorts engine wiring (owner 2026-11-22): the hook, the scene words and the lower-third captions."""
import subprocess
import sys
from pathlib import Path

from golide_engine.shorts3d import build
from golide_engine.stickman import captions

HOOK = Path(build.ASSETS) / "hook.py"


def test_hook_adds_one_branch(tmp_path):
    main = tmp_path / "main.js"
    main.write_text("x\n  if (!Q.has('skit')) loop(); else {\ny\n", encoding="utf-8")
    subprocess.run([sys.executable, str(HOOK), str(main)], check=True)
    src = main.read_text(encoding="utf-8")
    assert src.count("golide/scene.js") == 1 and "else if (!Q.has('skit')) loop(); else {" in src


def test_hook_refuses_a_changed_engine(tmp_path):
    main = tmp_path / "main.js"
    main.write_text("nothing to hook\n", encoding="utf-8")
    assert subprocess.run([sys.executable, str(HOOK), str(main)]).returncode != 0


def test_scene_words_cut_at_the_opening():
    words = [{"word": "a", "start": 0.1, "end": 0.2}, {"word": "b", "start": 9.12, "end": 9.3}]
    assert [w["word"] for w in build.scene_words(words, 9.1)] == ["a"]


def test_short3d_captions_two_words_lower_third():
    lines = captions.chunks([{"word": w, "start": i * 0.3, "end": i * 0.3 + 0.25} for i, w in enumerate("one two three four.".split())],
                            None, captions.WORDS["short3d"])
    assert all(len(c["words"]) <= 2 for c in lines)
    text = captions.ass(lines, "short3d", *captions.FRAME["short3d"])
    assert "PlayResY: 1920" in text and ",330,1" in text


def test_assets_present():
    for f in ("scene.js", "director.js", "render.cjs", "chipmaker-open.js"):
        assert (build.ASSETS / f).exists()
