"""2026-11-17 (owner): Futurepedia style recipes wired into the edit engine (edit/recipes.py)."""
import json
from pathlib import Path

from golide_engine.edit import editor, recipes
from golide_engine.vector.align import TimedLine, Word


def test_the_writer_gets_the_recipe_unchanged_without_its_sound_kit_or_storyboard_steps():
    text = recipes.recipe_text("xray")
    source = (recipes.BOOK / "x-ray.txt").read_text(encoding="utf-8")
    kit = source[source.find("STAGE KIT"):source.find("SOUND KIT (")].strip()
    assert kit in text                                    # the stage kit, word for word
    assert source[source.find("REFERENCE STYLE SOURCE"):].strip() in text
    assert "HOW TO STAY IN THE STYLE" in text and "STYLE CARD" in text
    assert "SOUND KIT (" not in text and "STORYBOARD FIRST" not in text
    rules = recipes.instructions("xray")
    assert "NO" in rules and "title" in rules and "ONE accent" in rules


def test_the_kit_shipped_is_the_recipes_kit():
    source = (recipes.BOOK / "x-ray.txt").read_text(encoding="utf-8")
    kit = source[source.find("```js", source.find("STAGE KIT")) + 6:source.find("```", source.find("```js", source.find("STAGE KIT")) + 6)]
    assert (recipes.KIT / "stage.js").read_text(encoding="utf-8").strip() == kit.strip()
    assert (recipes.KIT / "three" / "three.module.js").exists() and (recipes.KIT / "fonts").is_dir()


def test_the_request_carries_the_words_with_their_times_and_the_last_problems():
    req = recipes.request("xray", "a Blackwell GPU", [{"text": "Inside", "t": 0.2}, {"text": "memory", "t": 1.4}], 6.0,
                          (1600, 900), "the first frame is empty")
    assert "Inside@0.20" in req and "memory@1.40" in req and "1600x900" in req and "first frame is empty" in req


def _lines():
    words = [Word(w, 0.4 * i, 0.4 * i + 0.35) for i, w in enumerate("Inside the chip the memory sits next to the die".split())]
    return [TimedLine(0, " ".join(w.text for w in words), "", "", "", "", 0.0, words[-1].end, words)]


def test_the_editor_makes_a_recipe_scene_with_its_words_and_a_house_3d_stand_in(monkeypatch):
    monkeypatch.setattr(editor, "PAID_LOOKS", ("blueprint",))
    monkeypatch.setattr(editor, "FREE_LOOKS", tuple(k for k in editor.FREE_LOOKS if k != "blueprint"))
    s = {k: None for k in editor.SCENE["required"]}
    s.update(type="recipe", first_line=0, last_line=0, goli_corner=False, poses=[], rows=[], items=[], shots=[],
             points=[], brands=[], parts3d=[], recipe="blueprint", recipe_brief="A GPU: die, memory, heat", object3d="chip",
             move3d="explode", punch="memory")
    edit = editor.build({"scenes": [s]}, _lines(), 4.0, "long", [], None, [], [],
                        looks=editor.looks_for({"paid": {"blueprint": 1}}))
    sc = next(x for x in edit["scenes"] if x["type"] == "recipe_clip")
    assert sc["data"]["recipe"] == "blueprint" and sc["data"]["words"][0]["text"] == "Inside"
    assert sc["data"]["fallback"]["object"] == "chip" and sc["data"]["fallback"]["move"] == "explode"
    assert set(editor.SCENE["required"]) == set(editor.SCENE["properties"])


def test_a_recipe_scene_that_cannot_be_made_becomes_the_house_3d(tmp_path, monkeypatch):
    from golide_engine.edit import pipeline

    monkeypatch.setattr(pipeline, "settings", lambda: {"recipes": {"enabled": False}})
    edit = {"look": "xray", "notes": [], "scenes": [
        {"type": "photo", "start": 0, "duration": 2, "data": {}},
        {"type": "recipe_clip", "start": 2, "duration": 4, "data": {"recipe": "xray", "brief": "x", "words": [],
                                                                        "fallback": {"object": "chip", "move": "own"}}}]}
    pipeline._recipes(None, {"format": "long"}, tmp_path, "p", edit, "m")
    assert edit["scenes"][1]["type"] == "object3d" and edit["scenes"][1]["data"]["look"] == "xray"
    edit["scenes"][1] = {"type": "recipe_clip", "start": 2, "duration": 4, "data": {"recipe": "xray", "brief": "x",
                                                                                    "words": [], "fallback": None}}
    pipeline._recipes(None, {"format": "long"}, tmp_path, "p", edit, "m")
    assert [s["type"] for s in edit["scenes"]] == ["photo"] and edit["scenes"][0]["duration"] == 6


