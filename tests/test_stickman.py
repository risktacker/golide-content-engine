"""2026-11-17 (owner): Stickman, the third visual style. Long videos run the ReachMora engine unchanged."""
from golide_engine.stickman import longform


def _words(text, gap=0.4):
    out, t = [], 0.2
    for w in text.split():
        out.append({"word": w, "start": t, "end": t + gap - 0.05})
        t += gap
    return out


def test_timing_is_the_kits_format_built_from_our_spoken_words():
    script = "Jensen walked on stage. Then he showed the chip!\n"
    doc = longform.timing(script, _words(script), 4.0)
    assert doc["method"] == "asr" and doc["matched"] == 1.0 and doc["duration"] == 4.0
    first, second = doc["sentences"]
    assert first["text"] == "Jensen walked on stage." and first["words"][0]["n"] == "jensen"
    assert second["start"] > first["end"] - 0.1 and second["words"][-1]["n"] == "chip"


def test_words_the_voice_skipped_are_placed_between_their_neighbours():
    script = "One two three four five.\n"
    spoken = [w for w in _words(script) if w["word"] != "three"]
    doc = longform.timing(script, spoken, 3.0)
    t = [w["t"] for w in doc["sentences"][0]["words"]]
    assert t == sorted(t) and t[1] < t[2] < t[3] and doc["matched"] == 0.8


def test_the_writer_follows_the_kits_story_format_without_silent_cards():
    rules = longform.instructions()
    fmt = (longform.KIT / "references" / "story-format.md").read_text(encoding="utf-8")
    assert fmt in rules
    assert "NO silent title cards" in rules and "never invented" in rules and "never a likeness" in rules


def test_plan_warnings_are_read_from_the_kits_output():
    out = "#  0 wide ...\nWARNING: sentence 4 is not covered\nWARNING: cue word 'fortune' not found in shot 3\n"
    assert longform.warnings(out) == ["sentence 4 is not covered", "cue word 'fortune' not found in shot 3"]


def test_the_kit_is_vendored_unchanged():
    assert (longform.KIT / "engine" / "shots.py").exists() and (longform.KIT / "CREDITS.md").exists()
    assert "ReachMora" in (longform.KIT / "SKILL.md").read_text(encoding="utf-8")
