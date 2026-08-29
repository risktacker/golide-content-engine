from __future__ import annotations

import json
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
        if not track.source_url or not track.license or not track.path.exists():
            raise RuntimeError(f"music track {track.id!r} lacks a valid file, source, or license")
        return track

    @staticmethod
    def source_ledger(track: MusicTrack) -> dict[str, str]:
        return {
            "type": "music", "title": track.title, "creator": track.creator,
            "source_url": track.source_url, "license": track.license, "attribution": track.attribution,
        }
