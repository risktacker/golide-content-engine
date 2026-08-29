RESEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "claims": {"type": "array", "items": {"type": "object", "properties": {
            "claim": {"type": "string"}, "source_title": {"type": "string"},
            "source_url": {"type": "string"}, "published_or_updated": {"type": "string"},
        }, "required": ["claim", "source_title", "source_url", "published_or_updated"], "additionalProperties": False}},
    },
    "required": ["summary", "claims"], "additionalProperties": False,
}

STORYBOARD_SCHEMA = {
    "type": "object",
    "properties": {"scenes": {"type": "array", "items": {"type": "object", "properties": {
        "id": {"type": "string"}, "duration": {"type": "number"}, "visual_caption": {"type": "string"},
        "visual_prompt": {"type": "string"},
        "subject_bounds": {"type": "array", "items": {"type": "object", "properties": {
            "x": {"type": "number"}, "y": {"type": "number"}, "width": {"type": "number"}, "height": {"type": "number"},
        }, "required": ["x", "y", "width", "height"], "additionalProperties": False}},
    }, "required": ["id", "duration", "visual_caption", "visual_prompt", "subject_bounds"], "additionalProperties": False}}},
    "required": ["scenes"], "additionalProperties": False,
}

METADATA_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"}, "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "category_id": {"type": "integer"}, "video_language": {"type": "string"},
        "recording_location": {"type": ["string", "null"]}, "location_is_material": {"type": "boolean"},
        "altered_content": {"type": "boolean"}, "chapters": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "description", "tags", "category_id", "video_language", "recording_location", "location_is_material", "altered_content", "chapters"],
    "additionalProperties": False,
}
