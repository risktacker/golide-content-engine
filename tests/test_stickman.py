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
    assert "chapter cards" in rules and "never invented" in rules and "never a likeness" in rules


def test_plan_warnings_are_read_from_the_kits_output():
    out = "#  0 wide ...\nWARNING: sentence 4 is not covered\nWARNING: cue word 'fortune' not found in shot 3\n"
    assert longform.warnings(out) == ["sentence 4 is not covered", "cue word 'fortune' not found in shot 3"]


def test_the_kit_is_vendored_unchanged():
    assert (longform.KIT / "engine" / "shots.py").exists() and (longform.KIT / "CREDITS.md").exists()
    assert "ReachMora" in (longform.KIT / "SKILL.md").read_text(encoding="utf-8")


def test_captions_move_with_the_chapter_card_pauses():
    srt = "1\n00:00:01,000 --> 00:00:02,000\nhello there\n\n2\n00:00:12,500 --> 00:00:13,000\nlater on\n"
    out = longform.shift_srt(srt, [(10.0, 1.6)])
    assert "00:00:01,000 --> 00:00:02,000" in out and "00:00:14,100 --> 00:00:14,600" in out


def test_the_kits_timeline_gives_the_pauses(tmp_path):
    import json
    script = "One two three. Four five six.\n"
    doc = longform.timing(script, _words(script), 3.0)
    (tmp_path / "timing.json").write_text(json.dumps(doc))
    (tmp_path / "story.json").write_text(json.dumps({"shots": [{"kind": "wide", "s": [0]}, {"kind": "title", "text": "Two"},
                                                               {"kind": "wide", "s": [1]}]}))
    pauses = longform.gaps(tmp_path)
    assert len(pauses) == 1 and pauses[0][1] == 1.6


def test_unknown_icons_become_the_nearest_kit_icon_or_are_left_out():
    """2026-11-17: 'receipt' stopped the Nvidia render; an icon name is now always one the kit draws."""
    from golide_engine.stickman import longform
    known = longform.kit_icons()
    assert {"bulb", "moneybag", "chart_up", "shopping", "warning"} <= known and "receipt" not in known
    story = {"shots": [
        {"kind": "icon", "icons": [{"name": "receipt", "label": "PAID", "at": "paid"}, {"name": "bulb", "at": "x"}]},
        {"kind": "wide", "props": [{"icon": "gpu", "x": 1500}, {"icon": "zzqx", "x": 900}],
         "bubble": {"who": "a", "text": "hm", "icon": "spy"}, "chars": [{"id": "a", "name": "ignored"}]},
        {"kind": "counter", "compare": {"text": "6 YEARS", "icon": "home", "at": "w"}}]}
    changed = longform.fix_icons(story, known)
    assert story["shots"][0]["icons"][0]["name"] == "shopping" and story["shots"][0]["icons"][1]["name"] == "bulb"
    assert [p["icon"] for p in story["shots"][1]["props"]] == ["laptop"]          # the unknown prop is left out
    assert story["shots"][1]["bubble"]["icon"] == "warning" and story["shots"][2]["compare"]["icon"] == "house"
    assert story["shots"][1]["chars"][0]["name"] == "ignored" and len(changed) == 5
