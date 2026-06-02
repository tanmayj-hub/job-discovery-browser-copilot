from __future__ import annotations

import sqlite3
from pathlib import Path

from storage.db import (
    append_intervention_notes,
    create_intervention,
    get_intervention_queue,
    get_interventions,
    get_job_by_id,
    get_new_jobs,
    initialize_database,
    update_intervention_status,
    update_job_status,
    upsert_companies,
    upsert_job,
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
        "source_mode": "direct",
    }


def _sample_job(**overrides: object) -> dict[str, object]:
    job = {
        "company_name": "Example Co",
        "title": "Cloud Engineer",
        "location": "Toronto, Ontario, Canada",
        "job_url": "https://careers.example.com/jobs/1",
        "apply_url": "https://careers.example.com/jobs/1/apply",
        "source_name": "greenhouse",
        "source_mode": "direct",
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


def test_insert_job(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_sample_company()])

    job_id = upsert_job(connection, _sample_job())
    stored_job = get_job_by_id(connection, job_id)

    assert stored_job is not None
    assert stored_job["title"] == "Cloud Engineer"
    assert stored_job["match_score"] == 88
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
