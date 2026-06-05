from __future__ import annotations

import sqlite3
from pathlib import Path

from storage.db import (
    append_intervention_notes,
    build_job_identity,
    compute_content_hash,
    create_intervention,
    get_intervention_queue,
    get_interventions,
    get_job_by_id,
    get_new_jobs,
    get_source_status_rows,
    initialize_database,
    record_source_observation,
    update_intervention_status,
    update_job_status,
    upsert_companies,
    upsert_job,
    upsert_job_record,
)


def _sample_company() -> dict[str, object]:
    return {
        "name": "Example Co",
        "sector": "IT Consulting & Systems Integrators",
        "category": "Consulting/SI",
        "careers_url": "https://careers.example.com",
        "website_category": "greenhouse",
        "ats_hint": "greenhouse",
        "canada_hubs_notes": "Toronto",
        "role_families": ["Cloud", "DevOps"],
        "keywords": ["cloud", "terraform"],
        "priority": "High",
        "monitoring_hint": "Manual check",
        "status": "Watching",
        "source_mode": "api_allowed",
    }


def _sample_job(**overrides: object) -> dict[str, object]:
    job = {
        "company_name": "Example Co",
        "title": "Cloud Engineer",
        "location": "Toronto, Ontario, Canada",
        "job_url": "https://careers.example.com/jobs/1",
        "apply_url": "https://careers.example.com/jobs/1/apply",
        "source_name": "greenhouse",
        "source_mode": "api_allowed",
        "description": "AWS, Kubernetes, Terraform, and Linux support role.",
        "date_posted": "2026-06-02",
        "last_seen": "2026-06-02T08:00:00",
        "match_score": 88,
        "match_reasons": ["title matches target role", "matched skills: AWS, Kubernetes"],
        "status": "new",
    }
    job.update(overrides)
    return job


def test_initialize_database_creates_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "job_discovery.db"

    connection = initialize_database(db_path)
    tables = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        ).fetchall()
    }

    assert {"companies", "sources", "jobs", "daily_runs", "interventions"}.issubset(tables)


def test_initialize_database_adds_new_job_metadata_columns(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(jobs)").fetchall()
    }

    assert {
        "external_job_id",
        "ats_type",
        "board_slug",
        "raw_payload_json",
        "content_hash",
        "first_seen_at",
        "last_seen_at",
        "last_updated_at",
    }.issubset(columns)


def test_initialize_database_adds_source_observability_columns(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(sources)").fetchall()
    }

    assert {
        "ats_type",
        "last_collector",
        "last_status",
        "last_error",
        "fallback_used",
        "intervention_required",
        "jobs_discovered",
        "jobs_scored",
        "jobs_relevant",
        "jobs_saved",
        "jobs_inserted",
        "jobs_updated",
        "jobs_unchanged",
        "duplicates_skipped",
        "last_success_at",
        "consecutive_failures",
        "readiness_label",
    }.issubset(columns)


