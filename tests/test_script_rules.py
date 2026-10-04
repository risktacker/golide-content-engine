from golide_engine.engine.content_rules import (
    SCRIPT_SCHEMA, VISUAL_CUES, script_instructions, script_text,
)


def test_short_and_long_targets_sit_inside_recording_windows():
    short = script_instructions("short")
    long = script_instructions("long")
    assert "150 to 185 spoken words" in short
    assert "600 to 680 spoken words" in long
    for rules in (short, long):
        assert "CLAIM" in rules and "CALL TO ACTION" in rules
        assert "own voice" in rules
        assert "ElevenLabs" not in rules


def test_every_line_carries_a_visual_cue_from_the_fixed_library():
    line = SCRIPT_SCHEMA["properties"]["lines"]["items"]
    assert line["properties"]["visual"]["enum"] == list(VISUAL_CUES)
    assert set(line["required"]) >= {"text", "emphasis", "visual"}


def test_owner_reads_only_spoken_words():
    plan = {"title": "t", "lines": [
        {"section": "claim", "text": "AI doesn't decide who gets hired.", "emphasis": "AI",
         "visual": "dot_field", "label": "RANDOM"},
        {"section": "claim", "text": "Systems do.", "emphasis": "Systems",
         "visual": "grid", "label": "DECIDED"},
    ]}
    assert script_text(plan) == "AI doesn't decide who gets hired.\nSystems do."
