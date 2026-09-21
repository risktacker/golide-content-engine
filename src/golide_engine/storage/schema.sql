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
    media_purged_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analytics_video ON analytics_daily(youtube_video_id);
CREATE INDEX IF NOT EXISTS idx_cost_production ON cost_events(production_id);
CREATE INDEX IF NOT EXISTS idx_stage_production ON stage_runs(production_id, stage);

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

-- Distribution System v1: lightweight content records only. Media bytes never
-- belong in SQLite/GitHub; media_ref is an ephemeral object-storage pointer.
CREATE TABLE IF NOT EXISTS content_posts (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK(kind IN ('social', 'video')),
    content_class TEXT NOT NULL DEFAULT 'post' CHECK(content_class IN ('post', 'short', 'long')),
    title TEXT NOT NULL DEFAULT '',
    master_text TEXT NOT NULL,
    weekly_theme TEXT NOT NULL DEFAULT '',
    content_lane TEXT NOT NULL DEFAULT '',
    value_units_json TEXT NOT NULL DEFAULT '[]',
    product_bridge_position INTEGER CHECK(product_bridge_position IS NULL OR product_bridge_position IN (2,3)),
    product_url TEXT NOT NULL DEFAULT '',
    product_mode TEXT NOT NULL DEFAULT 'brand' CHECK(product_mode IN ('brand','specific_product','auto_product')),
    product_id TEXT NOT NULL DEFAULT '',
    owner_voice_media_ref TEXT,
    media_approved INTEGER NOT NULL DEFAULT 0,
    qa_approved INTEGER NOT NULL DEFAULT 0,
    release_approved INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK(status IN ('draft', 'scheduled', 'publishing', 'published', 'partial', 'failed')),
    scheduled_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS social_variants (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL REFERENCES content_posts(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL,
    parts_json TEXT NOT NULL DEFAULT '[]',
    media_ref TEXT,
    status TEXT NOT NULL CHECK(status IN ('pending', 'published', 'failed')),
    platform_content_id TEXT,
    published_url TEXT,
    last_error TEXT,
    published_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(post_id, platform)
);

CREATE TABLE IF NOT EXISTS publish_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL REFERENCES content_posts(id) ON DELETE CASCADE,
    variant_id TEXT NOT NULL REFERENCES social_variants(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('published', 'failed')),
    remote_id TEXT,
    error TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_content_posts_due
ON content_posts(status, scheduled_at);

CREATE INDEX IF NOT EXISTS idx_social_variants_post
ON social_variants(post_id, status);

CREATE INDEX IF NOT EXISTS idx_publish_attempts_post
ON publish_attempts(post_id, created_at);


-- Connected accounts store secret references only; tokens remain in the platform
-- secret manager and are never written into SQLite.
CREATE TABLE IF NOT EXISTS social_accounts (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    account_label TEXT NOT NULL DEFAULT '',
    external_account_id TEXT NOT NULL,
    transport TEXT NOT NULL CHECK(transport IN ('official_api', 'self_hosted', 'unified_connector', 'browser_session', 'assisted_send')),
    credential_ref TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('connected', 'disconnected', 'error')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(platform, external_account_id)
);

CREATE TABLE IF NOT EXISTS inbox_threads (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    external_thread_id TEXT NOT NULL,
    account_id TEXT NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    participant_ref TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK(status IN ('open', 'closed')),
    last_message_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(platform, external_thread_id)
);

CREATE TABLE IF NOT EXISTS inbox_messages (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES inbox_threads(id) ON DELETE CASCADE,
    external_message_id TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('inbound', 'outbound')),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(thread_id, external_message_id)
);

CREATE TABLE IF NOT EXISTS temporary_media (
    id TEXT PRIMARY KEY,
    object_key TEXT NOT NULL UNIQUE,
    media_kind TEXT NOT NULL CHECK(media_kind IN ('image', 'audio', 'video', 'render_asset')),
    post_id TEXT REFERENCES content_posts(id) ON DELETE SET NULL,
    status TEXT NOT NULL CHECK(status IN ('active', 'ready_for_cleanup', 'deleted')),
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_inbox_threads_open
ON inbox_threads(status, last_message_at);

CREATE INDEX IF NOT EXISTS idx_inbox_messages_thread
ON inbox_messages(thread_id, created_at);

CREATE INDEX IF NOT EXISTS idx_temporary_media_cleanup
ON temporary_media(status, expires_at);

