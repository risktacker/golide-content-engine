import json
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
    story = {"shots": [{"set": "zoo", "moves": [{"do": "fireworks"}, {"do": "money_rain"}], "cam": "zoomy"},
                       {"set": "vault", "cam": "push", "moves": [{"do": "cash_pile"}]}]}
    assert len(L.fix_places(story)) == 3 and story["shots"][0]["set"] == "zoo"    # first: told to the writer
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
            "import engine.shots as S\nfrom engine.kit import make_look\nfrom golide_engine.stickman.rm_roles import ROLES\n"
            "for r in ROLES: S.draw_char(c, 500, 900, .6, make_look(dict(ROLES[r], role=r)), face=.3)\n"
            "S.draw_char(c, 500, 900, .6, make_look({'headscarf': True}))\n"
            "for n, f in rm_moves.MOVES.items():\n    [f(c, u, {'text': 'GO', 'names': ['A', 'B', 'C']}, 3.0 + u) for u in (0, .3, .7, 1, 2)]\n"
            "print('drew', len(rm_sets.NEW_SETS), len(rm_moves.MOVES))\n")
    f = Path("/tmp/_rm_draw_check.py")
    f.write_text(code)
    out = subprocess.run([sys.executable, str(f)], cwd=L.KIT, capture_output=True, text=True, timeout=300,
                         env={"PYTHONPATH": f"{hook}:{src}", "PATH": "/usr/bin:/bin"})
    assert "drew" in out.stdout, out.stderr[-800:]


def test_roles_dress_the_cast_and_unknown_roles_are_reported():
    from golide_engine.stickman.rm_roles import apply_roles
    story = {"cast": {"a": {"role": "Soldier"}, "b": {"role": "worker", "color": "#123456"}, "c": {"role": "cowboy"}}}
    assert apply_roles(story) == ["cowboy"]
    assert story["cast"]["a"]["outfit"] == "sweater" and story["cast"]["a"]["hat"] == "none"
    assert story["cast"]["b"]["color"] == "#123456"                 # what the writer set wins
    assert "role" not in story["cast"]["c"]
    assert "soldier" in L.instructions() and "headscarf" in L.instructions()


def test_logos_are_attached_from_the_logo_book_never_drawn(monkeypatch):
    from golide_engine.vector import logos
    book = {"nvidia": {"svg": "<svg></svg>", "hex": "76B900", "title": "NVIDIA"}}
    monkeypatch.setattr(logos, "find", lambda n: book.get(n.lower()))
    story = {"shots": [{"set": "hq", "logo": "Nvidia"},
                       {"moves": [{"do": "kart_race", "names": ["Nvidia", "BYD"]}, {"do": "logo_pop", "logo": "BYD"}]}]}
    assert L.attach_logos(story) == ["BYD", "BYD"]
    assert story["shots"][0]["logo_art"]["title"] == "NVIDIA"
    assert story["shots"][1]["moves"][0]["logo_art"][0]["hex"] == "76B900" and story["shots"][1]["moves"][0]["logo_art"][1] is None
    assert "logo_art" not in story["shots"][1]["moves"][1]           # no mark: its name in text, never a look-alike


def test_what_the_writer_wanted_is_listed(monkeypatch, tmp_path):
    from golide_engine.vector import logos
    monkeypatch.setattr(logos, "find", lambda n: None)
    story = {"cast": {"a": {"role": "cowboy"}}, "shots": [
        {"set": "casino2", "cam": "dolly", "icons": [{"name": "slot_machine"}, {"name": "chip"}], "logo": "BYD",
         "moves": [{"do": "fireworks"}, {"do": "money_rain"}]}]}
    got = {(w["kind"], w["name"]) for w in L.wishes(story)}
    assert got == {("role", "cowboy"), ("place", "casino2"), ("camera", "dolly"), ("icon", "slot machine"),
                   ("move", "fireworks"), ("logo", "BYD")}
    monkeypatch.delenv("GOLIDE_STUDIO_BASE_URL", raising=False)
    L.report_wishes(tmp_path, "t", L.wishes(story))
    assert len(json.loads((tmp_path / "wishes.json").read_text())) == 6


def test_no_pole_stands_where_characters_stand():
    src = (Path(L.__file__).resolve().parent / "rm_sets.py").read_text()
    assert "for x in (130, 1790):" in src and "for x in (150, 1770):" in src     # court and press flags
    assert "_in_band(i * 260)" in src                                            # station pillars


