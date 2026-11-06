"""Lays finished 3D shots over the video, under the captions, on the voice's clock."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

FADE = 0.35


class ClipTrack:
    def __init__(self, clips: list[dict]):
        self.clips = sorted(clips, key=lambda c: c["start"])
        self._key: tuple | None = None
        self._frame: np.ndarray | None = None

    def _picture(self, path: Path, size: tuple[int, int]) -> np.ndarray:
        key = (str(path), size)
        if key != self._key:
            image = Image.open(path).convert("RGB")
            scale = max(size[0] / image.width, size[1] / image.height)
            fitted = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
            left, top = (fitted.width - size[0]) // 2, (fitted.height - size[1]) // 2
            self._frame = np.asarray(fitted.crop((left, top, left + size[0], top + size[1])), np.float32)
            self._key = key
        assert self._frame is not None
        return self._frame

    def at(self, t: float, size: tuple[int, int]) -> tuple[np.ndarray, float] | None:
        """The shot's picture at time t and how solid it is, or None between shots."""
        for clip in self.clips:
            if clip["start"] <= t < clip["end"]:
                frames = sorted(Path(clip["frames"]).glob("f*.png"))
                if not frames:
                    return None
                index = int((t - clip["start"]) * clip["fps"])
                alpha = min(1.0, (t - clip["start"]) / FADE, (clip["end"] - t) / FADE)
                return self._picture(frames[min(index, len(frames) - 1)], size), alpha
        return None
