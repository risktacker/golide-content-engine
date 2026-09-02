from golide_engine.youtube.uploader import _initial_release_status


def test_missed_release_is_public_at_insert_time():
    status, state, privacy = _initial_release_status(
        {"scheduled_at": "2000-01-01T00:00:00Z"}
    )
    assert status["privacyStatus"] == "public"
    assert "publishAt" not in status
    assert state == "published"
    assert privacy == "public"


def test_future_release_is_scheduled_at_insert_time():
    status, state, privacy = _initial_release_status(
        {"scheduled_at": "2099-01-01T18:00:00Z"}
    )
    assert status["privacyStatus"] == "private"
    assert status["publishAt"] == "2099-01-01T18:00:00Z"
    assert state == "scheduled"
    assert privacy == "private"