def test_goli_never_covers_the_stickman_panel_on_long():
    """Owner 2026-11-21: no collision. Measure every pose's real sprite where compose puts it beside the panel."""
    import numpy as np
    from PIL import Image
    from golide_engine.edit.compose import Composer
    from golide_engine.goli3d import video as g

    x, y, w_panel, h_panel = Composer.STAGE["long"]
    panel_right = x + w_panel + 6                      # the frame's border
    size = 600; w = size * g.aspect(); left = 1920 - w + 40
    assert abs(w_panel / h_panel - 16 / 9) < .01
    for pose in g.POSES:
        a = np.array(Image.open(Path("assets/goli3d/video") / pose / "body-sky.webp").convert("RGBA"))[:, :, 3]
        H, W = a.shape
        cols = np.where((a[:int(H * .85)] > 60).any(0))[0]          # the floor shadow is not his body
        if pose == "point_left":
            continue                                    # never used on long: compose turns it into "point"
        reach = left + (W - 1 - cols.max()) / W * w     # mirrored: his content side faces the panel
        right = left + w - cols.min() / W * w
        assert reach >= panel_right + 28, (pose, reach, panel_right)
        assert right <= 1920, (pose, right)


def test_every_behaviour_act_gives_a_state_and_the_writer_knows_them():
    from golide_engine.stickman.rm_acts import ACTS, act_state
    for name in ACTS:
        for tl in (0.0, .4, 1.3):
            o = act_state(name, min(1, tl), tl, 5 + tl, {"item": "phone"}, 1)
            assert isinstance(o, dict), name
    assert {"nod", "shake_head", "head_down", "scratch", "tap_foot", "laugh", "cry", "argue", "handshake", "type",
            "scroll", "grab", "walk_to", "run_to"} <= set(ACTS)
    text = L.instructions()
    assert "tap_foot" in text and "handshake" in text and "desk_row" in text


def test_acts_equipment_and_crowds_draw_in_the_kit():
    hook = Path(L.__file__).resolve().parent / "rm_hook"
    src = Path(L.__file__).resolve().parents[2]
    code = ("import sys,os; sys.path.insert(0, os.getcwd())\nimport skia, engine.props as P, engine.shots as S\n"
            "from engine.kit import make_look\n"
            "from golide_engine.stickman import rm_gear, rm_moves, rm_acts\n"
            "s = skia.Surface(480, 270); c = s.getCanvas(); c.scale(.25, .25)\n"
            "for n in rm_gear.ICONS: P.ICONS[n](c, 1.0, {'text': 'OPEN'})\n"
            "for n in ('bot_rows', 'desk_row', 'big_phone', 'comment_pop', 'like_counter'): rm_moves.MOVES[n](c, .6, {}, 2.0)\n"
            "for a in rm_acts.ARMS: S.draw_char(c, 500, 900, .6, make_look({}), arms=(a, a))\n"
            "print('drew', len(rm_gear.ICONS))\n")
    f = Path("/tmp/_rm_acts_check.py")
    f.write_text(code)
    out = subprocess.run([sys.executable, str(f)], cwd=L.KIT, capture_output=True, text=True, timeout=300,
                         env={"PYTHONPATH": f"{hook}:{src}", "PATH": "/usr/bin:/bin"})
    assert "drew 50" in out.stdout, out.stderr[-800:]


def test_unknown_acts_go_on_the_missing_list(monkeypatch):
    from golide_engine.vector import logos
    monkeypatch.setattr(logos, "find", lambda n: None)
    story = {"shots": [{"chars": [{"id": "a", "acts": [{"do": "moonwalk"}, {"do": "nod"}]}]}]}
    assert {"kind": "act", "name": "moonwalk"} in L.wishes(story) and {"kind": "act", "name": "nod"} not in L.wishes(story)


def test_walking_swings_the_arms_against_the_legs():
    from golide_engine.stickman.rm_acts import swing
    left_fwd, right_fwd = ((-10, 46, 0), (10, -46, 20)), ((-10, -46, 20), (10, 46, 0))
    a, b = swing(("down", "down"), left_fwd), swing(("down", "down"), right_fwd)
    assert a[0][2] == 1.0 and b[0][2] == 0.0                     # the arm swings the other way to its leg
    assert swing(("point", "down"), left_fwd)[0] == "point"       # an arm doing something keeps doing it
    assert swing(("down", "down"), None) == ("down", "down")
