"""2026-11-14 (owner): when he changes the words while recording (Studio or ElevenLabs), the captions and the
blocks follow what he said, not the old script."""
from golide_engine.captions import respell_from_script
from golide_engine.orchestration.owner_changes import reading_from_audio

DISPLAY = ("[INTRO]\nThe new MacBook Pro can hit 2,000 nits, but that isn't the reason its screen looks different.\n\n"
           "[01 · THE BLACK DIFFERENCE]\nStart with a normal laptop screen. Most LCD panels have a light behind it.")


def _words(text):
    return [{"word": w, "start": i * 0.3, "end": i * 0.3 + 0.25} for i, w in enumerate(text.split())]


def test_the_same_reading_changes_nothing():
    said = DISPLAY.replace("[INTRO]", "").replace("[01 · THE BLACK DIFFERENCE]", "")
    assert reading_from_audio(DISPLAY, _words(said)) == ""


def test_a_misheard_word_keeps_the_script():
    said = ("The new Mac Book Pro can hit 2,000 nits, but that isn't the reason its screen looks different. "
            "Start with a normal laptop screen. Most LCD panels have a light behind it.")
    out = reading_from_audio(DISPLAY, _words(said))
    assert out == "" or "MacBook" in out


def test_a_rewritten_hook_becomes_the_script_and_keeps_the_chapters():
    said = ("Your next laptop screen might switch its pixels off, and that changes everything you see. "
            "Start with a normal laptop screen. Most LCD panels have a light behind it.")
    out = reading_from_audio(DISPLAY, _words(said))
    assert out.startswith("[INTRO]\nYour next laptop screen might switch its pixels off")
    assert "2,000 nits" not in out and "[01 · THE BLACK DIFFERENCE]" in out and "Most LCD panels" in out


def test_captions_keep_a_rewritten_hook():
    heard = _words("Your next laptop screen might switch its pixels off and that changes everything")
    script = "The new MacBook Pro can hit 2,000 nits, but that isn't the reason its screen looks different."
    out = " ".join(w["word"] for w in respell_from_script(heard, script))
    assert out.startswith("Your next laptop screen")
