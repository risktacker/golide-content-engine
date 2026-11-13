"""2026-11-13 (owner, point 4): Goli moves between poses and reacts to what is said."""
import tempfile
from pathlib import Path

from golide_engine.edit.compose import Composer, reactions


def test_reactions_come_from_questions_exclamations_and_landings():
    edit = {"captions": [{"start": 1, "end": 2, "words": [{"text": "who", "at": 1.0}, {"text": "checks?", "at": 1.4}]},
                         {"start": 3, "end": 4, "words": [{"text": "wow!", "at": 3.2}]}],
            "scenes": [{"type": "metaphor", "start": 5, "duration": 3, "data": {"at": 1.2}}]}
    assert reactions(edit) == [(1.4, "question"), (3.2, "exclaim"), (6.2, "land")]


def test_pose_change_is_one_pose_at_a_time_with_a_swing():
    edit = {"format": "long", "duration": 6.0, "captions": [{"start": 2, "end": 3, "words": [{"text": "really?", "at": 2.5}]}],
            "scenes": [{"type": "host", "start": 0, "duration": 6.0, "data": {"place": "side", "cues": [], "poses": [
                {"pose": "talk", "at": 0}, {"pose": "point", "at": 1.0}]}}]}
    html = Composer("long").build(edit, Path(tempfile.mkdtemp()) / "o").read_text()
    assert 'tl.set("#s1-host-p0",{opacity:0},1.000);tl.set("#s1-host-p1",{opacity:1},1.000);' in html
    assert "back.out(2.4)" in html and '"#s1-host-act",{rotation:' in html
