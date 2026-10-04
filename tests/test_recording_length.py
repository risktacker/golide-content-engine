import pytest

from golide_engine.orchestration.recording import (
    RECORDING_WINDOWS,
    RecordingLengthError,
    check_recording_length,
)


def test_windows_are_locked():
    assert RECORDING_WINDOWS["short"] == (30.0, 90.0)
    assert RECORDING_WINDOWS["long"] == (210.0, 300.0)


@pytest.mark.parametrize("fmt,seconds", [("short", 30), ("short", 75), ("short", 90),
                                          ("long", 210), ("long", 270), ("long", 300)])
def test_accepts_inside_window(fmt, seconds):
    check_recording_length(fmt, seconds)


@pytest.mark.parametrize("fmt,seconds,word", [("short", 29, "too short"), ("short", 91, "too long"),
                                               ("long", 200, "too short"), ("long", 322, "too long")])
def test_rejects_outside_window_with_rerecord_message(fmt, seconds, word):
    with pytest.raises(RecordingLengthError) as info:
        check_recording_length(fmt, seconds)
    assert word in str(info.value)
    assert "re-record" in str(info.value)


def test_engine_never_retimes_owner_voice():
    from pathlib import Path
    source = Path("src/golide_engine/orchestration/production.py").read_text()
    assert "atempo" not in source
