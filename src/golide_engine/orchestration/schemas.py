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

ANNOTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["none", "keyword", "number", "label", "callout"]},
        "text": {"type": "string"},
        "start_offset": {"type": "number"},
        "duration": {"type": "number"},
        "position": {"type": "string", "enum": ["top", "center", "bottom", "left", "right"]},
        "color_token": {"type": "string", "enum": ["warm-ivory", "deep-navy", "neon-blue", "golide-gold", "danger-red"]},
    },
    "required": ["kind", "text", "start_offset", "duration", "position", "color_token"],
    "additionalProperties": False,
}

SECONDARY_ASSET_SCHEMA = {
    "type": "object",
    "properties": {
        "asset_key": {"type": "string"},
        "visual_prompt": {"type": "string"},
        "role": {"type": "string", "enum": ["foreground", "detail", "label", "inset"]},
        "position": {"type": "string", "enum": ["top", "center", "bottom", "left", "right"]},
        "scale": {"type": "number"},
        "entrance": {"type": "string", "enum": ["fade", "drift-left", "drift-right", "pop"]},
        "start_offset": {"type": "number"},
        "duration": {"type": "number"},
    },
    "required": ["asset_key", "visual_prompt", "role", "position", "scale", "entrance", "start_offset", "duration"],
    "additionalProperties": False,
}

MOTION_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["hold", "push-in", "pull-out", "pan-left", "pan-right", "reframe", "layer-reveal"]},
        "intensity": {"type": "string", "enum": ["subtle", "medium", "strong"]},
        "transition": {"type": "string", "enum": ["cut", "paper-wipe", "match-cut", "object-transition"]},
        "easing": {"type": "string", "enum": ["linear", "ease-in", "ease-out", "ease-in-out"]},
        "emphasis": {"type": "string"},
        "audio_cue": {"type": "string", "enum": ["none", "tick", "soft-trace", "paper", "swipe", "impact"]},
        "annotation": ANNOTATION_SCHEMA,
    },
    "required": ["type", "intensity", "transition", "easing", "emphasis", "audio_cue", "annotation"],
    "additionalProperties": False,
}

STORYBOARD_SCHEMA = {
    "type": "object",
    "properties": {"scenes": {"type": "array", "items": {"type": "object", "properties": {
        "beat_id": {"type": "string"},
        "visual_role": {"type": "string", "enum": ["ENTITY", "PROCESS", "DATA", "CONTRAST", "CAUSE_EFFECT", "REVEAL", "LIST", "DEFINITION", "CONTEXT"]},
        "asset_key": {"type": "string"},
        "visual_caption": {"type": "string"},
        "visual_prompt": {"type": "string"},
        "motion": MOTION_SCHEMA,
        "secondary_assets": {"type": "array", "items": SECONDARY_ASSET_SCHEMA},
        "subject_bounds": {"type": "array", "items": {"type": "object", "properties": {
            "x": {"type": "number"}, "y": {"type": "number"}, "width": {"type": "number"}, "height": {"type": "number"},
        }, "required": ["x", "y", "width", "height"], "additionalProperties": False}},
    }, "required": ["beat_id", "visual_role", "asset_key", "visual_caption", "visual_prompt", "motion", "secondary_assets", "subject_bounds"], "additionalProperties": False}}},
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
