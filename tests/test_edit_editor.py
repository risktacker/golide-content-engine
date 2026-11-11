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
        self.assertEqual(types, ["host", "browser_shot", "host", "kinetic_title"])
        lower = edit["scenes"][2]["data"]
        self.assertEqual(lower["place"], "lower")      # Short: Goli stays below the cards, no corner pop-ins
        self.assertEqual([p["pose"] for p in lower["poses"]][:1], ["point_up"])
        self.assertTrue(any("source 7" in n for n in edit["notes"]))
        host = edit["scenes"][0]["data"]
        self.assertEqual(host["place"], "studio")
        self.assertEqual([p["pose"] for p in host["poses"]], ["talk", "shock"])
        shot = edit["scenes"][1]
        self.assertAlmostEqual(shot["data"]["highlights"][0]["at"], max(0.9, self.lines[1].words[2].start - shot["start"]), 2)  # card lands first
        last = edit["scenes"][-1]
        self.assertAlmostEqual(last["start"] + last["duration"], 12.0)
        self.assertAlmostEqual(edit["scenes"][2]["duration"], 12.0 - edit["scenes"][1]["start"])
        starts = [s["start"] for s in edit["scenes"] if s["type"] != "host" or s["data"]["place"] == "studio"]
        self.assertEqual(starts, sorted(starts))

    def test_request_marks(self):
        text = editor.request("T", self.lines, self.sources, [], {3})
        self.assertIn("(FOLLOW)", text)
        self.assertIn('0: "$40"', text)


if __name__ == "__main__":
    unittest.main()
