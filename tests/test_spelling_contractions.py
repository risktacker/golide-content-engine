from golide_engine.quality.spelling import _spellcheck_words


def test_ascii_and_smart_apostrophe_contractions_are_not_spellchecked():
    text = (
        "aren't didn’t doesn’t hasn’t isn’t "
        "we're we’re they're they’re can't can’t won't won’t"
    )

    words = _spellcheck_words(text)

    assert "aren" not in words
    assert "didn" not in words
    assert "doesn" not in words
    assert "hasn" not in words
    assert "isn" not in words
    assert "aren't" not in words
    assert "isn't" not in words


def test_plain_words_remain_available_for_spellcheck():
    words = _spellcheck_words("A clear scientific explanation of visual motion")

    assert {"clear", "scientific", "explanation", "visual", "motion"} <= words
