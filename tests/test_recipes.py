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


def test_the_editor_makes_a_recipe_scene_with_its_words_and_a_house_3d_stand_in():
    s = {k: None for k in editor.SCENE["required"]}
    s.update(type="recipe", first_line=0, last_line=0, goli_corner=False, poses=[], rows=[], items=[], shots=[],
             points=[], brands=[], parts3d=[], recipe="xray", recipe_brief="A GPU: die, memory, heat", object3d="chip",
             move3d="explode", punch="memory")
    edit = editor.build({"scenes": [s]}, _lines(), 4.0, "long", [], None, [], [])
    sc = next(x for x in edit["scenes"] if x["type"] == "recipe_clip")
    assert sc["data"]["recipe"] == "xray" and sc["data"]["words"][0]["text"] == "Inside"
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