def test_labels_that_touch_or_leave_the_frame_are_sent_back():
    box = lambda text, x0, y0, x1, y1: {"text": text, "x0": x0, "y0": y0, "x1": x1, "y1": y1}
    found = [box("NV-HBI LINK", 200, 100, 600, 160), box("TWO DIES", 500, 140, 800, 200), box("HBM", 200, 700, 400, 760)]
    problems = recipes.label_problems(found, (1600, 900), 6.9)
    assert len(problems) == 1 and "NV-HBI LINK" in problems[0] and "TWO DIES" in problems[0]
    assert "leaves the frame" in recipes.label_problems([box("X", 1590, 100, 1650, 150)], (1600, 900), 1)[0]
    assert recipes.label_problems([box("A", 100, 100, 300, 150), box("B", 100, 170, 300, 220)], (1600, 900), 1) == []


def test_layer_stack_is_a_recipe_from_its_own_prompt():
    text = recipes.recipe_text("layers")
    assert "Name: Layer Stack" in text and "styles/layer-stack.js" in text and "SOUND KIT (" not in text
    assert "layers" in editor.RECIPE_KEYS
    player = (recipes.KIT / "player.html").read_text(encoding="utf-8")
    assert "userData.words" in player and "inset" in player and '"Inter"' in player   # 3D labels are measured


def test_all_six_futurepedia_prompts_are_recipes_and_blueprint_gets_its_lettering_library():
    assert set(editor.RECIPE_KEYS) == {"xray", "layers", "white", "circuit", "glass", "blueprint"} == set(recipes.RECIPES)
    for key in recipes.RECIPES:
        text = recipes.recipe_text(key)
        assert f"Name: {recipes.RECIPES[key]['name']}" in text and "REFERENCE STYLE SOURCE" in text and "SOUND KIT (" not in text
    assert "STROKEFONT.layout(text, opts)" in recipes.recipe_text("blueprint")
    assert "STROKEFONT.layout" not in recipes.recipe_text("glass")
    source = (recipes.BOOK / "blueprint-build.txt").read_text(encoding="utf-8")
    lib = (recipes.KIT / "strokefont.js").read_text(encoding="utf-8").strip()
    assert lib.startswith("/*") and lib in source                 # the library, unchanged from its prompt
    assert "K.words" in recipes.instructions("blueprint")


def test_printed_labels_on_one_surface_and_3d_words_passing_the_edge():
    box = lambda text, x0, y0, x1, y1, **k: {"text": text, "x0": x0, "y0": y0, "x1": x1, "y1": y1, **k}
    found = [box("220", 100, 90, 200, 128, sheet=1), box("16V", 110, 120, 190, 150, sheet=1), box("C8", 100, 90, 160, 120, sheet=2)]
    problems = recipes.printed_problems(found)
    assert len(problems) == 1 and "220" in problems[0] and "16V" in problems[0]
    assert "not registered" in recipes.printed_problems([{"unregistered": True}])[0]
    passing = [box("PROMPT", -40, 300, 120, 340, world=True)]
    assert recipes.label_problems(passing, (1600, 900), 2.0, last=False) == []      # the camera is still travelling
    assert "leaves the frame" in recipes.label_problems(passing, (1600, 900), 7.8, last=True)[0]   # the hold
    assert recipes.label_problems([box("GONE", -300, 10, -100, 40, world=True)], (1600, 900), 7.8) == []


def _scene(**kw):
    s = {k: None for k in editor.SCENE["required"]}
    s.update(type="recipe", first_line=0, last_line=0, goli_corner=False, poses=[], rows=[], items=[], shots=[],
             points=[], brands=[], parts3d=[])
    s.update(kw)
    return s


def test_switches_default_to_every_free_style_and_no_paid_one(monkeypatch):
    monkeypatch.setattr(editor, "PAID_LOOKS", ("blueprint",))
    monkeypatch.setattr(editor, "FREE_LOOKS", tuple(k for k in editor.FREE_LOOKS if k != "blueprint"))
    assert editor.looks_for(None) == {"free": list(editor.FREE_LOOKS), "paid": {}}
    got = editor.looks_for({"free": ["layers", "bogus"], "paid": {"blueprint": 2, "xray": 2, "white": 0, "layers": 3}})
    assert got == {"free": ["layers"], "paid": {"blueprint": 2}}          # xray is free since 2026-11-18
    text = editor.instructions("long", got)
    assert "recipe may be layers, blueprint (at most 2 in the video)" in text and "Do not use puppets" in text
    assert "PUPPET SHOT FORMAT" in editor.instructions("long") and "glass:" in editor.instructions("long")


