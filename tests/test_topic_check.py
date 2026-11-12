"""2026-11-12 (owner): research, script and title are about one topic, checked at every step."""
import datetime as dt

from golide_engine.orchestration.topic_check import checked_title, chosen_topic, core_problem, topic_packet

SPEC = {"model_title": "Did Anthropic Just Justify Its $1 Trillion IPO?",
        "selected_topic_source": "https://www.anthropic.com/claude-fable-and-mythos-5-2",
        "brief": "Use the viral model launch as a way to explain...",
        "topic_candidates": [
            {"model_title": "Something else", "authoritative_source_url": "https://other.example"},
            {"model_title": "Did Anthropic Just Justify Its $1 Trillion IPO?",
             "authoritative_source_url": "https://www.anthropic.com/claude-fable-and-mythos-5-2",
             "evidence_summary": "Anthropic introduces Claude Fable 5.2 and Claude Mythos 5.2.",
             "broke_on": "Fireship's explainer reached a 1.6x breakout."}]}


def test_research_and_script_are_told_the_topic():
    packet = topic_packet(SPEC, dt.date(2026, 11, 12))
    assert "Fable 5.2" in packet                         # the brief alone never named it
    assert "https://www.anthropic.com/claude-fable-and-mythos-5-2" in packet
    assert "2026-11-12" in packet
    assert chosen_topic(SPEC)["broke_on"].startswith("Fireship")


def test_unverified_topic_stops_before_the_script():
    assert core_problem({"claims": [], "core_fact": {"fact": "", "source_url": "", "published_or_updated": "",
                                                      "verified": False}})
    assert not core_problem({"core_fact": {"fact": "Fable 5.2 launched", "source_url": "https://anthropic.com/x",
                                           "published_or_updated": "2026-11-10", "verified": True}})
    assert not core_problem({"claims": []})          # older research without the check is not judged


def test_title_follows_the_script():
    title = "Did Anthropic Just Justify Its $1 Trillion IPO?"
    assert checked_title({"unsupported": [], "title": title}, title) == (title, [])
    new, wrong = checked_title({"unsupported": ["Fable 5.2"], "title": "Did AI Just Stop Being a Chatbot?"}, title)
    assert new == "Did AI Just Stop Being a Chatbot?" and wrong == ["Fable 5.2"]
    assert checked_title({"unsupported": ["x"], "title": ""}, title) == (title, [])
