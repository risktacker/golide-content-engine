import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from golide_engine.models import Annotation, Layer, Motion, Project, Scene
from golide_engine.render import _build_sfx_track, _compose_scene_clips, _render_scene_clips


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg smoke test")
class MotionFFmpegSmokeTests(unittest.TestCase):
    def test_real_motion_transition_annotation_and_sfx_render(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            media = []
            for index, color in enumerate(("0x111B36", "0xF4B942")):
                image = root / f"scene-{index}.png"
                subprocess.run([
                    "ffmpeg", "-y", "-f", "lavfi", "-i",
                    f"color=c={color}:s=400x700", "-frames:v", "1", str(image),
                ], check=True, capture_output=True)
                media.append(image)

            scenes = (
                Scene(
                    "beat-001", media[0], 0.6, "", 0.0, 0.6, "REVEAL",
                    Motion("push-in", "medium", "paper-wipe", "ease-out", "reveal", "impact"),
                    Annotation("number", "42", 0.1, 0.35, "center", "golide-gold"),
                    (Layer(media[1], "detail", "right", 0.25, "drift-left", 0.1, 0.35),),
                ),
                Scene(
                    "beat-002", media[1], 0.6, "", 0.6, 1.2, "PROCESS",
                    Motion("pan-left", "subtle", "cut", "ease-in-out", "process", "soft-trace"),
                    Annotation(),
                ),
            )
            project = Project(
                "smoke", "Smoke", "short", 320, 568, 12, 1.0,
                root / "narration.wav", None, None, None, 0.08, True,
                None, scenes, False,
            )
            output = root / "build"
            output.mkdir()
            clips = _render_scene_clips(project, output)
            silent = output / "silent.mp4"
            _compose_scene_clips(project, clips, silent)
            sfx, count = _build_sfx_track(project, output)
            self.assertTrue(silent.exists())
            self.assertTrue(sfx and sfx.exists())
            self.assertEqual(2, count)

            probe = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "json", str(silent),
            ], check=True, capture_output=True, text=True)
            duration = float(json.loads(probe.stdout)["format"]["duration"])
            self.assertAlmostEqual(1.2, duration, delta=0.15)


if __name__ == "__main__":
    unittest.main()
