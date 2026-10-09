"""2026-10-09: spelling and speech-recognition doubts never stop a video."""
from golide_engine.captions import respell_from_script


def w(word, start):
    return {"word": word, "start": start, "end": start + 0.3}


def test_misheard_word_takes_the_script_spelling():
    heard = [w("does", 0), w("the", 0.4), w("mats", 0.8), w("and", 1.2), w("Gemmini", 1.6), w("writes", 2.0)]
    fixed = respell_from_script(heard, "does the maths, and Gemini writes the draft.")
    assert [x["word"] for x in fixed] == ["does", "the", "maths", "and", "Gemini", "writes"]
    assert fixed[2]["start"] == 0.8


def test_one_misheard_word_split_in_two_is_rejoined():
    heard = [w("ask", 0), w("go", 0.4), w("lied", 0.7), w("today", 1.1)]
    fixed = respell_from_script(heard, "ask GOLIDE today")
    assert [x["word"] for x in fixed] == ["ask", "GOLIDE", "today"]


def test_spelling_is_a_warning_not_a_failure(tmp_path):
    from golide_engine.quality.spelling import check_spelling
    assert check_spelling(["the recieve step"], {"spelling": {"ignore": []}}) == ["possible misspelling: recieve"]
    import inspect
    from golide_engine.quality import runner
    assert "warnings = check_spelling" in inspect.getsource(runner.QualityRunner.run)
