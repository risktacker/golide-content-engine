from golide_engine.youtube.uploader import _initial_release_status


def test_missed_release_goes_out_30_minutes_after_render():
    """2026-11-13 (owner): a passed slot goes out 30 minutes after the render, so it can be checked first."""
    from datetime import datetime, timedelta, timezone
    status, state, privacy = _initial_release_status(
        {"scheduled_at": "2000-01-01T00:00:00Z"}
    )
    assert status["privacyStatus"] == "private"
    at = datetime.fromisoformat(status["publishAt"].replace("Z", "+00:00"))
    left = at - datetime.now(timezone.utc)
    assert timedelta(minutes=29) < left <= timedelta(minutes=30)
    assert state == "scheduled"
    assert privacy == "private"


def test_future_release_is_scheduled_at_insert_time():
    status, state, privacy = _initial_release_status(
        {"scheduled_at": "2099-01-01T18:00:00Z"}
    )
    assert status["privacyStatus"] == "private"
    assert status["publishAt"] == "2099-01-01T18:00:00Z"
    assert state == "scheduled"
    assert privacy == "private"
