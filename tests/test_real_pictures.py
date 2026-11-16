"""2026-11-17 (owner): real pictures of the people and products in the story (no face blurring), and the
person's photo on the thumbnail when the story is about him."""
from golide_engine.engine.source_capture import named_subjects
from golide_engine.vector import thumb_engine as E


def test_the_story_names_its_people_and_products():
    research = {"core_fact": "Nvidia CEO Jensen Huang said the Blackwell chips sold out.",
                "claims": [{"claim": "Jensen Huang told investors Nvidia shipped Blackwell GPUs."},
                           {"claim": "Nvidia revenue rose 62% in the quarter."},
                           {"claim": "Microsoft and Meta bought Blackwell racks."}]}
    got = named_subjects(research, "Jensen Huang Just Explained Why Nvidia Wins")
    assert {"Jensen Huang", "Nvidia", "Blackwell"} <= set(got) and "Explained Why Nvidia" not in got


def test_a_person_story_can_use_the_photo_card():
    design = E.BY_NAME["photo_card"]
    assert design.fits(E.Story("t", "W", "W", photo=__file__, person="Jensen Huang"))
    assert not design.fits(E.Story("t", "W", "W", photo=__file__))


def test_pages_are_never_blurred_any_more():
    import inspect
    from golide_engine.engine import source_capture
    assert "blur_faces(" not in inspect.getsource(source_capture.capture)
