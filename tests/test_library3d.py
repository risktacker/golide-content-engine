import os
import unittest
from unittest import mock

import numpy as np

os.environ.setdefault("GOLIDE_LIBRARY3D_OFFLINE", "1")

from golide_engine.vector import library3d, motion3d  # noqa: E402


def cube(at):
    import trimesh

    m = trimesh.creation.box(extents=(1, 1, 1))
    m.apply_translation(at)
    return np.asarray(m.vertices), np.asarray(m.faces)


class Library(unittest.TestCase):
    def test_every_entry_is_licence_clear_and_has_a_file(self):
        for key, entry in library3d.index().items():
            self.assertIn(entry["source"], ("nasa", "cc0"), key)
            self.assertTrue(entry["licence"], key)
            self.assertTrue(entry["repo_path"].endswith((".glb", ".gltf", ".obj")), key)

    def test_aliases_find_the_object(self):
        self.assertEqual(library3d.find("Perseverance"), "mars rover")
        self.assertEqual(library3d.find("JWST"), "james webb space telescope")
        self.assertIsNone(library3d.find("toaster"))

    def test_missing_file_offline_falls_back(self):
        with mock.patch.object(library3d, "CACHE", library3d.Path("/nonexistent")):
            self.assertFalse(library3d.available("hubble"))
            self.assertFalse(motion3d.is_model({"object": "hubble"}))

    def test_one_piece_model_splits_into_sections_that_can_open(self):
        meshes = [cube((x, 0, 0)) for x in (0, 3, 6, 9)]
        v = np.vstack([m[0] for m in meshes])
        f = np.vstack([m[1] + 8 * i for i, m in enumerate(meshes)])
        groups = library3d._clusters([(v, f)])
        self.assertGreater(len(groups), 1)
        self.assertEqual(sum(len(fs) for g in groups.values() for _, fs in g), len(f))

    def test_thin_panels_get_a_back_side(self):
        v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], float)
        f = np.array([[0, 1, 2]])
        v2, f2 = library3d._two_sided(v, f)
        self.assertEqual(len(f2), 2)
        self.assertEqual(len(v2), 6)


if __name__ == "__main__":
    unittest.main()
