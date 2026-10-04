"""Owner-recording length rules.

The owner's recording is the master timeline. The engine never speeds up,
slows down or trims the voice to fit a format. A recording outside its window
is rejected with a plain re-record instruction. The Studio upload form applies
the same windows in the browser before anything is uploaded.
"""

from __future__ import annotations

RECORDING_WINDOWS: dict[str, tuple[float, float]] = {
    "short": (30.0, 90.0),
    "long": (210.0, 300.0),
}


class RecordingLengthError(RuntimeError):
    """Raised when an owner recording falls outside its format window."""


def _clock(seconds: float) -> str:
    whole = int(round(seconds))
    return f"{whole // 60}:{whole % 60:02d}"


def check_recording_length(format_name: str, seconds: float) -> None:
    window = RECORDING_WINDOWS.get(format_name)
    if window is None:
        raise RecordingLengthError(f"unknown video format '{format_name}'")
    low, high = window
    label = "Short" if format_name == "short" else "Long video"
    seconds = float(round(seconds))  # same whole-second rule as the Studio upload form
    if seconds < low:
        raise RecordingLengthError(
            f"{label} recording is {_clock(seconds)}, too short. "
            f"Allowed: {_clock(low)} to {_clock(high)}. Please re-record and upload again."
        )
    if seconds > high:
        raise RecordingLengthError(
            f"{label} recording is {_clock(seconds)}, too long. "
            f"Allowed: {_clock(low)} to {_clock(high)}. Please re-record and upload again."
        )
