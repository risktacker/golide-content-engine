"""2026-11-13 (owner): the voice sounded like someone reading an article; the script must be written to be performed."""
from golide_engine.engine.story import delivery_problems, story_instructions

FLAT = ("[excited] On February 5, 2026, Anthropic launched Claude Opus 4.6, and the launch made it easy to mistake the "
        "upgrade for a smarter chatbot. [curious] But the important change is not the first answer it gives you. "
        "It is what happens after that answer. A long-horizon model can plan a job, use tools, keep track of earlier "
        "work, write and run code, then check whether the result works.\n\n") * 6

PERFORMED = """[curious][softly] So... what actually changed? Honestly? Not the first answer. It's what happens AFTER that answer!

[curious] Think about it. You ask it for a function. It writes one. Then what? It just waits.

[excited] Not anymore! Now it plans the job, runs the code, and checks it. Wait. Read that again. It CHECKS its own work.

[sarcastic] Sounds great, right? Okay, but who checks the checker? That's the real question."""


def test_no_quotas_any_more():
    """2026-11-13 (owner, after his v4 test): no counts of questions, exclamations, capitals or tags."""
    plain = ("Imagine a phone reveal so convincing, you forget the company never revealed it. The clips show a purple "
             "phone with 4 cameras. But the phone is still unconfirmed. So what surfaced? Tom's Guide reported dummy "
             "units. A dummy copies the outside, but it doesn't prove the real phone matches.")
    assert delivery_problems(plain, "short") == []
    assert delivery_problems(PERFORMED.replace("...", "."), "long") == []


def test_writer_writes_plainly_and_a_director_adds_the_tags():
    from golide_engine.engine.story import direction_instructions
    rules = story_instructions("long", (310, 340))
    assert "No audio tags" in rules and "VOICE TAGS" not in rules
    d = direction_instructions("short")
    assert "[curious]" in d and "NEVER add, remove or change words" in d and "never two tags" in d.lower()


def test_direction_is_kept_only_when_the_words_are_the_same():
    from golide_engine.engine.story import apply_direction
    plain = "[[0]] The dummy units show 4 cameras. Sounds convincing, right? It's a rumour, not a reveal."
    good = "[[0]] [skeptical] The dummy units show 4 cameras.\n\nSounds convincing, right? It's a RUMOUR, not a reveal."
    assert apply_direction(plain, good) == (good, "ok")
    assert apply_direction(plain, good.replace("4", "four"))[1] == "words changed"
    assert apply_direction(plain, good.replace("[[0]] ", ""))[1] == "chapter markers moved"
    stacked = "[[0]] [skeptical] [surprised] The dummy units show 4 cameras. Sounds convincing, right? It's a rumour, not a reveal."
    assert "[surprised]" not in apply_direction(plain, stacked)[0]
    odd = "[[0]] [screams] The dummy units show 4 cameras. Sounds convincing, right? It's a rumour, not a reveal."
    assert "[screams]" not in apply_direction(plain, odd)[0]


def test_hook_never_opens_with_a_date_or_greeting():
    for bad in ("[excited] On February 5, 2026, Anthropic launched Claude.", "In this video we look at AI.",
                "Hey everyone, welcome back."):
        assert any("first sentence" in p for p in delivery_problems(bad))
    assert not any("first sentence" in p for p in delivery_problems(
        "[curious] Your AI can now finish a junior engineer's job... so why are investors nervous?"))


def test_voice_is_cleaned_before_levelling():
    from golide_engine.edit.render import VOICE_CHAIN
    assert "highpass" in VOICE_CHAIN and "deesser" in VOICE_CHAIN and "acompressor" in VOICE_CHAIN


def test_a_short_has_no_dead_stops_and_is_one_chain():
    loose = ("[curious] Blue ports may be faster... Black ports are USB 2.0. Speeds reach 80 gigabits! "
             "Standards bodies recommend blue. Colour is a clue? Logos matter. Wattage is separate. Shapes vary.")
    got = delivery_problems(loose, "short")
    assert any('"..."' in p for p in got) and any("chain" in p for p in got)
    chain = ("[curious] Imagine you buy a laptop, but the fast port is a lie? So you check the colour. "
             "But blue only hints at speed! Then you look for the SS logo. That logo is the real promise. "
             "And the charging? That's a different label again. So you read the spec, and now you KNOW.")
    assert delivery_problems(chain, "short") == []


def test_the_same_thing_said_twice_is_caught():
    twice = "[curious] Check the SS logo, then read the specification. Okay? Wow! Check the SS logo, then read the specification."
    assert any("twice" in p for p in delivery_problems(twice, "short"))
