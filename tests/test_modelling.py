"""Model what is trending (owner direction 2026-10-22).

A long video models a long video and a short models a short; the source must be
taking numbers; our title is the source title with one to three words changed;
the script email shows the source; no trending video means no script; scripts
end on verdicts, not homework, and never reuse recent openings.
"""
import inspect
import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace as NS
from unittest import mock

from golide_engine.youtube import breakouts as bo

NOW = datetime(2026, 10, 22, 10, tzinfo=timezone.utc)


def fake_youtube(videos, channels, seen=None):
    run = lambda value: NS(execute=lambda: value)  # noqa: E731

    def search_list(**kw):
        if seen is not None:
            seen.append(kw)
        return run({"items": [{"id": {"videoId": k}} for k in videos]})
    return NS(
        search=lambda: NS(list=search_list),
        videos=lambda: NS(list=lambda id, **kw: run({"items": [videos[i] for i in id.split(",")]})),
        channels=lambda: NS(list=lambda id, **kw: run({"items": [channels[i] for i in id.split(",")]})),
    )


def video(vid, title, views, duration, channel="c", hours_ago=10):
    published = datetime.fromtimestamp(NOW.timestamp() - hours_ago * 3600, timezone.utc)
    return {"id": vid, "snippet": {"title": title, "channelId": channel, "channelTitle": channel,
                                   "publishedAt": published.isoformat().replace("+00:00", "Z"), "categoryId": "28"},
            "statistics": {"viewCount": str(views)}, "contentDetails": {"duration": duration}}


CHANNELS = {"c": {"id": "c", "statistics": {"viewCount": "100000000", "videoCount": "1000", "subscriberCount": "1"}}}


class FormatAndNumbersTests(unittest.TestCase):
    def test_durations(self):
        self.assertEqual(603, bo.duration_seconds("PT10M3S"))
        self.assertEqual(3600, bo.duration_seconds("PT1H"))
        self.assertEqual(0, bo.duration_seconds("junk"))

    def test_long_models_long_only_and_asks_youtube_for_that_length(self):
        seen = []
        yt = fake_youtube({"s": video("s", "Elon Musk New Flying Car", 317000, "PT40S"),
                           "l": video("l", "Tesla Roadster Flight Explained", 300000, "PT11M")}, CHANNELS, seen)
        found = bo.find_breakouts(yt, "long", now=NOW, queries=("tesla",))
        self.assertEqual(["Tesla Roadster Flight Explained"], [b["title"] for b in found])
        self.assertEqual(660, found[0]["duration_seconds"])
        self.assertEqual("medium", seen[0]["videoDuration"])

    def test_short_models_shorts_only(self):
        yt = fake_youtube({"s": video("s", "Elon Musk New Flying Car", 317000, "PT40S"),
                           "l": video("l", "Tesla Roadster Flight Explained", 300000, "PT11M")}, CHANNELS)
        found = bo.find_breakouts(yt, "short", now=NOW, queries=("tesla",))
        self.assertEqual(["Elon Musk New Flying Car"], [b["title"] for b in found])

    def test_numbers_bar_drops_videos_that_are_not_taking_numbers(self):
        # 5,000 views in 10 hours = 500/hour, and only 0.05x its channel's 100k average.
        yt = fake_youtube({"w": video("w", "Weak Tesla Video", 5000, "PT9M")}, CHANNELS)
        self.assertEqual([], bo.find_breakouts(yt, "long", now=NOW, queries=("tesla",)))
        self.assertTrue(bo.passes_bar({"views_per_hour": 2500, "breakout": 1}))
        self.assertTrue(bo.passes_bar({"views_per_hour": 100, "breakout": 6}))
        self.assertFalse(bo.passes_bar({"views_per_hour": 100, "breakout": 1}))


