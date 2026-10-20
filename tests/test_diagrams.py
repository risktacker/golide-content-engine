"""Exact diagrams (owner direction 2026-10-20): defined networks, flows and trees."""

import json
import tempfile
import unittest
from pathlib import Path

from golide_engine.vector.figures import FigureError, render_figure

SPECS = [
    "network: hub=Public Benefit Fund; nodes=Stockholders, Board, Researchers, The Public, Governments; glow=hub",
    "network: hub=Fund; nodes=Stockholders, Board, Researchers, Public; glow=Board; Board - Public",
    "flow: steps=Shares, Benefit Fund, Grants, Public; glow=Benefit Fund",
    "tree: root=Anthropic; children=Benefit Fund, Board, Stockholders; glow=Benefit Fund; Benefit Fund > Research, Safety",
]


class DiagramTests(unittest.TestCase):
    def test_every_diagram_draws_its_names_with_a_glow_in_both_formats(self):
        for spec in SPECS:
            for size in ((2100, 1000), (1024, 1536), (512, 512)):
                with self.subTest(spec=spec[:20], size=size), tempfile.TemporaryDirectory() as temp:
                    path = render_figure(spec, Path(temp) / "d.png", size)
                    meta = json.loads(path.with_suffix(".figure.json").read_text())
                    texts = " ".join(label["text"] for label in meta["labels"])
                    for name in ("Board", "Shares", "Anthropic"):
                        if name in spec:
                            self.assertIn(name, texts)
                    self.assertTrue(any(s["gold"] for s in meta["strokes"]))

    def test_too_many_long_names_fall_back_instead_of_overlapping(self):
        names = ", ".join(f"Very Long Department Name {i}" for i in range(7))
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(FigureError):
            render_figure(f"flow: steps={names}", Path(temp) / "d.png", (2100, 1000))


if __name__ == "__main__":
    unittest.main()
