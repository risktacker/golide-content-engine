"""A picture the image model refuses on safety grounds never stops a video (2026-10-16)."""

import tempfile
import unittest
from pathlib import Path

from golide_engine.providers.openai_media import is_moderation_block
from golide_engine.vector.scene_art import Part, calm_prompt, fill_from_neighbours


class RefusalTests(unittest.TestCase):
    def test_detects_the_safety_refusal(self):
        err = RuntimeError("Error code: 400 - {'error': {'message': 'Your request was rejected by the safety "
                           "system.', 'code': 'moderation_blocked'}}")
        self.assertTrue(is_moderation_block(err))
        self.assertFalse(is_moderation_block(RuntimeError("timeout")))

    def test_calm_prompt_keeps_the_style_and_softens_the_scene(self):
        part = Part("scene-03", "carbon-fibre tanks blasting air from jets", "the jets", "", "single")
        prompt = calm_prompt(f"Line art. Draw: {part.drawing} Gold: the jets.", part)
        self.assertNotIn("blasting", prompt)
        self.assertIn("no explosions", prompt)

    def test_refused_pictures_borrow_the_nearest_neighbour(self):
        with tempfile.TemporaryDirectory() as tmp:
            pics = [Path(tmp) / f"scene-0{i}.png" for i in range(1, 5)]
            for i in (0, 3):
                pics[i].write_bytes(f"pic{i}".encode())
            fill_from_neighbours(pics, {pics[1], pics[2]})
            self.assertEqual(pics[1].read_bytes(), b"pic0")
            self.assertEqual(pics[2].read_bytes(), b"pic3")

    def test_all_refused_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            pic = Path(tmp) / "scene-01.png"
            with self.assertRaises(RuntimeError):
                fill_from_neighbours([pic], {pic})


if __name__ == "__main__":
    unittest.main()