class TitleTweakTests(unittest.TestCase):
    def test_one_word_change_passes(self):
        self.assertEqual("", bo.title_tweak_problem("The NEW Tesla Roadster: My Honest Reaction",
                                                    "The NEW Tesla Roadster: My Honest Breakdown"))

    def test_hashtags_are_dropped_for_free(self):
        self.assertEqual("", bo.title_tweak_problem("Elon Musk New Flying Car #shorts #tesla",
                                                    "Elon Musk New Flying Roadster"))

    def test_identical_and_rewritten_titles_fail(self):
        self.assertIn("identical", bo.title_tweak_problem("Elon Musk New Flying Car", "Elon Musk New Flying Car"))
        # 22 Oct: this was the rewrite that should never have passed.
        self.assertIn("changes", bo.title_tweak_problem(
            "Elon Musk New Flying Car", "Elon Musk's Flying Roadster: How the Rocket Car Really Works"))

    def test_bad_titles_are_fixed_or_fall_back_to_one_word(self):
        from golide_engine.orchestration.production import ProductionService

        good = {"breakout": {"title": "iPhone Duo Review: The Truth"}, "model_title": "iPhone Duo Review: The Real Truth"}
        bad = {"breakout": {"title": "Elon Musk New Flying Car #shorts"}, "model_title": "A totally different title here"}
        text = NS(generate_json=mock.Mock(side_effect=RuntimeError("offline")))
        engine = NS(_reserve=lambda *a, **k: None, _record_text=lambda *a, **k: None)
        out = ProductionService._modelled_titles(engine, {}, "job", text, "m", [good, bad])
        self.assertEqual("iPhone Duo Review: The Real Truth", out[0]["model_title"])
        self.assertEqual("Elon Musk New Flying Car Explained", out[1]["model_title"])
        self.assertEqual(1, out[1]["title_changes"])


class NoFallbackTests(unittest.TestCase):
    def test_no_news_fallback_and_no_trend_means_no_script(self):
        from golide_engine.orchestration import production

        source = inspect.getsource(production.ProductionService.run)
        self.assertNotIn("There are no breakouts today", source)
        self.assertNotIn("PULSE_RULES", source)
        self.assertIn("nothing to model today", source)
        self.assertIn("_modelled_titles", source)
        self.assertIn("source_video", source)

    def test_nothing_to_model_email(self):
        from golide_engine.operations.email import build_nothing_to_model

        message = build_nothing_to_model(job_id="golide-long-2026-10-24", format_name="long",
                                         reason="no trending long video cleared the numbers bar")
        self.assertIn("No long video today", message["Subject"])
        self.assertIn("numbers bar", message.get_content())


class SourceInEmailTests(unittest.TestCase):
    MODEL = {"title": "Tesla Roadster Flight Explained", "channel": "Cars Daily", "subscribers": 8630,
             "views": 317612, "views_per_hour": 8025.7, "breakout": 20.0, "hours_old": 39.6,
             "duration_seconds": 660, "url": "https://www.youtube.com/watch?v=abc"}

    def test_email_opens_with_the_modelled_video_and_its_numbers(self):
        from golide_engine.operations.email import build_record_needed

        message = build_record_needed(job_id="j", title="Tesla Roadster Flight Really Explained", format_name="long",
                                      script="Line one.", model=self.MODEL,
                                      alternatives=[{"title": "SpaceX catch", "views": 408792,
                                                     "views_per_hour": 13515, "url": "https://youtu.be/x"}])
        plain = message.get_body(("plain",)).get_content()
        self.assertTrue(plain.startswith("MODELLED ON: Tesla Roadster Flight Explained"))
        for part in ("318K views", "8K views an hour", "20x", "length 11:00", "watch?v=abc",
                     "Our title: Tesla Roadster Flight Really Explained", "Also trending: SpaceX catch"):
            self.assertIn(part, plain)
        self.assertIn('href="https://www.youtube.com/watch?v=abc"', message.get_body(("html",)).get_content())

    def test_old_callers_without_a_model_still_work(self):
        from golide_engine.operations.email import build_record_needed

        plain = build_record_needed(job_id="j", title="t", format_name="short", script="x").get_body(("plain",))
        self.assertNotIn("MODELLED ON", plain.get_content())


