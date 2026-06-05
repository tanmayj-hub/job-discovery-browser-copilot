PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sector TEXT NOT NULL,
    category TEXT NOT NULL,
    careers_url TEXT,
    website_category TEXT,
    ats_hint TEXT,
    canada_hubs_notes TEXT,
    role_families TEXT NOT NULL DEFAULT '[]',
    keywords TEXT NOT NULL DEFAULT '[]',
    priority TEXT,
    monitoring_hint TEXT,
    status TEXT,
    source_mode TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_mode TEXT NOT NULL,
    careers_url TEXT,
    website_category TEXT,
    ats_hint TEXT,
    ats_type TEXT,
    last_collector TEXT,
    last_status TEXT,
    last_error TEXT,
    fallback_used INTEGER NOT NULL DEFAULT 0,
    intervention_required INTEGER NOT NULL DEFAULT 0,
    jobs_discovered INTEGER NOT NULL DEFAULT 0,
    jobs_scored INTEGER NOT NULL DEFAULT 0,
    jobs_relevant INTEGER NOT NULL DEFAULT 0,
    jobs_saved INTEGER NOT NULL DEFAULT 0,
    jobs_inserted INTEGER NOT NULL DEFAULT 0,
    jobs_updated INTEGER NOT NULL DEFAULT 0,
    jobs_unchanged INTEGER NOT NULL DEFAULT 0,
    duplicates_skipped INTEGER NOT NULL DEFAULT 0,
    last_success_at TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    readiness_label TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    last_checked TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_name, source_name),
    FOREIGN KEY (company_name) REFERENCES companies(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    job_url TEXT,
    apply_url TEXT,
    source_name TEXT,
    source_mode TEXT NOT NULL,
    description TEXT,
    date_posted TEXT,
    external_job_id TEXT,
    ats_type TEXT,
    board_slug TEXT,
    raw_payload_json TEXT,
    content_hash TEXT,
    first_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    first_seen_at TEXT,
    last_seen_at TEXT,
    last_updated_at TEXT,
    match_score INTEGER NOT NULL DEFAULT 0,
    match_reasons TEXT NOT NULL DEFAULT '[]',
    risk_flags TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'saved', 'rejected', 'reviewed', 'needs_manual_review')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_name) REFERENCES companies(name) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_jobs_company_name ON jobs(company_name);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_job_url ON jobs(job_url);

CREATE TABLE IF NOT EXISTS daily_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    run_date TEXT NOT NULL DEFAULT CURRENT_DATE,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    jobs_seen INTEGER NOT NULL DEFAULT 0,
    jobs_new INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS interventions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    company_name TEXT,
    intervention_type TEXT NOT NULL,
    reason TEXT,
    source_url TEXT,
    action_required TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL,
    FOREIGN KEY (company_name) REFERENCES companies(name) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_interventions_job_id ON interventions(job_id);
