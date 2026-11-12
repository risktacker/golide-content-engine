from golide_engine.providers.elevenlabs import ElevenLabsVoiceProvider, strip_cues
from golide_engine.engine.story import plan_from_story


def test_long_read_is_split_under_the_limit():
    voice = ElevenLabsVoiceProvider("eleven_v3", "v", max_characters_per_request=4800)
    para = ("This is a sentence that carries one thought forward. " * 20).strip()
    text = "\n\n".join([para] * 12)                     # about 12,700 characters
    parts = voice._parts(text)
    assert len(parts) >= 3 and all(len(p) <= 4800 for p in parts)
    assert "".join(parts).replace("\n", "") == text.replace("\n", "")


def test_cues_are_performed_not_shown():
    words = [{"word": "[excited]", "start": 0, "end": .1}, {"word": "Big", "start": .1, "end": .3},
             {"word": "[clears", "start": .3, "end": .4}, {"word": "throat]", "start": .4, "end": .5},
             {"word": "news.", "start": .5, "end": .8}]
    assert [w["word"] for w in strip_cues(words)] == ["Big", "news."]
    plan = plan_from_story({"title": "t", "chapters": [], "script": "[excited] Big news today. It is huge. "
                            "[serious] Here is why it matters to you."}, "short")
    assert all("[" not in l["text"] for l in plan["lines"])
    assert plan["voice_script"].startswith("[excited] Big news")


def test_v3_has_a_price():
    """2026-11-12: the first v3 read crashed after it was paid for, because v3 had no price."""
    import json
    from pathlib import Path
    pricing = json.loads(Path("config/provider-pricing.json").read_text())
    assert "eleven_v3" in json.dumps(pricing)
