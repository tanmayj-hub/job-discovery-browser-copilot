from __future__ import annotations

import csv
import importlib
from pathlib import Path

import yaml

import main as cli_main
from review.saved_job_review import (
    DEFAULT_VERIFIED_SNAPSHOT_PATH,
    export_saved_jobs_review,
    write_verified_saved_jobs_snapshot,
)
from storage.db import initialize_database, record_source_observation, upsert_companies, upsert_job


def _write_verified_yaml(path: Path) -> None:
    payload = {
        "verified_companies": [
            {
                "company_name": "Verified Co",
                "verified": True,
                "verified_at": "2026-06-14",
                "scope": "Canada",
                "status": "usable",
                "notes": "Trusted source.",
            },
            {
                "company_name": "BMO",
                "verified": True,
                "verified_at": "2026-06-14",
                "scope": "Canada",
                "status": "usable",
                "confidence": "provisional",
                "notes": "Provisional verified source.",
            },
            {
                "company_name": "RBC",
                "verified": False,
                "verified_at": "2026-06-14",
                "scope": "Canada",
                "status": "needs_manual_audit",
                "notes": "Exclude from verified-only review export.",
            },
        ]
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _seed_review_data(tmp_path: Path) -> tuple[object, Path, Path]:
    db_path = tmp_path / "job_discovery.db"
    verified_path = tmp_path / "verified_companies.yaml"
    snapshot_path = tmp_path / "latest-verified-saved-jobs.csv"
    _write_verified_yaml(verified_path)
    connection = initialize_database(db_path)
    upsert_companies(
        connection,
        [
            {
                "name": "Verified Co",
                "sector": "IT Consulting & Systems Integrators",
                "category": "Consulting/SI",
                "careers_url": "https://verified.example.com/careers",
                "website_category": "company-careers",
                "ats_hint": "",
                "canada_hubs_notes": "Toronto",
                "role_families": ["Cloud"],
                "keywords": ["cloud"],
                "priority": "High",
                "monitoring_hint": "Manual check",
                "status": "Watching",
                "source_mode": "browser_allowed",
            },
            {
                "name": "BMO",
                "sector": "Banking & Capital Markets",
                "category": "Bank/Market",
                "careers_url": "https://bmo.example.com/careers",
                "website_category": "company-careers",
                "ats_hint": "",
                "canada_hubs_notes": "Toronto",
                "role_families": ["Cloud"],
                "keywords": ["cloud"],
                "priority": "High",
                "monitoring_hint": "Manual check",
                "status": "Watching",
                "source_mode": "browser_allowed",
            },
            {
                "name": "RBC",
                "sector": "Banking & Capital Markets",
                "category": "Bank/Market",
                "careers_url": "https://rbc.example.com/careers",
                "website_category": "company-careers",
                "ats_hint": "",
                "canada_hubs_notes": "Toronto",
                "role_families": ["Cloud"],
                "keywords": ["cloud"],
                "priority": "High",
                "monitoring_hint": "Manual check",
                "status": "Watching",
                "source_mode": "browser_allowed",
            },
        ],
    )
    for company_name, saved_count in (("Verified Co", 1), ("BMO", 1), ("RBC", 1)):
        record_source_observation(
            connection,
            company_name=company_name,
            source_name="company-careers",
            source_mode="browser_allowed",
            careers_url=f"https://{company_name.lower().replace(' ', '')}.example.com/careers",
            collector="browser",
            status="completed",
            jobs_discovered=saved_count,
            jobs_scored=saved_count,
            jobs_relevant=saved_count,
            jobs_saved=saved_count,
            source_scope_status="canada_scope_confirmed",
            source_scope_confirmed=True,
        )

    verified_job = {
        "company_name": "Verified Co",
        "title": "Cloud Engineer",
        "location": "Toronto, Ontario, Canada",
        "job_url": "https://verified.example.com/jobs/1",
        "apply_url": "https://verified.example.com/jobs/1/apply",
        "source_name": "company-careers",
        "source_mode": "browser_allowed",
        "description": "AWS Terraform role",
        "first_seen_at": "2026-06-10T00:00:00Z",
        "last_seen_at": "2026-06-14T21:10:48Z",
        "match_score": 44,
        "match_reasons": ["title matches target role: Cloud Engineer"],
        "risk_flags": [],
        "status": "saved",
    }
    bmo_job = {
        "company_name": "BMO",
        "title": "Platform Engineer",
        "location": "Toronto, Ontario, Canada",
        "job_url": "https://bmo.example.com/jobs/2",
        "apply_url": "https://bmo.example.com/jobs/2/apply",
        "source_name": "company-careers",
        "source_mode": "browser_allowed",
        "description": "AWS platform role",
        "first_seen_at": "2026-06-12T00:00:00Z",
        "last_seen_at": "2026-06-14T21:10:48Z",
        "match_score": 50,
        "match_reasons": ["title matches target role: Platform Engineer"],
        "risk_flags": [],
        "status": "new",
    }
    rejected_job = {
        "company_name": "Verified Co",
        "title": "Rejected Role",
        "location": "Toronto, Ontario, Canada",
        "job_url": "https://verified.example.com/jobs/3",
        "source_name": "company-careers",
        "source_mode": "browser_allowed",
        "description": "Not a fit",
        "first_seen_at": "2026-06-12T00:00:00Z",
        "last_seen_at": "2026-06-14T21:10:48Z",
        "match_score": 5,
        "match_reasons": ["location signals: Toronto"],
        "risk_flags": [],
        "status": "rejected",
    }
    rbc_job = {
        "company_name": "RBC",
        "title": "Cloud Support Engineer",
        "location": "Toronto, Ontario, Canada",
        "job_url": "https://rbc.example.com/jobs/4",
        "source_name": "company-careers",
        "source_mode": "browser_allowed",
        "description": "Excluded because RBC is not yet verified usable.",
        "first_seen_at": "2026-06-12T00:00:00Z",
        "last_seen_at": "2026-06-14T21:10:48Z",
        "match_score": 42,
        "match_reasons": ["title matches target role: Cloud Support Engineer"],
        "risk_flags": [],
        "status": "saved",
    }

    for job in (verified_job, bmo_job, rejected_job, rbc_job):
        upsert_job(connection, job)

    write_verified_saved_jobs_snapshot(
        [verified_job, bmo_job, rejected_job, rbc_job],
        verified_companies_path=verified_path,
        output_path=snapshot_path,
    )
    return connection, verified_path, snapshot_path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_review_export_includes_unchanged_saved_jobs_and_all_usable_verified_companies(
    tmp_path: Path,
) -> None:
    connection, verified_path, snapshot_path = _seed_review_data(tmp_path)
    output_path = tmp_path / "saved-jobs-review.csv"

    rows = export_saved_jobs_review(
        connection,
        verified_companies_path=verified_path,
        output_path=output_path,
        saved_jobs_snapshot_path=snapshot_path,
    )

    assert len(rows) == 2
    assert {row["company"] for row in rows} == {"Verified Co", "BMO"}


def test_review_export_includes_provisional_bmo(tmp_path: Path) -> None:
    connection, verified_path, snapshot_path = _seed_review_data(tmp_path)
    output_path = tmp_path / "saved-jobs-review.csv"

    rows = export_saved_jobs_review(
        connection,
        verified_companies_path=verified_path,
        output_path=output_path,
        saved_jobs_snapshot_path=snapshot_path,
    )

    assert any(row["company"] == "BMO" for row in rows)


def test_review_export_excludes_needs_manual_audit_companies(tmp_path: Path) -> None:
    connection, verified_path, snapshot_path = _seed_review_data(tmp_path)
    output_path = tmp_path / "saved-jobs-review.csv"

    export_saved_jobs_review(
        connection,
        verified_companies_path=verified_path,
        output_path=output_path,
        saved_jobs_snapshot_path=snapshot_path,
    )
    rows = _read_csv(output_path)

    assert all(row["company"] != "RBC" for row in rows)


def test_review_export_excludes_rejected_jobs(tmp_path: Path) -> None:
    connection, verified_path, snapshot_path = _seed_review_data(tmp_path)
    output_path = tmp_path / "saved-jobs-review.csv"

    export_saved_jobs_review(
        connection,
        verified_companies_path=verified_path,
        output_path=output_path,
        saved_jobs_snapshot_path=snapshot_path,
    )
    rows = _read_csv(output_path)

    assert all(row["title"] != "Rejected Role" for row in rows)


def test_review_export_includes_blank_user_fields(tmp_path: Path) -> None:
    connection, verified_path, snapshot_path = _seed_review_data(tmp_path)
    output_path = tmp_path / "saved-jobs-review.csv"

    export_saved_jobs_review(
        connection,
        verified_companies_path=verified_path,
        output_path=output_path,
        saved_jobs_snapshot_path=snapshot_path,
    )
    rows = _read_csv(output_path)

    assert rows[0]["user_decision"] == ""
    assert rows[0]["user_notes"] == ""


def test_review_export_preserves_core_fields(tmp_path: Path) -> None:
    connection, verified_path, snapshot_path = _seed_review_data(tmp_path)
    output_path = tmp_path / "saved-jobs-review.csv"

    export_saved_jobs_review(
        connection,
        verified_companies_path=verified_path,
        output_path=output_path,
        saved_jobs_snapshot_path=snapshot_path,
    )
    rows = _read_csv(output_path)

    verified_row = next(row for row in rows if row["company"] == "Verified Co")
    assert verified_row["job_url"] == "https://verified.example.com/jobs/1"
    assert verified_row["score"] == "44"
    assert verified_row["relevance_tier"] == "core_target_fit"
    assert "Cloud Engineer" in verified_row["match_reasons"]


def test_review_export_cli_writes_csv(tmp_path: Path, monkeypatch, capsys) -> None:
    connection, verified_path, snapshot_path = _seed_review_data(tmp_path)
    output_path = tmp_path / "review" / "saved-jobs-review.csv"

    monkeypatch.setattr(cli_main, "VERIFIED_COMPANIES_CONFIG_PATH", verified_path)
    monkeypatch.setattr(cli_main, "VERIFIED_REVIEW_SNAPSHOT_PATH", snapshot_path)
    monkeypatch.setattr(
        cli_main,
        "get_storage_api",
        lambda: {
            "initialize_database": lambda _path: connection,
            "get_dashboard_overview": lambda _connection: {"total_companies": 1},
            "upsert_companies": lambda _connection, _companies: None,
        },
    )
    monkeypatch.setattr(cli_main, "load_companies_config", lambda: [])
    monkeypatch.setattr(cli_main, "get_collection_api", lambda: {})
    monkeypatch.setattr(cli_main, "get_onboarding_api", lambda: {})
    monkeypatch.setattr(cli_main, "get_reports_api", lambda: {})
    monkeypatch.setattr(cli_main, "get_audit_api", lambda: {})

    exit_code = cli_main.main(["review", "export-saved-jobs", "--output", str(output_path)])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert output_path.exists()
    assert "exported_rows" in captured
    assert "BMO" in captured


def test_review_snapshot_writer_uses_expected_default_path(tmp_path: Path) -> None:
    _, verified_path, _ = _seed_review_data(tmp_path)
    rows = write_verified_saved_jobs_snapshot(
        [
            {
                "company_name": "Verified Co",
                "title": "Cloud Engineer",
                "job_url": "https://verified.example.com/jobs/1",
                "match_score": 44,
                "match_reasons": ["title matches target role: Cloud Engineer"],
                "risk_flags": [],
                "status": "saved",
            }
        ],
        verified_companies_path=verified_path,
        output_path=tmp_path / DEFAULT_VERIFIED_SNAPSHOT_PATH.name,
    )

    assert len(rows) == 1


def test_dashboard_import_smoke() -> None:
    module = importlib.import_module("dashboard.app")

    assert hasattr(module, "main")
