"""3D Short storyboards (owner 2026-11-22): written once by Sol, repaired for free, capped at $1.50 since 2026-11-24."""
import json
import subprocess
from pathlib import Path

import pytest

from golide_engine.shorts3d import board, build, remote

FIX = Path(__file__).parent / "fixtures" / "shorts3d-board-trial.json"


def words(n=60, step=0.4):
    return [{"word": f"w{i}{',' if i % 6 == 5 else ''}", "start": round(i * step, 2), "end": round(i * step + 0.3, 2)} for i in range(n)]


def test_fixture_board_repairs_cleanly():
    w = words()
    fixed, notes = board.repair(json.loads(FIX.read_text()), w)
    assert len(fixed["cast"]) == 2 and len(fixed["things"]) == 3
    assert fixed["shots"][0]["from"] == 0
    starts = [w[s["from"]]["start"] for s in fixed["shots"]] + [w[-1]["end"]]
    assert all(b - a >= board.MIN_SHOT - 1e-6 for a, b in zip(starts, starts[1:]))
    assert all((a["angle"], a["lens"]) != (b["angle"], b["lens"]) for a, b in zip(fixed["shots"], fixed["shots"][1:]))


def test_nothing_is_pre_decided():
    """Owner 2026-11-23: no set, prop list or topic in what Sol is told; nouns and places are free text."""
    ins = board.instructions().lower()
    for word in ("office", "desk", "laptop", "sofa", "kitchen", "tv", "investor", "chip"):
        assert f" {word}" not in ins, word
    sch = json.dumps(board.schema())
    props = board.schema()["properties"]
    tp = props["things"]["items"]["properties"]
    assert all("enum" not in tp[k] for k in ("name", "search", "parts", "text")) and "enum" not in json.dumps(props["world"]["properties"]["place"])
    assert "set" not in props and '"office"' not in sch


def test_repair_fixes_what_a_model_gets_wrong():
    w = words()
    raw = {"world": {"place": "x", "size": [500, -3], "sky": "purple", "ground_color": "green"},
           "things": [{"id": "Ball!", "name": "ball", "at": [999, 1], "height_m": -1}, {"id": "ball", "name": "other", "on": "ball"}],
           "cast": [{"id": "Kid", "look": {"outfit": "cape", "color": "red"}}, {"id": "kid", "at": [1, 1]}],
           "beats": [{"from": 999, "who": "kid", "do": "fly"}, {"from": 2, "who": "ghost", "do": "stand"},
                     {"from": 3, "who": "kid", "do": "walk"}, {"from": 4, "who": "kid", "do": "kick", "target": "ball"},
                     {"from": 5, "who": "kid", "do": "ride", "target": "nothing"}],
           "events": [{"from": 6, "thing": "ball", "do": "move"}, {"from": 7, "thing": "ball", "do": "spin", "amount": 90}],
           "shots": [{"from": 0, "frame": ["kid"], "angle": "front"}, {"from": 1, "frame": ["kid"], "angle": "front"},
                     {"from": 40, "frame": ["nobody"]}]}
    fixed, notes = board.repair(raw, w)
    W = fixed["world"]
    assert W["size"] == [120.0, 10.0] and W["sky"] == "day" and W["ground_color"].startswith("#")
    ids = [t["id"] for t in fixed["things"]]
    assert ids == ["ball", "ballx"] and fixed["things"][0]["at"][0] == 60.0 and fixed["things"][0]["height_m"] == 0.02
    assert fixed["things"][1]["on"] == "ball"
    assert [c["id"] for c in fixed["cast"]] == ["kid", "kidp"] and fixed["cast"][0]["look"]["outfit"] == "shirt"
    dos = [(b["from"], b["do"], b["with"]) for b in fixed["beats"]]
    assert (3, "stand", "") in dos and (4, "kick", "ball") in dos and (5, "stand", "") in dos and (59, "stand", "") in dos
    assert [e["do"] for e in fixed["events"]] == ["spin"]
    assert notes


def test_long_shots_are_split_and_short_ones_merged():
    w = words(100, 0.4)        # 40 s, one shot asked for: split into parts of at most 3.5 s
    fixed, _ = board.repair({"cast": [{"id": "a", "at": [0, 0], "look": {}}],
                             "shots": [{"from": 0, "frame": ["a"], "angle": "front", "lens": "wide", "move": "push"}]}, w)
    starts = [w[s["from"]]["start"] for s in fixed["shots"]] + [w[-1]["end"]]
    assert len(fixed["shots"]) > 5
    assert all(b - a <= board.MAX_SHOT + 0.4 for a, b in zip(starts, starts[1:]))


