"""Owner direction 2026-11-01: a long video is as long as the video it models (3 to 8 minutes)."""

from golide_engine.engine.content_rules import (chapter_problems, chapter_range, length_problems,
                                                length_target, script_instructions)


def test_length_follows_the_model_within_3_to_8_minutes():
    assert length_target("long", 200)["words_max"] < 650          # a 3-minute model: a 3-minute script
    assert length_target("long", 300)["words_max"] < 900          # 5 minutes
    assert length_target("long", 3600)["words_max"] <= 1420       # never past 8 minutes
    assert length_target("long", 60)["words_min"] >= 480          # never under 3 minutes
    assert length_target("long", None)["words_min"] == 1300       # no model: the old default
    assert length_target("short", 20)["words_min"] == 150         # shorts unchanged


def test_short_long_video_gets_fewer_chapters_and_is_checked_against_its_own_length():
    assert chapter_range("long", 200) == (2, 3)
    plan = {"chapters": [{"number": ""}, {"number": "01"}, {"number": "02"}, {"number": ""}],
            "lines": [{"text": " ".join(["word"] * 140), "chapter": i} for i in range(4)]}
    assert length_problems(plan, "long", 200) == []
    assert length_problems(plan, "long", 480)                     # too short for an 8-minute model
    assert chapter_problems(plan, "long", 200) == []
    assert "2 to 3 numbered chapters" in script_instructions("long", "x", 200)
