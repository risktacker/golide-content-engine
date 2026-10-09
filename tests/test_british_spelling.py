from golide_engine.quality.spelling import unknown_words

POLICY = {"spelling": {"ignore": []}}


def test_british_spellings_pass_and_real_typos_do_not():
    text = ["It does the maths, organises the colour of every programme in the centre, analyses travelled data"]
    assert unknown_words(text, POLICY) == []
    assert unknown_words(["It does the mathz and the recieve step"], POLICY) == ["mathz", "recieve"]