def test_initialize_database_migrates_old_jobs_table(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy_job_discovery.db"
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE companies (
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
        CREATE TABLE sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_mode TEXT NOT NULL,
            careers_url TEXT,
            website_category TEXT,
            ats_hint TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            last_checked TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(company_name, source_name)
        );
        CREATE TABLE jobs (
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
            first_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            match_score INTEGER NOT NULL DEFAULT 0,
            match_reasons TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE daily_runs (
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
        CREATE TABLE interventions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            company_name TEXT,
            intervention_type TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolved_at TEXT
        );
        """
    )
    connection.commit()
    connection.close()

    migrated = initialize_database(db_path)
    columns = {
        row["name"] for row in migrated.execute("PRAGMA table_info(jobs)").fetchall()
    }

    assert "external_job_id" in columns
    assert "content_hash" in columns
    assert "first_seen_at" in columns
    assert "last_seen_at" in columns
    assert "last_updated_at" in columns


def test_insert_job(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_sample_company()])

    job_id = upsert_job(connection, _sample_job())
    stored_job = get_job_by_id(connection, job_id)

    assert stored_job is not None
    assert stored_job["title"] == "Cloud Engineer"
    assert stored_job["match_score"] == 88
    assert stored_job["ats_type"] is None
    assert stored_job["content_hash"] == compute_content_hash(_sample_job())
    assert stored_job["first_seen_at"] is not None
    assert stored_job["last_seen_at"] == "2026-06-02T08:00:00"
    assert stored_job["last_updated_at"] == "2026-06-02T08:00:00"
    assert stored_job["match_reasons"] == [
        "title matches target role",
        "matched skills: AWS, Kubernetes",
    ]
    assert get_new_jobs(connection)[0]["id"] == job_id


def test_duplicate_job_update_reuses_existing_row(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_sample_company()])

    first_id = upsert_job(connection, _sample_job())
    second_id = upsert_job(
        connection,
        _sample_job(
            description="Updated description with Azure and Python.",
            match_score=92,
            match_reasons=["updated score"],
            last_seen="2026-06-03T09:30:00",
        ),
    )

    stored_job = get_job_by_id(connection, first_id)
    job_count = connection.execute("SELECT COUNT(*) AS count FROM jobs").fetchone()["count"]

    assert second_id == first_id
    assert job_count == 1
    assert stored_job is not None
    assert stored_job["description"] == "Updated description with Azure and Python."
    assert stored_job["match_score"] == 92
    assert stored_job["match_reasons"] == ["updated score"]
    assert stored_job["last_seen"] == "2026-06-03T09:30:00"
    assert stored_job["last_seen_at"] == "2026-06-03T09:30:00"
    assert stored_job["last_updated_at"] == "2026-06-03T09:30:00"


def test_same_unchanged_job_only_updates_last_seen(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_sample_company()])

    first_result = upsert_job_record(
        connection,
        _sample_job(
            first_seen_at="2026-06-02T08:00:00",
            last_seen_at="2026-06-02T08:00:00",
        ),
    )
    second_result = upsert_job_record(
        connection,
        _sample_job(
            first_seen_at="2026-06-02T08:00:00",
            last_seen_at="2026-06-03T10:15:00",
        ),
    )

    stored_job = get_job_by_id(connection, first_result.job_id)

    assert second_result.job_id == first_result.job_id
    assert second_result.action == "unchanged"
    assert stored_job is not None
    assert stored_job["first_seen_at"] == "2026-06-02T08:00:00"
    assert stored_job["last_seen_at"] == "2026-06-03T10:15:00"
    assert stored_job["last_updated_at"] == "2026-06-02T08:00:00"


def test_greenhouse_external_identity_prevents_duplicate_rows(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_sample_company()])

    first_id = upsert_job(
        connection,
        _sample_job(
            job_url="https://boards.greenhouse.io/example/jobs/12345",
            source_name="greenhouse",
            external_job_id="12345",
            ats_type="greenhouse",
            board_slug="example",
        ),
    )
    second_id = upsert_job(
        connection,
        _sample_job(
            job_url="https://boards.greenhouse.io/example/jobs/12345?gh_jid=12345",
            source_name="greenhouse",
            external_job_id="12345",
            ats_type="greenhouse",
            board_slug="example",
            description="Updated description",
            last_seen_at="2026-06-04T09:00:00",
        ),
    )

    count = connection.execute("SELECT COUNT(*) AS count FROM jobs").fetchone()["count"]
    stored_job = get_job_by_id(connection, first_id)

    assert second_id == first_id
    assert count == 1
    assert stored_job is not None
    assert stored_job["external_job_id"] == "12345"
    assert stored_job["board_slug"] == "example"
    assert stored_job["description"] == "Updated description"


def test_lever_external_identity_prevents_duplicate_rows(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_sample_company()])

    first_id = upsert_job(
        connection,
        _sample_job(
            job_url="https://jobs.lever.co/example/abc123",
            source_name="lever",
            external_job_id="abc123",
            ats_type="lever",
            board_slug="example",
        ),
    )
    second_id = upsert_job(
        connection,
        _sample_job(
            job_url="https://jobs.lever.co/example/abc123/",
            source_name="lever",
            external_job_id="abc123",
            ats_type="lever",
            board_slug="example",
        ),
    )

    count = connection.execute("SELECT COUNT(*) AS count FROM jobs").fetchone()["count"]

    assert second_id == first_id
    assert count == 1


def test_api_jobs_with_same_title_and_location_keep_distinct_external_ids(
    tmp_path: Path,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_sample_company()])

    first_id = upsert_job(
        connection,
        _sample_job(
            title="DevOps Engineer",
            location="Canada - Toronto",
            source_name="lever",
            job_url="https://jobs.lever.co/example/abc123",
            external_job_id="abc123",
            ats_type="lever",
            board_slug="example",
        ),
    )
    second_id = upsert_job(
        connection,
        _sample_job(
            title="DevOps Engineer",
            location="Canada - Toronto",
            source_name="lever",
            job_url="https://jobs.lever.co/example/xyz789",
            external_job_id="xyz789",
            ats_type="lever",
            board_slug="example",
        ),
    )

    count = connection.execute("SELECT COUNT(*) AS count FROM jobs").fetchone()["count"]

    assert second_id != first_id
    assert count == 2


def test_build_job_identity_prioritizes_company_ats_board_and_external_id() -> None:
    identity = build_job_identity(
        _sample_job(
            external_job_id="12345",
            ats_type="greenhouse",
            board_slug="example",
        )
    )

    assert identity == (
        "company_ats_board_external",
        "example co",
        "greenhouse",
        "example",
        "12345",
    )


def test_update_status(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_sample_company()])
    job_id = upsert_job(connection, _sample_job())

    update_job_status(connection, job_id, "reviewed")
    stored_job = get_job_by_id(connection, job_id)

    assert stored_job is not None
    assert stored_job["status"] == "reviewed"


def test_update_status_rejects_invalid_value(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_sample_company()])
    job_id = upsert_job(connection, _sample_job())

    try:
        update_job_status(connection, job_id, "archived")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid status to raise ValueError")


def test_jobs_require_existing_company(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    try:
        upsert_job(connection, _sample_job())
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("Expected foreign key violation for missing company")


def test_intervention_storage_and_queue_fields(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_sample_company()])

    intervention_id = create_intervention(
        connection,
        intervention_type="browser_pause",
        company_name="Example Co",
        source_url="https://careers.example.com",
        reason="captcha_detected",
        notes="CAPTCHA blocked the page.",
    )

    queue = get_intervention_queue(connection)

    assert intervention_id == queue[0]["id"]
    assert queue[0]["company_name"] == "Example Co"
    assert queue[0]["source_url"] == "https://careers.example.com"
    assert queue[0]["reason"] == "captcha_detected"
    assert queue[0]["status"] == "pending"
    assert queue[0]["action_required"] == "Review manually. Do not continue automatically."


def test_intervention_status_updates_and_notes(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_sample_company()])

    intervention_id = create_intervention(
        connection,
        intervention_type="browser_pause",
        company_name="Example Co",
        reason="login_required",
        notes="Initial note.",
    )

    append_intervention_notes(connection, intervention_id, "Follow-up note.")
    update_intervention_status(connection, intervention_id, "resolved")
    record = next(
        item for item in get_interventions(connection) if item["id"] == intervention_id
    )

    assert record["status"] == "resolved"
    assert record["resolved_at"] is not None
    assert "Initial note." in record["notes"]
    assert "Follow-up note." in record["notes"]


def test_record_source_observation_persists_latest_status(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_sample_company()])

    record_source_observation(
        connection,
        company_name="Example Co",
        source_name="greenhouse",
        source_mode="api_allowed",
        careers_url="https://careers.example.com",
        website_category="greenhouse",
        ats_hint="greenhouse",
        ats_type="greenhouse",
        collector="greenhouse_api",
        status="success",
        jobs_discovered=2,
        jobs_scored=2,
        jobs_relevant=1,
        jobs_saved=1,
        jobs_inserted=1,
        duplicates_skipped=1,
    )

    source = get_source_status_rows(connection)[0]

    assert source["collector"] == "greenhouse_api"
    assert source["status"] == "success"
    assert source["ats_type"] == "greenhouse"
    assert source["jobs_discovered"] == 2
    assert source["jobs_saved"] == 1
    assert source["duplicates_skipped"] == 1
    assert source["readiness_label"] == "ready_api"
    assert source["last_success_at"] is not None


def test_record_source_observation_tracks_failures(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_sample_company()])

    record_source_observation(
        connection,
        company_name="Example Co",
        source_name="greenhouse",
        source_mode="api_allowed",
        collector="greenhouse_api",
        status="error",
        error="API timeout",
    )
    record_source_observation(
        connection,
        company_name="Example Co",
        source_name="greenhouse",
        source_mode="api_allowed",
        collector="greenhouse_api",
        status="error",
        error="API timeout",
    )

    source = get_source_status_rows(connection)[0]

    assert source["consecutive_failures"] == 2
    assert source["error"] == "API timeout"
    assert source["readiness_label"] == "error"