def test_things_match_only_on_their_own_noun():
    from golide_engine.shorts3d import things
    idx = [{"lib": "k", "id": "ballerina", "words": ["ballerina", "dancer"]}, {"lib": "k", "id": "ball", "words": ["ball", "soccer"]},
           {"lib": "k", "id": "truck", "words": ["truck", "delivery"]}, {"lib": "k", "id": "fire-truck", "words": ["fire", "truck"]}]
    assert things.best({"name": "soccer ball", "search": "football"}, idx)["id"] == "ball"
    assert things.best({"name": "fire truck", "search": "fire engine truck"}, idx)["id"] == "fire-truck"
    assert things.best({"name": "steam locomotive", "search": "train"}, idx) is None
    assert things.words("pickupTruck_Large") == ["pickup", "truck"]
    assert things.best({"name": "hand cart", "search": "cart"}, [{"lib": "p", "id": "w", "words": ["portable", "welding", "cart"]}]) is None
    assert things.best({"name": "wooden crate", "search": "crate"}, [{"lib": "p", "id": "c", "words": ["wooden", "military", "crate"]}])
    wall = {"name": "canyon cliffs", "search": "cliff rock", "height_m": 20, "parts": ["rock: box 0 0 0 80 8 20"]}
    assert things.best(wall, [{"lib": "p", "id": "b", "words": ["boulder", "cliff", "rock"], "dims": [3000, 2800, 2400]}]) is None


def test_things_without_a_model_are_built_from_their_parts():
    from golide_engine.shorts3d import things
    ps = things.parts_of({"height_m": 2.0, "parts": ["body: box 0 0 0 4 2 1 #ff0000", "wheel: cyl 1 0 0 1 0.3 1 rx90", "junk"]})
    assert len(ps) == 2 and ps[0]["color"] == "#ff0000"
    assert abs(max(p["c"][1] + p["s"][1] / 2 for p in ps) - 2.0) < 1e-3


def test_cost_cap_keeps_one_call_under_the_cap():
    ins = board.instructions() + board.request("T", words(180, 0.4), board.phrases(words(180, 0.4)))
    est = board.estimate_input_tokens(ins)
    cost = est * board.PRICE_IN + board.max_output_tokens(est) * board.PRICE_OUT
    assert cost <= board.COST_CAP_USD


def test_write_never_lets_the_provider_ask_twice():
    seen = {}
    class Out:
        value = {"set": "office"}; input_tokens = 1; cached_input_tokens = 0; output_tokens = 1; request_id = "r"
    class P:
        def generate_json(self, ins, req, schema, max_output_tokens, grow):
            seen.update(grow=grow, limit=max_output_tokens, strict=schema["additionalProperties"] is False)
            return Out()
    data, _ = board.write(P(), "T", words())
    assert data == {"set": "office"} and seen["grow"] is False and seen["strict"]


def test_phrases_start_after_punctuation():
    p = board.phrases(words(12))
    assert [x["from"] for x in p] == [0, 6]


def test_join_refuses_missing_parts(tmp_path):
    with pytest.raises(RuntimeError, match="parts missing"):
        build.join(tmp_path, 2, tmp_path / "p.mp4")


def test_join_in_order(tmp_path):
    for i in range(2):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=64x64:r=30", "-t", "0.5",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(tmp_path / f"part-{i}.mp4")], check=True)
    out = build.join(tmp_path, 2, tmp_path / "picture.mp4")
    assert abs(build._seconds(out) - 1.0) < 0.1


def test_remote_keys():
    assert remote.key("p1", "part-3.mp4") == "shorts3d/p1/part-3.mp4"


def test_old_flat_card_kit_is_gone():
    root = Path(build.ROOT)
    assert not (root / "vendor" / "cartoon-short-kit").exists()
    assert not (root / "src" / "golide_engine" / "stickman" / "short.py").exists()


def test_held_short_skips_reels_in_the_upload_step():
    src = (Path(build.ROOT) / "src" / "golide_engine" / "cli.py").read_text()
    assert 'not release.get("hold_private")' in src


def test_no_line_comment_swallows_code_in_scene_modules():
    """A // comment in the middle of a one-line statement chain hid the TV headline (2026-11-22): every // must end
    its line, so nothing after it on that line is meant to run."""
    import re
    for f in (Path(build.ASSETS)).glob("*.js"):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            code = re.sub(r"'[^']*'|\"[^\"]*\"|`[^`]*`", "''", line)
            if "//" in code:
                tail = code.split("//", 1)[1]
                assert not re.search(r";\s*[A-Za-z_$][\w$.]*\s*\(.*\)\s*;", tail), f"{f.name}:{n} code after //"


def test_voice_tags_survive_a_director_that_changed_a_word():
    """2026-11-23: the director wrote "two" for "2", the check threw all tags away, the Short had none."""
    from golide_engine.engine.story import apply_direction
    plain = "He saw gaps every 39 feet, and 2 companies race.\n\nThen summer comes, and something weird happens. His gaps start shrinking."
    directed = "[curious] He saw gaps every thirty-nine feet, and two companies race.\n\n[surprised] Then summer comes, and something weird happens. His gaps start shrinking."
    out, why = apply_direction(plain, directed)
    assert out.startswith("[curious] He saw gaps every 39 feet, and 2 companies race.")
    assert "[surprised] Then summer comes" in out and "two" not in out
    assert why.startswith("words changed: tags moved")
    assert apply_direction(plain, "Something else entirely.")[0] == plain