def test_a_paid_style_is_used_only_when_switched_on_and_only_up_to_its_count(monkeypatch):
    monkeypatch.setattr(editor, "PAID_LOOKS", ("blueprint",))
    monkeypatch.setattr(editor, "FREE_LOOKS", tuple(k for k in editor.FREE_LOOKS if k != "blueprint"))
    x = dict(recipe="blueprint", recipe_brief="A GPU", object3d="chip", move3d="explode")
    lines = _lines()
    raw = {"scenes": [_scene(**x)]}
    off = editor.build(raw, lines, 4.0, "long", [], None, [], [])
    assert not any(s["type"] == "recipe_clip" for s in off["scenes"])          # not switched on: no spend
    on = editor.build(raw, lines, 4.0, "long", [], None, [], [], looks=editor.looks_for({"paid": {"blueprint": 1}}))
    assert [s["data"]["recipe"] for s in on["scenes"] if s["type"] == "recipe_clip"] == ["blueprint"]


def test_a_free_style_scene_carries_its_fill_and_needs_no_brief():
    fill = {"stops": ["Prompt", "Memory", "Blackwell", "Answer"]}
    raw = {"scenes": [_scene(recipe="circuit", fill=json.dumps(fill))]}
    edit = editor.build(raw, _lines(), 4.0, "long", [], None, [], [])
    sc = next(s for s in edit["scenes"] if s["type"] == "recipe_clip")
    assert sc["data"]["fill"] == fill and sc["data"]["recipe"] == "circuit"
    off = editor.build(raw, _lines(), 4.0, "long", [], None, [], [], looks=editor.looks_for({"free": []}))
    assert not any(s["type"] == "recipe_clip" for s in off["scenes"])


def test_free_fills_rewrite_only_the_content_block_and_stretch_to_the_beat():
    code = recipes.fill_code("layers", {"layers": [{"name": "App"}, {"name": "Model"}, {"name": "Chips"}]}, 6.0)
    assert '"APP"' in code and "D = 6.000" in code and "api.update(t * k)" in code
    import pytest
    with pytest.raises(ValueError):
        recipes.content_block("circuit", {"stops": ["one", "two"]})
    with pytest.raises(ValueError):
        recipes.content_block("glass", {"first": {"name": "a", "parts": 3}, "second": {"name": "b", "parts": 3},
                                        "captions": ["a"] * 5})
    with pytest.raises(ValueError):
        recipes.content_block("xray", {})
    assert set(recipes.FREE) | set(recipes.PAID) == set(recipes.RECIPES)


def test_any_object_is_read_from_named_parts_and_fitted():
    """2026-11-18 (owner: every script has different objects): the engine's 3D part format, named, any object."""
    parts = recipes.object_parts(["body: box 0 0 0 4 2 1", "motor: cyl 1 0 1 1 1 1", "motor: cyl -1 0 1 1 1 1 rx90 gold",
                                  "nonsense", "x: box 0 0 0 0 1 1"], (8.0, 3.0, 8.0))
    assert [p["name"] for p in parts] == ["body", "motor", "motor"] and parts[2]["gold"]
    assert max(p["c"][0] + p["s"][0] / 2 for p in parts) <= 4.0 and min(p["c"][1] - p["s"][1] / 2 for p in parts) == 0
    import pytest
    with pytest.raises(ValueError):
        recipes.object_parts(["just words"], (1, 1, 1))


def test_blueprint_draws_any_structure_from_parts():
    fill = {"title": ["Gravity", "dam", "x"], "dims": ["420 m", "90 m", "130 m"],
            "build": ["wall: box 0 0 0 10 2 6", "spillway: box 0 -1.6 0 2.2 1.2 3.6"],
            "notes": [{"at": "Wall", "lines": ["concrete", "wall", "x"]}, {"at": "tower", "lines": ["x"]}]}
    scene = recipes.blueprint_layout(fill)
    assert scene["title"] == ["GRAVITY", "DAM"] and scene["dims"] == ["420 M", "90 M", "130 M"]
    assert scene["notes"] == [{"at": "wall", "lines": ["CONCRETE", "WALL"]}] and len(scene["build"]) == 2
    code = recipes.fill_code("blueprint", fill, 7.0)
    assert "__SCENE__" not in code and '"duration": 7.0' in code and "blueprint-kit" in code
    assert "blueprint" in recipes.FREE and not editor.PAID_LOOKS
    import pytest
    with pytest.raises(ValueError):
        recipes.blueprint_layout({"build": ["wall: box 0 0 0 1 1 1"], "notes": [{"at": "roof", "lines": ["x"]}]})


