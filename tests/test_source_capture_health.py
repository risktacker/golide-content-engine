"""Owner 2026-11-25: "if the recorded screen is broken it should not be used but rather another block"."""
from golide_engine.engine.source_capture import broken_page


def test_broken_screens_are_refused_and_good_ones_kept():
    good = {"text": "OpenCode is an open source AI coding agent " * 5, "font": "inter, sans-serif", "sheets": 6,
            "links": 40, "raw": 0, "imgs": 4, "broken": 0, "words": 300, "title": "OpenCode"}
    assert broken_page(good) == ""
    assert "styles" in broken_page(dict(good, sheets=0))
    assert "unstyled" in broken_page(dict(good, raw=38, font='"times new roman"'))
    assert "block" in broken_page(dict(good, title="Just a moment...", text="Verify you are human"))
    assert "block" in broken_page(dict(good, text="404 Not Found"))
    assert "pictures" in broken_page(dict(good, broken=3))
    assert "near empty" in broken_page(dict(good, words=4, imgs=0))
    assert broken_page(None)
