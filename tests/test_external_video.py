"""Owner direction 2026-11-03: the owner's own video, built from his script and recording."""

from PIL import Image

from golide_engine.engine.content_rules import script_text
from golide_engine.orchestration.external import (external_research, is_external, owner_script_plan,
                                                  reference_note, reference_plate, with_link)
from golide_engine.youtube_metadata import social_caption

SCRIPT = ("Most job seekers send a hundred applications and hear nothing back. That is not bad luck, "
          "it is a broken system, and here is the one I built to turn applications into "
          "interviews, step by step, with the exact templates I used. Try it today.")


def test_plan_keeps_every_word_in_order_and_lines_stay_short():
    plan = owner_script_plan(SCRIPT, "")
    assert script_text(plan).split() == SCRIPT.split()
    assert all(len(line["text"].split()) <= 14 for line in plan["lines"])


def test_spec_detection_research_reference_and_link():
    spec = {"purpose": "external-video",
            "external": {"link": "https://example.com/x", "reference_link": "https://example.com/thing"}}
    assert is_external(spec) and not is_external({"purpose": "channel-automation"})
    assert external_research(spec)["claims"][0]["source_url"] == "https://example.com/x"
    assert "https://example.com/thing" in reference_note(spec)
    assert reference_note({"purpose": "external-video", "external": {}}) == ""
    assert with_link("About it.", "https://example.com/x").startswith("Link: https://example.com/x")


def test_link_in_captions_but_not_on_instagram():
    meta = {"description": "A video.", "keywords": ["job search"], "hashtags": ["#jobs"], "link": "https://example.com/x"}
    assert social_caption("Title", meta, 2200).split("\n\n")[1] == "Link: https://example.com/x"
    assert "https://example.com/x" not in social_caption("Title", meta, 2200, include_link=False)


def test_reference_picture_becomes_a_product_plate(tmp_path):
    src = tmp_path / "ref.jpg"
    Image.new("RGB", (600, 900), (200, 40, 40)).save(src)
    target = reference_plate(src, tmp_path / "scene-01.png")
    assert Image.open(target).mode == "RGBA" and target.with_suffix(".plate.json").exists()