def test_x_ray_shows_any_object_from_parts():
    fill = {"object": "Delivery drone", "flow": "magic", "build": ["body: box 0 0 0 2 2 0.6", "battery: box 0 0 0.1 1 0.6 0.3"],
            "parts": [{"part": "battery", "name": "Battery", "note": "20 minutes"}, {"part": "engine", "name": "x"}]}
    scene = recipes.xray_layout(fill)
    assert scene["object"] == "DELIVERY DRONE" and scene["flow"] == "current"
    assert [p["part"] for p in scene["parts"]] == ["battery"] and scene["parts"][0]["name"] == "BATTERY"
    assert "x-ray-kit" in recipes.fill_code("xray", fill, 6.0)
    assert "xray" in recipes.FREE and "xray" in editor.FREE_LOOKS and not editor.PAID_LOOKS


def test_white_model_builds_what_its_pieces_do_not_have():
    scene = recipes.white_layout({"stops": [{"kind": "mine", "name": "Copper mine", "build": ["headframe: box 0 0 0 2 2 4", "wheel: cyl 0 0 4 1.5 0.3 1.5 rx90 gold"]},
                                            {"kind": "factory", "name": "Smelter"}],
                                  "extras": ["tree", {"build": ["silo: cyl 0 0 0 1 1 3"]}]})
    kinds = [p["kind"] for p in scene["pieces"]]
    assert kinds[:2] == ["custom", "factory"] and "custom" in kinds[2:] and scene["pieces"][0]["build"][1]["gold"]


def test_circuit_city_is_a_kit_of_board_parts():
    """2026-11-18: 2-6 stops, each a real part of a board, in the signal's order; plain names keep the reference's four."""
    old = recipes.circuit_layout({"stops": ["Prompt", "HBM memory", "Blackwell", "Answer"]})
    assert [s["kind"] for s in old["stops"]] == ["port", "memory", "processor", "port"]
    assert [s["name"] for s in old["stops"]] == ["PROMPT", "HBM MEMORY", "BLACKWELL", "ANSWER"]
    assert [s["ref"] for s in old["stops"]] == ["J1", "U1", "U2", "J2"]
    fill = {"stops": [{"kind": "sensor", "name": "Camera"}, {"kind": "lidar", "name": "Lidar"}, {"kind": "battery", "name": "Battery"}]}
    scene = recipes.circuit_layout(fill)
    assert [s["kind"] for s in scene["stops"]] == ["sensor", "chip", "battery"]          # never dropped
    code = recipes.fill_code("circuit", fill, 7.0)
    assert "__SCENE__" not in code and '"duration": 7.0' in code and "registerStyle" in code
    import pytest
    with pytest.raises(ValueError):
        recipes.circuit_layout({"stops": [{"kind": "port", "name": "only one"}]})


def test_white_model_is_a_free_kit_laid_out_by_code():
    """2026-11-18: the storyboard names the stops and extras; code places them so pieces never overlap."""
    fill = {"stops": [{"kind": "factory", "name": "tsmc", "note": "makes the chips"}, {"kind": "ship", "name": "Singapore"},
                      {"kind": "datacenter", "name": "Malaysia"}, {"kind": "spaceship", "name": "x"}],
            "extras": ["road", "car", "tree", "bogus"], "accent": "#76b900"}
    scene = recipes.white_layout(fill)
    stops = [p for p in scene["pieces"] if p.get("id")]
    assert [p["kind"] for p in stops] == ["factory", "ship", "datacenter"] and scene["path"] == ["s0", "s1", "s2"]
    xs = [(p["at"][0], recipes.WHITE_PIECES[p["kind"]] * p["scale"]) for p in stops]
    for (a, wa), (b, wb) in zip(xs, xs[1:]):
        assert b - wb / 2 >= a + wa / 2                         # no two stops overlap
    assert scene["steps"][0]["name"] == "TSMC" and scene["accent"] == "#76b900"
    assert any(p["kind"] == "road" for p in scene["pieces"]) and not any(p["kind"] == "bogus" for p in scene["pieces"])
    code = recipes.fill_code("white", fill, 6.0)
    assert "__SCENE__" not in code and '"duration": 6.0' in code and "white-model-kit" in code
    assert "white" in recipes.FREE and "white" in editor.FREE_LOOKS and "white" not in editor.PAID_LOOKS
    try:
        recipes.white_layout({"stops": [{"kind": "house"}]})
    except ValueError:
        pass
    else:
        raise AssertionError("one stop is not a flow")
    assert "THE REAL THING ONLY" in editor.instructions("long")
