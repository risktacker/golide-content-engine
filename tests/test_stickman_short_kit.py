"""2026-11-18 (owner, after the fast-cut Elon test): Stickman Shorts get our world kit (real logos, city, cash, karts,
Earth, satellites, signposts), our cast kit (chunky modern puppets) and the fast-pace story rules."""
import json

from golide_engine.stickman import logos, short


def _pkg(tmp_path):
    (tmp_path / "_data").mkdir()
    (tmp_path / "icons").mkdir()
    icons = [{"title": "Google", "hex": "4285F4"}, {"title": "OpenAI", "hex": "412991"},
             {"title": "X", "hex": "000000", "aliases": {"aka": ["Twitter"]}}, {"title": "NVIDIA", "hex": "76B900"}]
    (tmp_path / "_data" / "simple-icons.json").write_text(json.dumps(icons))
    for slug in ("google", "openai", "x", "nvidia"):
        (tmp_path / "icons" / f"{slug}.svg").write_text(f'<svg><path d="M0 0h{len(slug)}"/></svg>')
    return tmp_path


def test_the_logos_of_the_brands_the_script_names(tmp_path):
    found = logos.for_script("You co-founded OpenAI. Google is ahead. You bought Twitter. Nvidia can't keep up.", _pkg(tmp_path))
    assert list(found) == ["openai", "google", "x", "nvidia"]          # in the order the script names them
    assert found["google"] == {"d": "M0 0h6", "hex": "4285F4", "title": "Google"}
    assert "x" not in logos.for_script("an x in a word", tmp_path)          # a name under 3 letters matches only by its other names


def test_the_project_carries_both_kits_and_the_logos(tmp_path):
    parts = {"world_js": "const DECK = 6;", "world_state_js": "function worldState(S, f) { waterU.t.value = f / 30; }",
             "story_js": "export const TOTAL = 1;", "cast_js": "", "logos": {"google": {"d": "M0 0", "hex": "4285F4", "title": "Google"}},
             "music_end": 1, "cues_py": ""}
    try:
        short.build_project(tmp_path, parts, {"words": [], "phrases": {"frames30": 30, "phrases": []}})
    except Exception:       # the sound step needs a full plan; the web files are written before it
        pass
    main = (tmp_path / "web" / "main.js").read_text()
    assert 'const LOGO = {"google"' in main and "const signBoard" in main and "const cashBlock" in main
    assert main.index("const LOGO") < main.index("const signBoard") < main.index("const DECK = 6;")
    toon = (tmp_path / "web" / "toon.js").read_text()
    assert "export const modernFront" in toon and "export const billFx" in toon


def test_the_writer_gets_the_fast_pace_logo_and_city_rules():
    rules = short.instructions()
    for piece in ("one shot per phrase", "REAL logos", "T.modernFront", "cashBlock", "signPost", "satellite",
                  "brainstorm", "city"):
        assert piece in rules, piece
    assert "and no brand logos" not in rules
    ask = short.request("T", short.phrases([{"word": "Google.", "start": 0.0, "end": 0.5}], 1.0),
                        logos={"google": {"d": "", "hex": "", "title": "Google"}})
    assert "REAL LOGOS READY" in ask and "google: Google" in ask


def test_the_kits_parse_as_javascript():
    """A stray comment once swallowed a loop and broke every Short: both kits must parse."""
    import shutil, subprocess
    from pathlib import Path
    if not shutil.which("node"):
        return
    root = Path(__file__).resolve().parents[1] / "src" / "golide_engine" / "stickman" / "short_kit"
    world = (root / "world-kit.js").read_text()
    subprocess.run(["node", "-e", "new Function(require('fs').readFileSync(0, 'utf8'))"], input=world, text=True, check=True)
    cast = (root / "cast-kit.js").read_text().replace("export const ", "const ")
    subprocess.run(["node", "-e", "new Function(require('fs').readFileSync(0, 'utf8'))"], input=cast, text=True, check=True)
