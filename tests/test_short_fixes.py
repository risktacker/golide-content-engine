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


def test_one_metaphor_in_a_short():
    assert editor.METAPHOR_CAP["short"] == 1