class VerdictNotHomeworkTests(unittest.TestCase):
    def test_long_rules_no_longer_demand_steps(self):
        from golide_engine.engine.content_rules import LONG_STRUCTURE_RULES, chapter_problems, script_instructions

        self.assertNotIn("steps the viewer can actually do this week", LONG_STRUCTURE_RULES)
        self.assertIn("THE VIEWER LEAVES KNOWING", LONG_STRUCTURE_RULES)
        self.assertIn("MODEL THE SOURCE", LONG_STRUCTURE_RULES)
        self.assertNotIn("one small action", script_instructions("short", "golide-short-2026-10-23"))
        plan = {"chapters": [{"number": "", "title": "Intro"}, {"number": "01", "title": "A"},
                             {"number": "02", "title": "B"}, {"number": "03", "title": "C"},
                             {"number": "", "title": "Close"}],
                "lines": [{"chapter": i, "text": "A plain sentence about it here."} for i in range(5)]}
        self.assertFalse([p for p in chapter_problems(plan, "long") if "steps" in p])

    def test_marked_lines_are_banned_phrases(self):
        from golide_engine.engine.content_rules import flow_problems

        lines = ["That distinction brings us to the airborne footage.", "This week, use those five checks.",
                 "And the car flies.", "But only for a moment.", "Because the gas runs out.",
                 "Then it lands.", "So it is a prototype.", "And the car flies again."]
        problems = " ".join(flow_problems({"lines": [{"text": t} for t in lines]}))
        self.assertIn("that distinction brings us", problems)
        self.assertIn("this week, use", problems)

    def test_no_rotating_stock_turns(self):
        from golide_engine.engine import content_rules

        self.assertFalse(hasattr(content_rules, "TURN_STYLES"))
        self.assertNotIn("that's where it can go wrong", content_rules.script_variety("golide-long-2026-10-22"))


class NoRepeatTests(unittest.TestCase):
    PREVIOUS = ["[INTRO]\nIn the next few minutes, we'll follow the proposal,\nand finish with four checks you can make this week.\n"]

    def test_reused_openings_and_phrases_are_flagged(self):
        from golide_engine.engine.content_rules import repeat_problems

        plan = {"lines": [{"text": "In the next few minutes, we'll go through how it drives."},
                          {"text": "And finish with four checks you can make this week."}]}
        problems = " ".join(repeat_problems(plan, self.PREVIOUS))
        self.assertIn('"in the next..."', problems)
        self.assertIn("four checks you can make", problems)

    def test_fresh_script_passes(self):
        from golide_engine.engine.content_rules import repeat_problems

        plan = {"lines": [{"text": "Cars are supposed to stay on the road."},
                          {"text": "Tesla just made one leave it."}]}
        self.assertEqual([], repeat_problems(plan, self.PREVIOUS))

    def test_recent_scripts_come_from_published_records(self):
        import json
        import tempfile
        from pathlib import Path

        from golide_engine.orchestration.production import ProductionService

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "data" / "production-records"
            folder.mkdir(parents=True)
            for i in range(8):
                (folder / f"r{i}.json").write_text(json.dumps(
                    {"production_id": f"p{i}", "narration": f"script {i}", "recorded_at": f"2026-10-1{i}"}))
            engine = NS(root=Path(tmp))
            got = ProductionService._recent_scripts(engine, "p7")
            self.assertEqual(["script 6", "script 5", "script 4", "script 3", "script 2", "script 1"], got)


if __name__ == "__main__":
    unittest.main()


