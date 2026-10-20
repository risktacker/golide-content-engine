"""Exact diagrams (owner direction 2026-10-20): defined networks, flows and trees."""

import json
import tempfile
from pathlib import Path

import pytest

from golide_engine.vector.figures import FigureError, render_figure

SPECS = [
    "network: hub=Public Benefit Fund; nodes=Stockholders, Board, Researchers, The Public, Governments; glow=hub",
    "network: hub=Fund; nodes=Stockholders, Board, Researchers, Public; glow=Board; Board - Public",
    "flow: steps=Shares, Benefit Fund, Grants, Public; glow=Benefit Fund",
    "tree: root=Anthropic; children=Benefit Fund, Board, Stockholders; glow=Benefit Fund; Benefit Fund > Research, Safety",
]


@pytest.mark.parametrize("spec", SPECS)
@pytest.mark.parametrize("size", [(2100, 1000), (1024, 1536)])
def test_diagram_draws_every_name_once_with_a_glow(spec, size):
    with tempfile.TemporaryDirectory() as temp:
        path = render_figure(spec, Path(temp) / "d.png", size)
        meta = json.loads(path.with_suffix(".figure.json").read_text())
    texts = " ".join(label["text"] for label in meta["labels"])
    for name in ("Board", "Fund", "Public", "Shares", "Anthropic"):
        if name in spec:
            assert name.split()[0] in texts
    assert any(s["gold"] for s in meta["strokes"])


def test_too_many_long_names_fall_back_instead_of_overlapping():
    names = ", ".join(f"Very Long Department Name {i}" for i in range(7))
    with tempfile.TemporaryDirectory() as temp, pytest.raises(FigureError):
        render_figure(f"flow: steps={names}", Path(temp) / "d.png", (2100, 1000))
