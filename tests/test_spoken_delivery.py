"""2026-11-13 (owner): the voice sounded like someone reading an article; the script must be written to be performed."""
from golide_engine.engine.story import delivery_problems, story_instructions

FLAT = ("[excited] On February 5, 2026, Anthropic launched Claude Opus 4.6, and the launch made it easy to mistake the "
        "upgrade for a smarter chatbot. [curious] But the important change is not the first answer it gives you. "
        "It is what happens after that answer. A long-horizon model can plan a job, use tools, keep track of earlier "
        "work, write and run code, then check whether the result works.\n\n") * 6

PERFORMED = """[curious][softly] So... what actually changed? Honestly? Not the first answer. It's what happens AFTER that answer!

[curious] Think about it. You ask it for a function. It writes one. Then what? It just waits.

[excited] Not anymore! Now it plans the job, runs the code, and checks it. Wait. Read that again... it CHECKS its own work.

[sarcastic] Sounds great, right? Okay, but who checks the checker? That's the real question."""


def test_flat_script_is_caught():
    problems = delivery_problems(FLAT)
    assert any("questions" in p for p in problems)
    assert any("exclamations" in p for p in problems)
    assert any("pauses" in p for p in problems)


def test_performed_script_passes():
    assert delivery_problems(PERFORMED) == []


def test_writer_is_told_to_perform():
    rules = story_instructions("long", (310, 340))
    assert "SPOKEN DELIVERY" in rules and "VOICE TAGS" in rules and "[laughs]" in rules and "[whispers]" in rules


def test_hook_never_opens_with_a_date_or_greeting():
    for bad in ("[excited] On February 5, 2026, Anthropic launched Claude.", "In this video we look at AI.",
                "Hey everyone, welcome back."):
        assert any("first sentence" in p for p in delivery_problems(bad))
    assert not any("first sentence" in p for p in delivery_problems(
        "[curious] Your AI can now finish a junior engineer's job... so why are investors nervous?"))


def test_voice_is_cleaned_before_levelling():
    from golide_engine.edit.render import VOICE_CHAIN
    assert "highpass" in VOICE_CHAIN and "deesser" in VOICE_CHAIN and "acompressor" in VOICE_CHAIN
