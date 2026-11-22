"""3D Short storyboards (owner 2026-11-22): written once by Sol, repaired for free, capped at $0.86."""
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
    assert fixed["set"] == "office" and len(fixed["cast"]) == 4
    assert fixed["shots"][0]["from"] == 0
    starts = [w[s["from"]]["start"] for s in fixed["shots"]] + [w[-1]["end"]]
    assert all(b - a >= board.MIN_SHOT - 1e-6 for a, b in zip(starts, starts[1:]))
    assert all(a["angle"] != b["angle"] for a, b in zip(fixed["shots"], fixed["shots"][1:]))


def test_repair_fixes_what_a_model_gets_wrong():
    w = words()
    raw = {"set": "space", "cast": [{"id": "Boss!", "place": "desk-9", "look": {"outfit": "cape", "color": "red"}},
                                    {"id": "b", "place": "desk-9", "look": {}}],
           "tv": {"place": "above:nobody", "states": [{"from": 3, "title": "X"}]},
           "beats": [{"from": 999, "who": "boss", "act": "fly", "face": "angry", "bubble": "#", "look": "moon"},
                     {"from": 2, "who": "ghost", "act": "type"}],
           "glow": [{"from": 1, "place": "mars"}],
           "shots": [{"from": 0, "who": ["boss"], "angle": "front"}, {"from": 1, "who": ["boss"], "angle": "front"},
                     {"from": 40, "who": ["nobody"]}]}
    fixed, notes = board.repair(raw, w)
    assert fixed["set"] == "office"
    assert [c["id"] for c in fixed["cast"]] == ["boss", "b"]
    assert len({c["place"] for c in fixed["cast"]}) == 2 and all(c["place"] in board.OFFICE_PLACES for c in fixed["cast"])
    assert fixed["cast"][0]["look"]["outfit"] == "suit" and fixed["cast"][0]["look"]["color"].startswith("#")
    assert fixed["tv"]["place"] == "none" and fixed["tv"]["states"] == []
    assert fixed["beats"] == [{"from": 59, "who": "boss", "act": "stand", "face": "calm", "bubble": "none", "look": "front"}]
    assert fixed["glow"] == []
    assert notes


def test_long_shots_are_split_and_short_ones_merged():
    w = words(100, 0.4)        # 40 s, one shot asked for: split into parts of at most 3.5 s
    fixed, _ = board.repair({"set": "office", "cast": [{"id": "a", "place": "open-1", "look": {}}],
                             "shots": [{"from": 0, "who": ["a"], "angle": "front", "lens": "wide", "move": "push"}]}, w)
    starts = [w[s["from"]]["start"] for s in fixed["shots"]] + [w[-1]["end"]]
    assert len(fixed["shots"]) > 5
    assert all(b - a <= board.MAX_SHOT + 0.4 for a, b in zip(starts, starts[1:]))


def test_cost_cap_keeps_one_call_under_86_cents():
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
