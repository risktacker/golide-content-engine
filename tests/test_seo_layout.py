"""2026-10-13: summary, 10+ keywords, chapters, hashtags; more than 20 tags."""
from golide_engine.vector.chapters import with_chapters
from golide_engine.youtube_metadata import compose_description, fit_tags, social_caption

KEYS = ["AI agents", "Gemini agent", "Google AI", "AI at work", "automation tools", "AI news", "tech news",
        "AI productivity", "workplace AI", "AI assistant", "Google Workspace AI", "AI safety"]
TAGS = ["ai", "gemini"]


def test_description_order_with_chapters():
    desc = compose_description("Para one.\n\nPara two.\n#old", KEYS, ["AI", "#TechNews", "Gemini agent"])
    full = with_chapters(desc, ["00:00 Intro", "00:40 01 What it is", "02:10 02 Steps"])
    rows = [r for r in full.split("\n\n") if r]
    assert rows[0] == "Para one." and rows[1] == "Para two."
    assert rows[2].count(",") >= 9                      # keywords line
    assert rows[3].startswith("Chapters")               # timestamps after keywords
    assert rows[4] == "#AI #TechNews #Geminiagent"      # hashtags last
    assert "#old" not in full


def test_more_than_twenty_tags_within_limit():
    tags = fit_tags(TAGS, KEYS)
    assert len(tags) > 20
    assert sum(map(len, tags)) + len(tags) - 1 <= 500


def test_social_caption_keeps_keywords_and_hashtags_when_trimmed():
    meta = {"seo_body": "word " * 1000, "keywords": KEYS, "hashtags": ["AI", "Tech"], "chapters": []}
    cap = social_caption("Title", meta, 2200)
    assert len(cap) <= 2200 and cap.endswith("#AI #Tech") and "AI agents, Gemini agent" in cap


def test_static_posts_get_keywords_and_hashtags():
    from golide_engine.orchestration.static_automation import add_seo
    copies = {"instagram": "Hook.\n\nBody.", "facebook": "Hook.", "linkedin": "Hook.", "x": "Short post."}
    out = add_seo(copies, KEYS, ["CanvaAI", "AI", "TechNews", "Design", "Automation"])
    for p in ("instagram", "facebook", "linkedin"):
        assert out[p].endswith("#CanvaAI #AI #TechNews #Design #Automation")
        assert "AI agents, Gemini agent" in out[p]
    assert out["x"].endswith("#CanvaAI #AI")
