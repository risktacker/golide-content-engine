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


def test_dictionary_and_evidence(tmp_path):
    from golide_engine.quality.spelling import accept_with_evidence, load_dictionary, unknown_words

    policy = _policy()
    flagged = unknown_words(["Plan for crypto agility and a sentnce."], policy, load_dictionary(tmp_path))
    assert flagged == ["crypto", "sentnce"]
    accepted = accept_with_evidence(tmp_path, flagged, {"your recording": "plan for Crypto agility", "the research sources": ""})
    assert accepted == {"crypto": "seen in your recording"}
    assert unknown_words(["crypto agility, a sentnce"], policy, load_dictionary(tmp_path)) == ["sentnce"]


def test_repo_dictionary_knows_crypto():
    from pathlib import Path

    from golide_engine.quality.spelling import load_dictionary

    assert "crypto" in load_dictionary(Path(__file__).resolve().parents[1])