def test_scene_modules_parse(tmp_path):
    """Every 3D Short scene module must be valid JavaScript (2026-11-23: a // comment swallowed a closing brace)."""
    import shutil
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    for f in Path(build.ASSETS).glob("*.js"):
        copy = tmp_path / (f.stem + ".mjs")
        copy.write_text(f.read_text())
        r = subprocess.run([node, "--check", str(copy)], capture_output=True, text=True)
        assert r.returncode == 0, f"{f.name}: {r.stderr[:300]}"


def test_moves_fly_between_landings_and_cut_between_moves():
    w = words(60, 0.4)
    raw = {"cast": [{"id": "a", "at": [0, 0], "look": {}}, {"id": "b", "at": [2, 0], "look": {}}],
           "moves": [{"from": 0, "job": "hook", "follow": "", "landings": [
                         {"see": "close on a", "from": 0, "frame": ["a"], "angle": "front", "lens": "face"},
                         {"see": "pull back to both", "from": 4, "frame": ["a", "b"], "angle": "high", "lens": "wide"}]},
                     {"from": 10, "job": "talk", "follow": "b", "landings": [
                         {"see": "b speaks", "from": 10, "frame": ["b"], "angle": "low", "lens": "face"}]}]}
    fixed, _ = board.repair(raw, w)
    sh = fixed["shots"]
    assert [s["take"] for s in sh[:3]] == [0, 0, 1]
    assert sh[0]["move"] == "push" and sh[1]["move"] == "crane-up" and sh[2]["job"] == "talk" and sh[2]["follow"] == "b"
    assert sh[0]["see"] == "close on a"


def test_instructions_carry_the_measured_method():
    ins = board.instructions()
    for k in ("hook", "setup", "explain", "climax", "attention chain", "180-degree", "8 to 20 kinds", "sound off", "THE ENGINE STANDS THE CAMERA", "CLOSE on the exact", "painted ON a thing", "turned"):
        assert k in ins, k


def sentence_words(text, step=0.4):
    return [{"word": t, "start": round(i * step, 2), "end": round(i * step + 0.3, 2)} for i, t in enumerate(text.split())]


def test_every_full_stop_is_its_own_scene_with_enough_pictures():
    """Owner 2026-11-24: Ricks Clips storyboards almost every full stop; a long sentence needs more pictures."""
    w = sentence_words("One two three. " + " ".join(f"w{i}" for i in range(14)) + ". End now!")
    ss = board.sentences(w)
    assert [s["from"] for s in ss] == [0, 3, 17] and ss[1]["until"] == 16
    assert ss[1]["pictures"] == 6 and ss[0]["pictures"] == 1
    req = board.request("T", w, board.phrases(w))
    assert "SENTENCES" in req and "6 pictures" in req
    ins = board.instructions()
    assert "SENTENCE BY SENTENCE" in ins and "one move per sentence" in ins.lower()


def test_coverage_finds_a_sentence_with_too_few_pictures():
    w = sentence_words("One two three. " + " ".join(f"w{i}" for i in range(14)) + ". End now!")
    b = {"moves": [{"from": 0, "job": "hook", "follow": "", "landings": [{"from": 0}, {"from": 5}]}],
         "plan": [{"sentence": 0}, {"sentence": 1}]}
    cov = board.coverage(b, w)
    assert cov[1]["short"] and cov[1]["landings"] == 1 and cov[1]["needs"] == 6 and cov[1]["plan_rows"] == 1


def test_the_engine_learns_general_rules_from_each_film():
    from golide_engine.shorts3d import lessons
    report = {"shots": [{"station_dropped": ["Hero is hidden behind cliff"], "found": ["Hero is hidden behind cliff"]},
                        {"station_moved": [1, 2, 3]}],
              "staging": ["Sailor passes through crate"]}
    keys = lessons.observe(["p1 walk at word 4 had nowhere to go: stands"], report, [{"short": True}])
    assert {"station-hidden", "station-inside", "staging", "walk-nowhere", "sentence-short"} <= set(keys)
    st = lessons.update(None, keys)
    st = lessons.update(st, ["staging"])
    rules = lessons.for_sol(st)
    assert rules[0].startswith("People walked") and "2 films" in rules[0]
    assert all("cliff" not in r and "crate" not in r and "Sailor" not in r for r in rules)   # general, never the film's nouns
    for _ in range(lessons.LAPSE):
        st = lessons.update(st, [])
    assert lessons.for_sol(st) == []
    ins = board.instructions(rules)
    assert "LESSONS FROM EARLIER FILMS" in ins and rules[0] in ins


def test_too_close_shots_move_to_the_next_free_word_instead_of_vanishing():
    w = sentence_words(" ".join(f"w{i}" for i in range(20)), step=0.3)
    b = {"cast": [{"id": "a", "at": [0, 0]}], "moves": [{"from": 0, "job": "hook", "follow": "", "landings": [
        {"from": 0, "frame": ["a"]}, {"from": 1, "frame": ["a"]}, {"from": 9, "frame": ["a"]}]}]}
    fixed, notes = board.repair(b, w)
    assert [s["from"] for s in fixed["shots"]][:3] == [0, 3, 9] and any("moved to word 3" in n for n in notes)
