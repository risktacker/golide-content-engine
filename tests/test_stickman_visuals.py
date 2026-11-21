import json
import subprocess
import sys
from pathlib import Path

from golide_engine.stickman import longform as L


def test_writer_sees_the_whole_visual_list():
    known = L.kit_icons()
    assert {"chip", "datacenter", "rocket", "satellite", "factory", "gavel", "hospital", "label", "bulb"} <= known
    assert len(known) >= 100
    assert "datacenter" in L.instructions()


def test_an_unknown_thing_becomes_a_name_card_not_a_gap():
    story = {"shots": [{"props": [{"icon": "quantum_computer"}], "icons": [{"name": "Mars rover"}, {"name": "rocket"}]}]}
    L.fix_icons(story)
    shot = story["shots"][0]
    assert shot["props"] == [{"icon": "label", "text": "quantum computer"}]
    assert shot["icons"][0] == {"name": "label", "text": "Mars rover"} and shot["icons"][1] == {"name": "rocket"}


def test_our_icons_load_in_the_kits_spawn_workers():
    hook = Path(L.__file__).resolve().parent / "rm_hook"
    src = Path(L.__file__).resolve().parents[2]
    code = ("import sys,os,multiprocessing as mp; sys.path.insert(0, os.getcwd())\n"
            "def w(_):\n    import engine.props as P\n    return 'chip' in P.ICONS and 'bulb' in P.ICONS\n"
            "if __name__ == '__main__':\n    import engine.props as P\n    assert 'chip' in P.ICONS\n"
            "    with mp.get_context('spawn').Pool(1) as p: print(p.map(w, [0])[0])\n")
    f = Path("/tmp/_rm_spawn_check.py")
    f.write_text(code)
    out = subprocess.run([sys.executable, str(f)], cwd=L.KIT, capture_output=True, text=True, timeout=120,
                         env={"PYTHONPATH": f"{hook}:{src}", "PATH": "/usr/bin:/bin"})
    assert out.stdout.strip().endswith("True"), out.stderr[-500:]
