PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS productions (
    production_id TEXT PRIMARY KEY,
    format TEXT NOT NULL CHECK(format IN ('short', 'long')),
    concept_family TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    approved INTEGER NOT NULL DEFAULT 0,
    scheduled_at TEXT,
    youtube_video_id TEXT UNIQUE,
    parameters_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stage_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_id TEXT NOT NULL REFERENCES productions(production_id),
    stage TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    error TEXT,
    UNIQUE(production_id, stage, attempt)
);

CREATE TABLE IF NOT EXISTS cost_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_id TEXT NOT NULL REFERENCES productions(production_id),
    stage TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_units REAL NOT NULL DEFAULT 0,
    cached_input_units REAL NOT NULL DEFAULT 0,
    output_units REAL NOT NULL DEFAULT 0,
    images INTEGER NOT NULL DEFAULT 0,
    audio_minutes REAL NOT NULL DEFAULT 0,
    characters INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL,
    provider_request_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analytics_daily (
    day TEXT NOT NULL,
    youtube_video_id TEXT NOT NULL,
    production_id TEXT REFERENCES productions(production_id),
    views INTEGER NOT NULL DEFAULT 0,
    engaged_views INTEGER NOT NULL DEFAULT 0,
    likes INTEGER NOT NULL DEFAULT 0,
    comments INTEGER NOT NULL DEFAULT 0,
    shares INTEGER NOT NULL DEFAULT 0,
    subscribers_gained INTEGER NOT NULL DEFAULT 0,
    subscribers_lost INTEGER NOT NULL DEFAULT 0,
    average_view_duration REAL NOT NULL DEFAULT 0,
    average_view_percentage REAL NOT NULL DEFAULT 0,
    estimated_revenue REAL NOT NULL DEFAULT 0,
    raw_json TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    PRIMARY KEY(day, youtube_video_id)
);

CREATE TABLE IF NOT EXISTS feedback_factors (
    format TEXT NOT NULL,
    parameter_key TEXT NOT NULL,
    parameter_value TEXT NOT NULL,
    sample_size INTEGER NOT NULL,
    performance_score REAL NOT NULL,
    score_adjustment REAL NOT NULL,
    calculated_at TEXT NOT NULL,
    PRIMARY KEY(format, parameter_key, parameter_value)
);

CREATE TABLE IF NOT EXISTS uploads (
    production_id TEXT PRIMARY KEY REFERENCES productions(production_id),
    youtube_video_id TEXT UNIQUE,
    privacy_status TEXT NOT NULL,
    scheduled_at TEXT,
    upload_status TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL UNIQUE,
    uploaded_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analytics_video ON analytics_daily(youtube_video_id);
CREATE INDEX IF NOT EXISTS idx_cost_production ON cost_events(production_id);
CREATE INDEX IF NOT EXISTS idx_stage_production ON stage_runs(production_id, stage);
CREATE INDEX IF NOT EXISTS idx_upload_uploaded_at ON uploads(uploaded_at);

CREATE TABLE IF NOT EXISTS budget_allocations (
    production_id TEXT NOT NULL REFERENCES productions(production_id),
    provider TEXT NOT NULL,
    month TEXT NOT NULL,
    budget_class TEXT NOT NULL CHECK(budget_class IN ('scheduled', 'independent')),
    allocated_usd REAL NOT NULL CHECK(allocated_usd >= 0),
    created_at TEXT NOT NULL,
    PRIMARY KEY(production_id, provider, month)
);

CREATE TABLE IF NOT EXISTS budget_pauses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_id TEXT NOT NULL REFERENCES productions(production_id),
    stage TEXT NOT NULL,
    provider TEXT NOT NULL,
    reason TEXT NOT NULL,
    required_usd REAL NOT NULL DEFAULT 0,
    remaining_usd REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS topic_demand_snapshots (
    cache_key TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    format TEXT NOT NULL CHECK(format IN ('short', 'long')),
    score REAL NOT NULL,
    verdict TEXT NOT NULL CHECK(verdict IN ('pass', 'reject')),
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_budget_month ON budget_allocations(provider, budget_class, month);
CREATE INDEX IF NOT EXISTS idx_budget_pause_open ON budget_pauses(production_id, resolved_at);
CREATE INDEX IF NOT EXISTS idx_topic_demand_created ON topic_demand_snapshots(created_at);
