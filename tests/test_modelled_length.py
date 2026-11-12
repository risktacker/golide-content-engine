"""Owner direction 2026-11-10: every long read lands at 8 to 9 minutes (replaces "as long as the model")."""

from golide_engine.engine.content_rules import (chapter_problems, chapter_range, length_problems,
                                                length_target, script_instructions)


def test_long_reads_land_at_5_to_6_minutes_whatever_the_model():
    for model in (60, 200, 300, 3600, None):
        t = length_target("long", model)
        assert 700 <= t["words_min"] and t["words_max"] <= 920    # 2026-11-12 owner: 5 to 6 minutes (v3 budget)
    assert length_target("short", 20)["words_min"] == 105         # 2026-11-12 owner: 45-second shorts


def test_short_long_video_gets_fewer_chapters_and_is_checked_against_its_own_length():
    assert chapter_range("long", 200) == (3, 4)
    plan = {"chapters": [{"number": ""}, {"number": "01"}, {"number": "02"}, {"number": ""}],
            "lines": [{"text": " ".join(["word"] * 90), "chapter": i} for i in range(4)]}
    assert length_problems(plan, "long", 200)                     # 360 words is far too short
    long_plan = {"lines": [{"text": " ".join(["word"] * 210), "chapter": i} for i in range(4)]}
    assert length_problems(long_plan, "long", 200) == []
    too_long = {"lines": [{"text": " ".join(["word"] * 300), "chapter": i} for i in range(4)]}
    assert "too long" in length_problems(too_long, "long", 200)[0]
