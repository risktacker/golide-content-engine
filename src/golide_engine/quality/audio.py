from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


def measure_loudness(video: str | Path) -> dict[str, float]:
    command = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-af",
        "loudnorm=I=-16:TP=-1:LRA=11:print_format=json", "-f", "null", "-",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])
    matches = re.findall(r"\{[\s\S]*?\}", result.stderr)
    if not matches:
        raise RuntimeError("ffmpeg did not report loudness data")
    raw = json.loads(matches[-1])
    return {"integrated_lufs": float(raw["input_i"]), "true_peak_dbtp": float(raw["input_tp"]), "loudness_range": float(raw["input_lra"])}


def check_audio(video: str | Path, policy: dict) -> list[str]:
    measurement = measure_loudness(video)
    limits = policy["audio"]
    failures = []
    if not limits["integrated_lufs_min"] <= measurement["integrated_lufs"] <= limits["integrated_lufs_max"]:
        failures.append(f"integrated loudness {measurement['integrated_lufs']} LUFS outside policy")
    if measurement["true_peak_dbtp"] > limits["true_peak_dbtp_max"]:
        failures.append(f"true peak {measurement['true_peak_dbtp']} dBTP exceeds policy")
    return failures
