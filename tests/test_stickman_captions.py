from golide_engine.stickman import captions as C


def words(text, step=.3, t0=0.0):
    out, t = [], t0
    for w in text.split():
        out.append({"word": w, "start": round(t, 3), "end": round(t + step - .02, 3)}); t += step
    return out


def test_lines_follow_sentences_and_inkee_length():
    ws = words("Nvidia built a giant campus. Inside, the data centre runs day and night with 400% more chips than before.")
    lines = C.chunks(ws)
    assert [w["text"] for w in lines[0]["words"]] == ["Nvidia", "built", "a", "giant", "campus."]
    assert all(len(c["words"]) <= C.MAX_WORDS for c in lines)
    assert all(a["end"] <= b["start"] for a, b in zip(lines, lines[1:]))          # never two lines at once
    gold = [c["words"][k]["text"] for c in lines for k in c["keys"]]
    assert gold == ["400%"]


def test_chapter_cards_push_the_captions_with_the_voice():
    ws = words("One two three. Four five six.")
    plain, moved = C.chunks(ws), C.chunks(ws, [(0.85, 2.0)])
    assert moved[0]["words"][0]["at"] == plain[0]["words"][0]["at"]
    assert moved[1]["words"][0]["at"] == plain[1]["words"][0]["at"] + 2.0


def test_ass_lights_words_as_spoken_in_the_inkee_face():
    text = C.ass(C.chunks(words("It costs $20 a month.")), "beside")
    assert "Poppins ExtraBold" in text and "\\k" in text
    assert "644" in text                                    # beside: clear of Goli on the right
    assert "\\1c&H0068C2E8" in text                         # the money in gold
    assert (C.FONTS / "Poppins-ExtraBold.ttf").exists()
