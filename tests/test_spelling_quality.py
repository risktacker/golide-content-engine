from golide_engine.quality.spelling import _spellcheck_words, check_spelling


def _policy():
    return {
        "spelling": {
            "ignore": ["saccades", "vestibulo"],
        }
    }


def test_spellcheck_words_skips_expected_non_dictionary_tokens():
    words = _spellcheck_words(
        "It isn't something we didn't expect. #AnimalScience vestibulo-ocular saccades"
    )
    assert "isn't" not in words
    assert "didn't" not in words
    assert "animalscience" not in words
    assert "vestibulo" not in words
    assert "ocular" not in words
    assert "saccades" in words


def test_spelling_accepts_contractions_hashtags_and_scientific_terms():
    failures = check_spelling(
        ["It isn't something we didn't expect. #AnimalScience vestibulo-ocular saccades"],
        _policy(),
    )
    assert failures == []


def test_spelling_still_flags_plain_misspelling():
    failures = check_spelling(["This sentnce has a typo."], _policy())
    assert "possible misspelling: sentnce" in failures
