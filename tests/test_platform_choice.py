"""2026-11-04 (owner): each video goes only to the platforms he ticked."""
from golide_engine.orchestration.reels import chosen_platforms, keep_variants, long_social_payload, reels_payload

META = {"title": "T", "description": "d"}


def test_no_choice_means_everywhere():
    assert chosen_platforms({}) == {"youtube", "instagram", "facebook", "linkedin"}
    assert chosen_platforms({"platforms": ["none"]}) == set()
    assert chosen_platforms({"platforms": ["linkedin", "x"]}) == {"linkedin"}


def test_short_keeps_only_chosen():
    p = reels_payload(content_id="c", metadata=META, video_ref="r2://v", cover_ref=None,
                      youtube_video_id="", owner_voice_ref="")
    kept = keep_variants(p, {"instagram", "linkedin", "youtube"}, "")
    assert [v["platform"] for v in kept["variants"]] == ["instagram", "linkedin"]   # no YouTube id: not recorded


def test_long_everywhere_unchanged():
    p = long_social_payload(content_id="c", metadata=META, video_ref="r2://v", youtube_video_id="abc",
                            owner_voice_ref="", publish_at="2026-11-05T17:30:00Z")
    kept = keep_variants(p, None, "abc")
    assert {v["platform"] for v in kept["variants"]} == {"youtube", "facebook", "linkedin", "instagram"}
