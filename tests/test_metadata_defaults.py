from golide_engine.orchestration.production import apply_locked_upload_defaults


def test_locked_upload_defaults_override_model_language_values():
    metadata = {
        "title": "A title",
        "description": "A description",
        "video_language": "English",
        "title_description_language": "English (United States)",
    }
    policy = {
        "upload_defaults": {
            "video_language": "en",
            "title_description_language": "en",
        }
    }

    normalized = apply_locked_upload_defaults(metadata, policy)

    assert normalized["video_language"] == "en"
    assert normalized["title_description_language"] == "en"
    assert normalized["title"] == "A title"
    assert metadata["video_language"] == "English"
