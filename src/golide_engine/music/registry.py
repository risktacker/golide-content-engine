from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MusicTrack:
    id: str
    path: Path
    title: str
    creator: str
    source_url: str
    license: str
    attribution: str
    moods: tuple[str, ...]


class MusicRegistry:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.base = self.path.parent
        self.raw = json.loads(self.path.read_text(encoding="utf-8"))

    def tracks(self) -> tuple[MusicTrack, ...]:
        return tuple(
            MusicTrack(
                id=item["id"], path=(self.base / item["path"]).resolve(), title=item["title"],
                creator=item["creator"], source_url=item["source_url"], license=item["license"],
                attribution=item.get("attribution", ""), moods=tuple(item.get("moods", [])),
            ) for item in self.raw.get("tracks", [])
        )

    def select(self, mood: str, track_id: str | None = None) -> MusicTrack:
        matches = [track for track in self.tracks() if track_id == track.id] if track_id else [
            track for track in self.tracks() if mood.lower() in {value.lower() for value in track.moods}
        ]
        if not matches:
            raise RuntimeError(f"no licensed music registered for mood={mood!r}")
        track = matches[0]
        if track.license == "GOLIDE-Owned-Procedural-1.0" and not track.path.exists():
            self._generate_owned_bed(track.path)
        if not track.source_url or not track.license or not track.path.exists():
            raise RuntimeError(f"music track {track.id!r} lacks a valid file, source, or license")
        return track

    @staticmethod
    def _generate_owned_bed(path: Path, duration_seconds: int = 600) -> None:
        """Create the reusable non-vocal GOLIDE bed locally with FFmpeg."""
        path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"sine=frequency=55:sample_rate=44100:duration={duration_seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=110:sample_rate=44100:duration={duration_seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=44100:duration={duration_seconds}",
            "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.02:sample_rate=44100:duration={duration_seconds}",
            "-filter_complex",
            (
                "[0:a]volume=0.22,tremolo=f=0.10:d=0.18[a0];"
                "[1:a]volume=0.07,tremolo=f=0.11:d=0.35[a1];"
                "[2:a]volume=0.025,tremolo=f=0.17:d=0.45[a2];"
                "[3:a]lowpass=f=850,highpass=f=80,volume=0.10[a3];"
                "[a0][a1][a2][a3]amix=inputs=4:normalize=0,"
                "aecho=0.8:0.25:420|760:0.12|0.07,"
                "lowpass=f=1400,highpass=f=35,"
                "afade=t=in:st=0:d=2,afade=t=out:st="
                f"{max(0, duration_seconds - 3)}:d=3,"
                "loudnorm=I=-24:TP=-3:LRA=7,pan=stereo|c0=c0|c1=c0[out]"
            ),
            "-map", "[out]", "-c:a", "aac", "-b:a", "96k", str(path),
        ]
        subprocess.run(command, capture_output=True, text=True, check=True)

    @staticmethod
    def source_ledger(track: MusicTrack) -> dict[str, str]:
        return {
            "type": "music", "title": track.title, "creator": track.creator,
            "source_url": track.source_url, "license": track.license, "attribution": track.attribution,
        }
