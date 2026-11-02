"""Owner direction 2026-11-03: sales videos from Studio, built from the owner's own script."""

from pathlib import Path

from PIL import Image

from golide_engine.engine.content_rules import script_text
from golide_engine.orchestration.sales import cover_plate, is_sale, owner_script_plan, sale_research, with_link
from golide_engine.youtube_metadata import social_caption

SCRIPT = ("Most job seekers send a hundred applications and hear nothing back. That is not bad luck, "
          "it is a broken system, and this book shows you the one I built to turn applications into "
          "interviews, step by step, with the exact templates I used. Get it on Amazon today.")


def test_plan_keeps_every_word_in_order_and_lines_stay_short():
    plan = owner_script_plan(SCRIPT, "The Book")
    assert script_text(plan).split() == SCRIPT.split()
    assert all(len(line["text"].split()) <= 14 for line in plan["lines"])
    assert plan["lines"][0]["section"] == "claim" and plan["lines"][-1]["section"] == "cta"


def test_spec_detection_research_and_link():
    spec = {"purpose": "sales-video", "title": "The Book",
            "sale": {"link": "https://amazon.com/dp/X", "product_name": "The Book"}}
    assert is_sale(spec) and not is_sale({"purpose": "channel-automation"})
    assert sale_research(spec)["claims"][0]["source_url"] == "https://amazon.com/dp/X"
    assert with_link("About the book.", "https://amazon.com/dp/X").startswith("Get it here: https://amazon.com/dp/X")
    assert with_link("https://amazon.com/dp/X is here", "https://amazon.com/dp/X") == "https://amazon.com/dp/X is here"


def test_caption_carries_the_buy_link():
    meta = {"description": "A book.", "keywords": ["job search"], "hashtags": ["#jobs"],
            "buy_link": "https://amazon.com/dp/X"}
    caption = social_caption("The Book", meta, 2200)
    assert caption.split("\n\n")[1] == "Get it here: https://amazon.com/dp/X"


def test_cover_becomes_a_product_plate(tmp_path):
    src = tmp_path / "cover.jpg"
    Image.new("RGB", (600, 900), (200, 40, 40)).save(src)
    target = cover_plate(src, tmp_path / "scene-01.png")
    assert Image.open(target).mode == "RGBA"
    assert target.with_suffix(".plate.json").exists()
