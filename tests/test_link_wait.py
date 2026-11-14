"""2026-11-14 (owner): every slot waits for the video he pastes; no link by the slot's time, the engine takes over
with the AI voice (option (a): it publishes 30 minutes after the render)."""
import json
from datetime import date, datetime, timezone

from golide_engine.orchestration.queue import link_fallback, pick_due_spec, waiting_for_link
from golide_engine.orchestration.schedule import build_spec

RULE = {"id": "golide-shorts", "format": "short", "generate_time": "09:00", "publish_time": "13:00",
        "weekdays": ["monday"], "start_date": "2026-01-01"}
BEFORE = datetime(2026, 11, 16, 9, 30, tzinfo=timezone.utc)      # 11:30 Lusaka
AFTER = datetime(2026, 11, 16, 11, 5, tzinfo=timezone.utc)       # 13:05 Lusaka


def _spec():
    return build_spec(RULE, date(2026, 11, 16), "Africa/Lusaka", "UC")


def test_a_slot_waits_for_the_link_until_its_time():
    spec = _spec()
    assert spec["link_wait"] and waiting_for_link(spec, BEFORE) and not waiting_for_link(spec, AFTER)
    assert not link_fallback(spec, BEFORE) and "voice_choice" not in spec


def test_a_pasted_link_starts_it_and_it_waits_for_his_recording():
    spec = dict(_spec(), replace_model={"url": "https://youtu.be/abcdefghijk", "requested_at": "t"})
    assert not waiting_for_link(spec, BEFORE)
    assert not link_fallback(spec, AFTER) and spec.get("voice_choice") != "ai"


def test_no_link_by_the_slot_time_means_engine_topic_and_ai_voice():
    spec = _spec()
    assert link_fallback(spec, AFTER) and spec["voice_choice"] == "ai" and spec["link_fallback"]
    assert not link_fallback(spec, AFTER)          # once


def test_the_queue_never_runs_a_slot_that_is_waiting_for_a_link(tmp_path):
    waiting = _spec()
    waiting["release"]["scheduled_at"] = "2099-01-01T11:00:00Z"
    path = tmp_path / "w.json"
    path.write_text(json.dumps(waiting))
    assert pick_due_spec([path], tmp_path) is None
