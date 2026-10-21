"""Unclear pictures are redrawn at most twice per video (owner, 2026-10-21)."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from golide_engine.orchestration import production
from golide_engine.orchestration.production import MAX_REDRAWS, REDRAW_COUNTER, redraws_used


class RedrawCapTests(unittest.TestCase):
    def _run(self, folder: Path, pictures: int) -> int:
        calls = []
        engine = SimpleNamespace(_reserve=lambda *a, **k: None, _record_image=lambda *a, **k: None)
        line_art = SimpleNamespace(create=lambda prompt, path, size: calls.append(path) or path.write_bytes(b"x"))
        with mock.patch("golide_engine.vector.illustrate.vectorize", return_value=object()), \
             mock.patch("golide_engine.vector.illustrate.picture_problems", return_value=["all glow"]), \
             mock.patch("golide_engine.vector.scene_art.picture_size", return_value="1024x1024"):
            for n in range(pictures):
                target = folder / f"p{n}.png"
                target.write_bytes(b"x")
                part = SimpleNamespace(picture_id=f"p{n}")
                production.ProductionService._redraw_if_unclear(
                    engine, {"format": "long"}, part, "prompt", target, line_art, "img", "job")
        return len(calls)

    def test_at_most_two_redraws_per_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._run(Path(tmp), 5), MAX_REDRAWS)
            self.assertEqual(redraws_used(Path(tmp) / REDRAW_COUNTER), MAX_REDRAWS)

    def test_a_resumed_run_keeps_the_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._run(Path(tmp), 1)
            self.assertEqual(self._run(Path(tmp), 3), MAX_REDRAWS - 1)

    def test_missing_or_broken_counter_reads_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            counter = Path(tmp) / REDRAW_COUNTER
            self.assertEqual(redraws_used(counter), 0)
            counter.write_text("junk")
            self.assertEqual(redraws_used(counter), 0)


if __name__ == "__main__":
    unittest.main()
