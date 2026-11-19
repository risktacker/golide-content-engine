"""2026-11-13 (owner): the broken USB Short: pops everywhere, half-second pictures, words off the phone's frame."""
from golide_engine.edit import editor
from golide_engine.edit.layout import safe_factor
from golide_engine.edit.render import sound_plan


def test_no_pops_or_ticks_and_sounds_are_spaced():
    cues = [{"kind": k, "t": i * 0.3} for i, k in enumerate(["pop", "click", "whoosh", "pop", "whoosh", "impact",
                                                              "click", "whoosh", "riser", "pop"] * 6)]
    kept = sound_plan(cues)
    assert not any(c["kind"] in ("pop", "click") for c in kept)
    assert len(kept) <= 14            # 60 cues in 18 s -> about one every 1.3 s
    assert all(b["t"] - a["t"] >= 0.6 or b["kind"] == "impact" for a, b in zip(kept, kept[1:]))
    assert all(c["kind"] != "riser" for c in kept[-1:])


def test_half_second_pictures_join_their_neighbour():
    scenes = [{"type": t, "start": s, "duration": d, "data": {}} for t, s, d in
              [("kinetic_title", 0.76, .51), ("metaphor", 1.27, .51), ("browser_shot", 1.78, .5),
               ("stat_counter", 2.28, .6), ("kinetic_title", 2.88, 2.0)]]
    out = [s for s in editor._min_length(scenes, "short") if s["type"] != "host"]
    assert all(s["duration"] >= 1.0 for s in out)
    assert abs(out[0]["start"] - 0.76) < 1e-6 and abs(out[-1]["start"] + out[-1]["duration"] - 4.88) < 1e-6


def test_content_past_the_phone_crop_is_shrunk():
    assert safe_factor([200, 400, 880, 900], "short", (1080, 1920)) == 1.0
    f = safe_factor([-118, 400, 1000, 900], "short", (1080, 1920))
    assert f < 1 and 540 - (540 + 118) * f >= 129


def test_no_words_blocks_and_the_picture_before_holds():
    sc = lambda t, s, d: {"type": t, "start": s, "duration": d, "data": {}}
    scenes = [sc("kinetic_title", 0, 2), sc("metaphor", 2, 2), sc("kinetic_title", 4, 2), sc("photo", 6, 2),
              sc("kinetic_title", 8, 2), sc("kinetic_title", 10, 2), sc("stat_counter", 12, 2)]
    notes = []
    out = editor._words_cap(scenes, notes)
    assert sum(s["type"] == "kinetic_title" for s in out) == 0
    photo = next(s for s in out if s["type"] == "photo")
    assert photo["duration"] == 4                     # holds up to 4 s; longer than that Goli takes the beat (2026-11-19)
    assert out[0]["type"] == "metaphor" and out[0]["start"] == 0 and out[0]["duration"] == 4   # an opening words block goes to the picture after
    goli = [(s["start"], s["duration"]) for s in out if s["type"] == "host"]
    assert goli == [(4, 2), (10, 2)] and all(not s["data"]["words"] for s in out if s["type"] == "host")
    assert sum(s["duration"] for s in out) == 14


def test_a_long_hook_gets_a_picture_per_sentence_or_clause_and_the_rest_and_shorts_do_not_change():
    from golide_engine.edit.editor import beats
    from golide_engine.vector.align import TimedLine, Word
    text = ("Imagine a phone reveal so convincing, you forget the company never revealed it. The clips show a "
            "purple phone with four cameras. But it is still unconfirmed, and that matters.")
    ws = [Word(w, i * 0.32, i * 0.32 + 0.28) for i, w in enumerate(text.split())]
    hook = TimedLine(0, text, "", "", "", "intro", 0, ws[-1].end, ws)
    body_words = [Word(w, 20 + i * 0.32, 20 + i * 0.32 + 0.28) for i, w in enumerate(text.split())]
    body = TimedLine(1, text, "", "", "", "01", 20, body_words[-1].end, body_words)
    got = beats([hook, body], "long")
    in_hook = [b for b in got if b.start < 15]
    assert len(in_hook) == 4 and all(b.text[-1] in ",." for b in in_hook)    # cut where a clause ends
    assert len([b for b in got if b.start >= 15]) == 4                       # after the hook: ~3 s beats (2026-11-18)
    short = beats([hook], "short")
    assert [b.text for b in short] == [b.text for b in beats([hook], "short")]


def test_numbers_one_a_minute_and_cards_short_then_goli():
    """2026-11-19 (owner review of the China EV video): 8 number cards in a minute, "40%" and a chapter card ~9 s."""
    sc = lambda t, s, d: {"type": t, "start": s, "duration": d, "data": {}}
    scenes = [sc("stat_counter", 0, 3), sc("photo", 3, 3), sc("stat_counter", 6, 3), sc("photo", 9, 60),
              sc("stat_counter", 69, 3), sc("photo", 72, 60)]
    notes = []
    out = editor._words_cap(scenes, notes, "long")
    stats = [s["start"] for s in out if s["type"] == "stat_counter"]
    assert stats == [0, 69] and any(s["type"] == "host" and s["start"] == 6 for s in out)
    cards = editor._short_cards([sc("chapter_card", 0, 9), sc("photo", 9, 3)], [], [])
    assert [(s["type"], s["start"], s["duration"]) for s in cards] == [("chapter_card", 0, 2.0), ("host", 2, 7), ("photo", 9, 3)]


def test_a_recipe_plays_long_enough_to_watch():
    """2026-11-19 (owner): recipes lasted under a second while text cards got 2-3 s."""
    sc = lambda t, s, d: {"type": t, "start": s, "duration": d, "data": {}}
    out = editor._recipe_time([sc("recipe_clip", 0, 1.0), sc("photo", 1, 2), sc("metaphor", 3, 4)], "long", [])
    assert [(s["type"], s["start"], s["duration"]) for s in out] == [("recipe_clip", 0, 4.5), ("metaphor", 4.5, 2.5)]
    out = editor._recipe_time([sc("recipe_clip", 0, 1.0), sc("recipe_clip", 1, 1.0)], "short", [])
    assert [s["duration"] for s in out] == [1.0, 1.0]         # never eats another recipe
