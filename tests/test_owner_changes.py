"""Owner 2026-11-10: replace the day's script from a pasted video; edit the script in Studio."""
import json
from pathlib import Path

from golide_engine.engine.content_rules import script_display
from golide_engine.engine.story import plan_from_story
from golide_engine.orchestration import owner_changes as oc
from golide_engine.orchestration.queue import waiting_for_voice


class FakeDB:
    def __init__(self):
        self.deleted = []

    def execute(self, sql, args):
        self.deleted.append(args[1])


class FakeYouTube:
    def videos(self):
        return self

    def list(self, **kw):
        self.kw = kw
        return self

    def execute(self):
        return {"items": [{"snippet": {"title": "How Compaq Cloned IBM", "channelTitle": "AI Terry",
                                       "description": "The story"},
                           "statistics": {"viewCount": "9000"}, "contentDetails": {"duration": "PT9M5S"}}]}


def test_a_pasted_video_becomes_the_model_and_clears_the_old_script(tmp_path):
    work = tmp_path / "productions" / "p1"
    work.mkdir(parents=True)
    for name in ("research.json", "script.txt", "scene-plan.json"):
        (work / name).write_text("{}")
    spec = {"id": "p1", "title": "Old", "brief": "old", "script_edit": "old words",
            "replace_model": {"url": "https://youtu.be/v_XdN5-ya9A", "requested_at": "t1"}}
    spec_path = tmp_path / "p1.json"
    assert not waiting_for_voice(spec, tmp_path)          # a new script is due
    db = FakeDB()
    assert oc.apply_replace(spec, spec_path, work, db, "p1", FakeYouTube(), transcript=lambda u: "words " * 50)
    assert spec["title"] == "How Compaq Cloned IBM" and spec["source_breakout"]["duration_seconds"] == 545
    assert spec["platform_demand"]["verdict"] == "pass" and "script_edit" not in spec
    assert not (work / "script.txt").exists() and set(db.deleted) == {"research", "script"}
    assert json.loads(spec_path.read_text())["title"] == "How Compaq Cloned IBM"
    assert not oc.apply_replace(spec, spec_path, work, db, "p1", FakeYouTube(), transcript=lambda u: "")


def test_the_owners_edit_keeps_chapters_and_applies_once(tmp_path):
    plan = {"chapters": [{"number": "", "title": "Intro"}, {"number": "01", "title": "How it works"}], "lines": [
        {"chapter": 0, "text": "Hello there friend."}, {"chapter": 1, "text": "First the chip boots."}]}
    shown = script_display(plan)
    assert oc.edit_pending({"script_edit": shown}, tmp_path, shown) == ""      # unchanged: nothing to do
    edited = shown.replace("Hello there friend.", "Hello there, my friend.")
    assert oc.edit_pending({"script_edit": edited}, tmp_path, shown) == edited
    new = plan_from_story(oc.story_from_reading(edited, plan["chapters"]), "long")
    assert [(l["chapter"], l["text"]) for l in new["lines"]][0] == (0, "Hello there, my friend.")
    assert len(new["chapters"]) == 2
    oc.mark_edit_done(tmp_path, edited)
    assert oc.edit_pending({"script_edit": edited}, tmp_path, shown) == ""


def test_news_channels_rank_below_creators():
    from golide_engine.youtube.breakouts import is_news_channel
    assert is_news_channel("CNBC Television") and is_news_channel("The Verge")
    assert not is_news_channel("Nate Herk | AI Automation") and not is_news_channel("Fireship")
