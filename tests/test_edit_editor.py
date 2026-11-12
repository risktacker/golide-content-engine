import unittest
from pathlib import Path

from golide_engine.edit import editor
from golide_engine.vector.align import TimedLine, Word


def _lines(texts):
    out, t = [], 0.0
    for i, tx in enumerate(texts):
        ws = []
        for w in tx.split():
            ws.append(Word(w.strip(".,?"), t, t + 0.3))
            t += 0.35
        out.append(TimedLine(i, tx, "", "", "", "", ws[0].start, ws[-1].end, ws))
        t += 0.3
    return out


class EditorTest(unittest.TestCase):
    def setUp(self):
        self.lines = _lines(["Fable 5.2 is out today.", "Output costs $40 per million tokens.", "Is it worth it?",
                             "Follow for more."])
        self.sources = [{"ok": True, "url": "https://platform.claude.com/x", "title": "Fable", "top": "01-top.png",
                         "highlights": [{"phrase": "$40", "rects": [[800, 300, 40, 28]]}]}]

    def test_schema_is_strict(self):
        scene = editor.EDIT_SCHEMA["properties"]["scenes"]["items"]
        self.assertEqual(set(scene["required"]), set(scene["properties"]))

    def test_build_times_and_repairs(self):
        raw = {"scenes": [
            {"type": "studio", "first_line": 0, "last_line": 0, "poses": [{"pose": "shock", "word": "today"}],
             "screen_words": "Fable 5.2 is here", "punch": "Fable"},
            {"type": "source", "first_line": 1, "last_line": 1, "source": 0, "phrase": 0, "callout": "$40",
             "callout_sub": "per million tokens", "edge": "glass", "goli_corner": True, "poses": []},
            {"type": "source", "first_line": 2, "last_line": 2, "source": 7, "phrase": 0, "screen_words": "Worth it?"},
            # line 3 missing: the last scene must stretch over it
        ]}
        edit = editor.build(raw, self.lines, 12.0, "short", self.sources, Path("/tmp"), [], [])
        types = [s["type"] for s in edit["scenes"]]
        self.assertEqual(types[:4], ["host", "browser_shot", "host", "kinetic_title"])
        for sc in edit["scenes"]:             # the pace rule: no block holds the screen too long on a Short
            if sc["type"] != "host":
                self.assertLessEqual(sc["duration"], editor.BEAT["short"] * 1.6 + 0.9, sc["type"])
        self.assertTrue(edit["captions"] and edit["captions"][0]["words"])
        lower = edit["scenes"][2]["data"]
        self.assertEqual(lower["place"], "lower")      # Short: Goli stays below the cards, no corner pop-ins
        self.assertEqual([p["pose"] for p in lower["poses"]][:1], ["point_up"])
        self.assertTrue(any("source 7" in n for n in edit["notes"]))
        host = edit["scenes"][0]["data"]
        self.assertEqual(host["place"], "studio")
        self.assertEqual([p["pose"] for p in host["poses"]], ["talk", "shock"])
        shot = edit["scenes"][1]
        self.assertAlmostEqual(shot["data"]["highlights"][0]["at"], max(0.6, self.lines[1].words[2].start - shot["start"]), 2)  # card lands first
        last = edit["scenes"][-1]
        self.assertAlmostEqual(last["start"] + last["duration"], 12.0)
        self.assertAlmostEqual(edit["scenes"][2]["duration"], 12.0 - edit["scenes"][1]["start"])
        starts = [s["start"] for s in edit["scenes"] if s["type"] != "host" or s["data"]["place"] == "studio"]
        self.assertEqual(starts, sorted(starts))

    def test_request_marks(self):
        text = editor.request("T", self.lines, self.sources, [], {3})
        self.assertIn("(FOLLOW)", text)
        self.assertIn("0 [fact] $40", text)
        self.assertIn("BEATS", text)

    def test_beats_are_short_and_inside_lines(self):
        long_line = _lines(["one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen"])
        out = editor.beats(long_line, "short")
        self.assertGreaterEqual(len(out), 2)
        for b in out:
            self.assertLessEqual(b.end - b.start, 3.2)
        self.assertEqual(" ".join(b.text for b in out), long_line[0].text)
        self.assertEqual([b.index for b in out], list(range(len(out))))

    def test_shots_cover_page_blocks(self):
        page = dict(self.sources[0], headline=[10, 10, 500, 60], blocks=[{"text": "A long paragraph about it", "rect": [1, 2, 3, 4]}])
        kinds = [s["kind"] for s in editor.shots(page)]
        self.assertEqual(kinds, ["fact", "headline", "text"])


if __name__ == "__main__":
    unittest.main()


def test_bookends_vary_and_frame_the_video():
    from types import SimpleNamespace

    from golide_engine.edit import editor as E

    seen = {E.pick_bookends("Story", [], [], n)[0] for n in range(40)}
    assert len(seen) >= 5                                            # many different openings
    intro, outro = E.pick_bookends("Story", ["walk_in", "pop_up", "coffee"], ["end_card"], 3)
    assert intro not in ("walk_in", "pop_up", "coffee") and outro != "end_card"   # never the last ones again
    assert E.pick_bookends("Nvidia stock crashed", [], [], 1)[0] != "coffee"      # no calm coffee on a crash
    lines = [SimpleNamespace(text="What just happened", start=0.0, end=2.0),
             SimpleNamespace(text="The end of the story", start=58.0, end=60.0)]
    scenes = [{"type": "kinetic_title", "start": 0.0, "duration": 30.0, "data": {}},
              {"type": "kinetic_title", "start": 30.0, "duration": 30.0, "data": {}}]
    out = E._bookends(scenes, lines, [], 60.0, "walk_in", "lights_off")
    assert out[0]["data"]["intro"] == "walk_in" and out[-1]["data"]["outro"] == "lights_off"
    assert out[1]["start"] >= out[0]["duration"] and out[-2]["start"] + out[-2]["duration"] <= out[-1]["start"] + 1e-6


def test_close_marked_as_intro_becomes_close():
    from types import SimpleNamespace

    from golide_engine.engine.story import plan_from_story
    from golide_engine.vector.chapters import chapter_marks

    story = {"title": "t", "chapters": [{"number": "", "title": "Intro"}, {"number": "01", "title": "One"}],
             "script": "[[0]] Hello there friend. [[1]] The first part is here. [[0]] And that is the close of it."}
    plan = plan_from_story(story, "long")
    assert plan["chapters"][-1]["title"] == "Close"
    assert [l["chapter"] for l in plan["lines"]] == sorted(l["chapter"] for l in plan["lines"])
    bad = {"chapters": [{"number": "", "title": "Intro"}, {"number": "01", "title": "One"}],
           "lines": [{"text": "a", "chapter": 0}, {"text": "b", "chapter": 1}, {"text": "c", "chapter": 0}]}
    timed = [SimpleNamespace(index=i, start=float(i * 20), section="proof") for i in range(3)]
    assert [m.title for m in chapter_marks(bad, timed)] == ["Intro", "One", "Close"]
