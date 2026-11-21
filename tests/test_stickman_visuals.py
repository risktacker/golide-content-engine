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


def test_the_writer_sees_places_moves_and_camera():
    sets, moves = L.kit_sets(), L.kit_moves()
    assert {"office", "street", "datacenter", "factory", "court", "hospital", "space", "mars", "launchpad", "port",
            "farm", "ocean", "hq", "cutaway", "trading", "vault"} <= sets and len(sets) >= 40
    assert {"money_rain", "rocket_launch", "earth_spin", "kart_race", "podium", "dominoes", "chart_down", "alarm"} <= moves
    text = L.instructions()
    assert "datacenter" in text and "rocket_launch" in text and "pan_left" in text


def test_unknown_place_move_or_camera_goes_back_then_never_stops_the_render():
    story = {"shots": [{"set": "casino", "moves": [{"do": "fireworks"}, {"do": "money_rain"}], "cam": "zoomy"},
                       {"set": "vault", "cam": "push", "moves": [{"do": "cash_pile"}]}]}
    assert len(L.fix_places(story)) == 3 and story["shots"][0]["set"] == "casino"    # first: told to the writer
    L.fix_places(story, final=True)
    assert story["shots"][0] == {"moves": [{"do": "money_rain"}]}                     # kit's own place for the kind
    assert story["shots"][1] == {"set": "vault", "cam": "push", "moves": [{"do": "cash_pile"}]}


def test_places_and_moves_load_in_the_kits_spawn_workers():
    hook = Path(L.__file__).resolve().parent / "rm_hook"
    src = Path(L.__file__).resolve().parents[2]
    code = ("import sys,os,multiprocessing as mp; sys.path.insert(0, os.getcwd())\n"
            "def w(_):\n    import engine.shots as S, engine.sets as T\n"
            "    from golide_engine.stickman import rm_moves\n"
            "    return 'datacenter' in T.SETS and 'mars' in T.SETS and S.Shot.__init__.__name__ == '__init__' and 'money_rain' in rm_moves.MOVES\n"
            "if __name__ == '__main__':\n    import engine.shots\n"
            "    with mp.get_context('spawn').Pool(1) as p: print(p.map(w, [0])[0])\n")
    f = Path("/tmp/_rm_spawn_check2.py")
    f.write_text(code)
    out = subprocess.run([sys.executable, str(f)], cwd=L.KIT, capture_output=True, text=True, timeout=120,
                         env={"PYTHONPATH": f"{hook}:{src}", "PATH": "/usr/bin:/bin"})
    assert out.stdout.strip().endswith("True"), out.stderr[-800:]


def test_every_place_and_move_draws():
    hook = Path(L.__file__).resolve().parent / "rm_hook"
    src = Path(L.__file__).resolve().parents[2]
    code = ("import sys,os; sys.path.insert(0, os.getcwd())\nimport skia, engine.sets as T, engine.shots\n"
            "from golide_engine.stickman import rm_sets, rm_moves\n"
            "s = skia.Surface(480, 270); c = s.getCanvas(); c.scale(.25, .25)\n"
            "for n, f in rm_sets.NEW_SETS.items(): f(c, {}); f(c, {'time': 'night', 'sign': 'Nvidia', 'flag': 'X'})\n"
            "for n, f in rm_moves.MOVES.items():\n    [f(c, u, {'text': 'GO', 'names': ['A', 'B', 'C']}, 3.0 + u) for u in (0, .3, .7, 1, 2)]\n"
            "print('drew', len(rm_sets.NEW_SETS), len(rm_moves.MOVES))\n")
    f = Path("/tmp/_rm_draw_check.py")
    f.write_text(code)
    out = subprocess.run([sys.executable, str(f)], cwd=L.KIT, capture_output=True, text=True, timeout=300,
                         env={"PYTHONPATH": f"{hook}:{src}", "PATH": "/usr/bin:/bin"})
    assert "drew" in out.stdout, out.stderr[-800:]
