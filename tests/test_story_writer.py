"""The story writer (owner direction 2026-11-06): the writer only tells the story; code cuts it
into screen lines; a storyboard picks gold words and pictures without touching the words."""
from golide_engine.engine.story import apply_board, plan_from_story, story_instructions

STORY = ("[[0]] On Thursday afternoon someone paid 93 cents to send one transaction. Three minutes later the "
         "main wallet was empty, and by the end of the night about 6.3 billion dollars was gone. "
         "[[1]] To see how, you need one idea about how an exchange keeps money. "
         "[[2]] So follow the channel, because when those wallets move, we will be watching.")


def test_the_story_is_cut_into_lines_without_changing_a_word():
    story = {"title": "t", "chapters": [{"number": "", "title": "Intro"}, {"number": "01", "title": "The vault"},
                                        {"number": "", "title": "Close"}], "script": STORY}
    plan = plan_from_story(story, "long")
    words = " ".join(line["text"] for line in plan["lines"]).split()
    assert words == " ".join(STORY.replace("[[0]]", "").replace("[[1]]", "").replace("[[2]]", "").split()).split()
    assert [line["chapter"] for line in plan["lines"]][0] == 0 and plan["lines"][-1]["chapter"] == 2
    assert all(len(line["text"].split()) <= 14 for line in plan["lines"])
    assert plan["lines"][-1]["follow"]


def test_a_short_has_no_chapters_and_the_board_never_changes_words():
    plan = plan_from_story({"title": "t", "chapters": [{"number": "", "title": "x"}], "script": STORY}, "short")
    assert plan["chapters"] == [] and {line["chapter"] for line in plan["lines"]} == {0}
    before = [line["text"] for line in plan["lines"]]
    picks = [{"emphasis": "93 cents", "subjects": ["coin"], "visual": "icon_hero", "label": "", "follow": False}]
    plan = apply_board(plan, {"lines": picks})
    assert [line["text"] for line in plan["lines"]] == before
    assert plan["lines"][0]["emphasis"] == "93 cents"
    assert all(line["emphasis"] for line in plan["lines"])   # defaults where the board said nothing


def test_the_writer_models_what_works_and_carries_none_of_the_old_recipe():
    text = story_instructions("long", 400)
    assert "METHOD EXAMPLE" in text and "SCRIPT VOICE GUIDE" in text
    for old in ("claim, proof, pattern", "breath-sized", "LINE RULES", "line to remember"):
        assert old not in text


def test_short_has_its_own_shape_and_long_gives_the_viewer_something():
    short, long = story_instructions("short", 50), story_instructions("long", 400)
    # a Short gets its own Short examples (2026-11-14), never the long-video ones; long gets the REA one too
    assert "A SHORT HAS ITS OWN SHAPE" in short and "SHORT METHOD EXAMPLE" in short
    assert "METHOD EXAMPLE 1, a news story" not in short and "SHORT METHOD EXAMPLE" not in long
    assert "SHORT METHOD EXAMPLE 3" in short and "METHOD EXAMPLE 3, teaching a topic" in long
    assert "THE ESSENCE" in long and "By the end of this video" in long