class WholeIndustryTests(unittest.TestCase):
    """2026-10-22: the sources are YouTube's charts, the tech channels and a rotating
    watchlist, not 12 fixed phrases."""

    def test_hot_terms_come_from_several_channels(self):
        items = [("Introducing Claude Duet", "anthropic"),
                 ("Anthropic Just Dropped Claude Duet (Full Breakdown)", "brock"),
                 ("Galaxy S26 Ultra Review", "mkbhd"),
                 ("iPhone 18 leak", "solo")]
        self.assertEqual(["Claude Duet"], bo.hot_terms(items, 4))

    def test_watchlist_rotates_through_everyone(self):
        names = [f"n{i}" for i in range(32)]
        seen = set()
        for day in range(4):
            seen.update(bo.rotation(names, 8, day))
        self.assertEqual(set(names), seen)
        self.assertNotEqual(bo.rotation(names, 8, 1), bo.rotation(names, 8, 2))

    def test_config_covers_the_big_ai_labs(self):
        sources = bo.load_sources()
        text = " ".join(sources["watchlist"] + sources["channels"]).lower()
        for name in ("anthropic", "openai", "gemini", "meta", "grok", "copilot", "deepseek", "samsung", "nvidia"):
            self.assertIn(name, text)
        self.assertGreaterEqual(len(sources["channels"]), 40)

    def test_full_discovery_uses_chart_channels_and_hot_term_searches(self):
        searches = []
        vids = {
            "chart1": video("chart1", "Introducing Claude Duet", 600000, "PT6M", channel="anthropic", hours_ago=20),
            "up1": video("up1", "Anthropic Just Dropped Claude Duet (Full Breakdown)", 171000, "PT7M39S",
                         channel="brock", hours_ago=18),
            "s1": video("s1", "Claude Duet hands on", 90000, "PT9M", channel="c", hours_ago=10),
        }
        chans = dict(CHANNELS, anthropic={"id": "anthropic", "statistics": {"viewCount": "1000", "videoCount": "10"}},
                     brock={"id": "brock", "statistics": {"viewCount": "1000", "videoCount": "10"}})
        run = lambda value: NS(execute=lambda: value)  # noqa: E731

        def videos_list(**kw):
            if kw.get("chart"):
                return run({"items": [vids["chart1"]] if kw["regionCode"] == "US" else []})
            return run({"items": [vids[i] for i in kw["id"].split(",") if i in vids]})

        def channels_list(**kw):
            if "forHandle" in kw:
                if kw["forHandle"] == "BrockMesarich":
                    return run({"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UUbrock"}}}]})
                return run({"items": []})
            return run({"items": [chans[i] for i in kw["id"].split(",") if i in chans]})

        def search_list(**kw):
            searches.append(kw["q"])
            return run({"items": [{"id": {"videoId": "s1"}}] if kw["q"] == "Claude Duet" else []})

        yt = NS(videos=lambda: NS(list=videos_list), channels=lambda: NS(list=channels_list),
                search=lambda: NS(list=search_list),
                playlistItems=lambda: NS(list=lambda **kw: run({"items": [
                    {"contentDetails": {"videoId": "up1", "videoPublishedAt": "2026-10-21T16:00:00Z"}}]})))
        sources = {"chart_regions": ["US", "GB"], "chart_category": "28", "channels": ["@BrockMesarich", "@nobody"],
                   "watchlist": ["Samsung Galaxy", "Waymo"], "searches_per_run": 2, "hot_terms_per_run": 4}
        with mock.patch("builtins.print"):
            found = bo.find_breakouts(yt, "long", now=NOW, sources=sources)
        self.assertEqual("Claude Duet", searches[0])                 # found without anyone listing it
        self.assertIn("Samsung Galaxy", searches)
        by = {b["title"]: b["found_by"] for b in found}
        self.assertEqual("chart US", by["Introducing Claude Duet"])
        self.assertEqual("channel @BrockMesarich", by["Anthropic Just Dropped Claude Duet (Full Breakdown)"])
        self.assertEqual("search Claude Duet", by["Claude Duet hands on"])

    def test_long_videos_get_a_72_hour_window(self):
        self.assertEqual(72, bo.FRESH_HOURS["long"])
        self.assertEqual(48, bo.FRESH_HOURS["short"])


class LongLengthTests(unittest.TestCase):
    def test_short_long_script_is_sent_back(self):
        from golide_engine.engine.content_rules import length_problems

        plan = {"lines": [{"text": "word " * 600}]}
        self.assertIn("too short", " ".join(length_problems(plan, "long")))
        plan = {"lines": [{"text": "word " * 1350}]}
        self.assertEqual([], length_problems(plan, "long"))


class TopicLockTests(unittest.TestCase):
    def test_a_chosen_topic_is_never_chosen_again_on_resume(self):
        # 22 Oct: the resumed Roadster run re-chose and uploaded under the Apple candidate's title.
        from golide_engine.orchestration import production

        source = inspect.getsource(production.ProductionService.run)
        self.assertIn("topic_locked", source)
        self.assertIn("if self.youtube is not None and not topic_locked:", source)

    def test_music_bed_is_a_little_lower(self):
        from golide_engine.vector.ambient import LEVEL_DB

        self.assertEqual(-22.0, LEVEL_DB)


class SpeedAndLanguageTests(unittest.TestCase):
    """2026-10-28: speed leads the pick, and only English videos are modelled."""

    def test_speed_beats_a_small_channel_spike(self):
        from golide_engine.youtube.breakouts import score
        self.assertGreater(score(117818, 2.7), score(32400, 24.8))

    def test_non_english_titles_are_skipped(self):
        from golide_engine.youtube.breakouts import is_english
        self.assertFalse(is_english("L'écran de leur iPhone Duo est déjà cassé !"))
        self.assertFalse(is_english("Elon Musk Sắp Cấy Chip Não Blindsight"))
        self.assertFalse(is_english("Tesla Roadster", {"defaultAudioLanguage": "fr"}))
        self.assertTrue(is_english("Is the Duo Actually a Worse Z Fold 8??"))
        self.assertTrue(is_english("Microsoft Buying Out 60,000 Employees"))
