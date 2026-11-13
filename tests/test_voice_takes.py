"""2026-11-13 (owner, Isaac's method): one read per paragraph; the hook of a long video read 3 times, best kept."""
import subprocess

from golide_engine.providers.elevenlabs import ElevenLabsVoiceProvider, liveliness, pick_take

PARA = "This is a sentence that is long enough to count for something real. " * 5


def _voice(takes=3):
    return ElevenLabsVoiceProvider("eleven_v3", "voice", max_characters_per_request=4800, hook_takes=takes,
                                   take_settings={"stability": 0.0})


def test_one_request_per_paragraph():
    script = "\n\n".join([PARA] * 6)
    parts = _voice(1)._parts(script)
    assert len(parts) == 6 and all(len(p) >= 250 for p in parts)


def test_short_paragraphs_join_the_next():
    parts = _voice(1)._parts("Short one.\n\n" + PARA + "\n\n" + PARA)
    assert len(parts) == 2 and parts[0].startswith("Short one.")


def test_hook_is_the_opening_sentences_and_is_its_own_part():
    script = PARA * 2 + "\n\n" + PARA
    voice = _voice(3)
    parts = voice._parts(script)
    assert 250 <= len(parts[0]) <= 400
    assert voice.planned_characters(script) == len(script.strip()) + 2 * len(parts[0])
    assert voice.planned_characters(script, 1) == len(script.strip())     # Shorts: read once


def test_the_liveliest_believable_take_wins():
    takes = [{"take": 0, "seconds": 10.0, "life": 1.5}, {"take": 1, "seconds": 10.4, "life": 2.6},
             {"take": 2, "seconds": 16.0, "life": 4.0}]           # take 2 rambled: too long, out
    report = pick_take(takes, 30)
    assert report["chosen"] == 1
    assert [t["ok"] for t in report["takes"]] == [True, True, False]


def test_liveliness_hears_a_flat_read(tmp_path):
    flat, moving = tmp_path / "flat.wav", tmp_path / "moving.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=f=140:d=3", "-af", "volume=0.5", str(flat)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "aevalsrc=0.5*sin(2*PI*(110*t+40*t*t)):d=3", str(moving)],
                   check=True)
    assert liveliness(moving) > liveliness(flat)
