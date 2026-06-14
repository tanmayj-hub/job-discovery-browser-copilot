from __future__ import annotations

import csv
import importlib
from pathlib import Path

import yaml

import main as cli_main
from review.saved_job_review import export_saved_jobs_review
from storage.db import (
    initialize_database,
    record_source_observation,
    upsert_companies,
    upsert_job,
)


def _write_verified_yaml(path: Path) -> None:
    payload = {
        "verified_companies": [
            {
                "company_name": "Verified Co",
                "verified": True,
                "verified_at": "2026-06-14",
                "scope": "Canada",
                "status": "usable",
                "confidence": "provisional",
                "notes": "Provisional review source.",
            },
            {
                "company_name": "Other Co",
                "verified": False,
                "verified_at": "2026-06-14",
                "scope": "Canada",
                "status": "needs_review",
                "notes": "Not usable.",
            },
        ]
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _seed_review_data(tmp_path: Path) -> tuple[object, Path]:
    db_path = tmp_path / "job_discovery.db"
    verified_path = tmp_path / "verified_companies.yaml"
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
                "name": "Other Co",
                "sector": "Banking & Capital Markets",
                "category": "Bank/Market",
                "careers_url": "https://other.example.com/careers",
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
    record_source_observation(
        connection,
        company_name="Verified Co",
        source_name="company-careers",
        source_mode="browser_allowed",
        careers_url="https://verified.example.com/careers",
        collector="browser",
        status="completed",
        jobs_discovered=2,
        jobs_scored=2,
        jobs_relevant=2,
        jobs_saved=2,
        source_scope_status="canada_scope_confirmed",
        source_scope_confirmed=True,
    )
    record_source_observation(
        connection,
        company_name="Other Co",
        source_name="company-careers",
        source_mode="browser_allowed",
        careers_url="https://other.example.com/careers",
        collector="browser",
        status="completed",
        jobs_discovered=1,
        jobs_scored=1,
        jobs_relevant=1,
        jobs_saved=1,
        source_scope_status="canada_scope_confirmed",
        source_scope_confirmed=True,
    )
    upsert_job(
        connection,
        {
            "company_name": "Verified Co",
            "title": "Cloud Engineer",
            "location": "Toronto, Ontario, Canada",
            "job_url": "https://verified.example.com/jobs/1",
            "apply_url": "https://verified.example.com/jobs/1/apply",
            "source_name": "company-careers",
            "source_mode": "browser_allowed",
            "description": "AWS Terraform role",
            "first_seen_at": "2099-01-01T00:00:00Z",
            "last_seen_at": "2099-01-01T00:00:00Z",
            "match_score": 44,
            "match_reasons": ["title matches target role: Cloud Engineer"],
            "risk_flags": [],
            "status": "saved",
        },
    )
    upsert_job(
        connection,
        {
            "company_name": "Verified Co",
            "title": "Rejected Role",
            "location": "Toronto, Ontario, Canada",
            "job_url": "https://verified.example.com/jobs/2",
            "source_name": "company-careers",
            "source_mode": "browser_allowed",
            "description": "Not a fit",
            "first_seen_at": "2099-01-01T00:00:00Z",
            "last_seen_at": "2099-01-01T00:00:00Z",
            "match_score": 5,
            "match_reasons": ["location signals: Toronto"],
            "risk_flags": [],
            "status": "rejected",
        },
    )
    upsert_job(
        connection,
        {
            "company_name": "Other Co",
            "title": "Platform Engineer",
            "location": "Toronto, Ontario, Canada",
            "job_url": "https://other.example.com/jobs/3",
            "source_name": "company-careers",
            "source_mode": "browser_allowed",
            "description": "Other company role",
            "first_seen_at": "2099-01-01T00:00:00Z",
            "last_seen_at": "2099-01-01T00:00:00Z",
            "match_score": 50,
            "match_reasons": ["title matches target role: Platform Engineer"],
            "risk_flags": [],
            "status": "saved",
        },
    )
    return connection, verified_path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_review_export_includes_verified_company_saved_jobs(tmp_path: Path) -> None:
    connection, verified_path = _seed_review_data(tmp_path)
    output_path = tmp_path / "saved-jobs-review.csv"

    rows = export_saved_jobs_review(
        connection,
        verified_companies_path=verified_path,
        output_path=output_path,
    )

    assert len(rows) == 1
    assert rows[0]["company"] == "Verified Co"
    assert rows[0]["title"] == "Cloud Engineer"


def test_review_export_includes_blank_user_fields(tmp_path: Path) -> None:
    connection, verified_path = _seed_review_data(tmp_path)
    output_path = tmp_path / "saved-jobs-review.csv"

    export_saved_jobs_review(
        connection,
        verified_companies_path=verified_path,
        output_path=output_path,
    )
    rows = _read_csv(output_path)

    assert rows[0]["user_decision"] == ""
    assert rows[0]["user_notes"] == ""


def test_review_export_excludes_rejected_jobs(tmp_path: Path) -> None:
    connection, verified_path = _seed_review_data(tmp_path)
    output_path = tmp_path / "saved-jobs-review.csv"

    export_saved_jobs_review(
        connection,
        verified_companies_path=verified_path,
        output_path=output_path,
    )
    rows = _read_csv(output_path)

    assert all(row["title"] != "Rejected Role" for row in rows)


def test_review_export_preserves_core_fields(tmp_path: Path) -> None:
    connection, verified_path = _seed_review_data(tmp_path)
    output_path = tmp_path / "saved-jobs-review.csv"

    export_saved_jobs_review(
        connection,
        verified_companies_path=verified_path,
        output_path=output_path,
    )
    rows = _read_csv(output_path)

    assert rows[0]["job_url"] == "https://verified.example.com/jobs/1"
    assert rows[0]["score"] == "44"
    assert rows[0]["relevance_tier"] == "core_target_fit"
    assert "Cloud Engineer" in rows[0]["match_reasons"]


def test_review_export_cli_writes_csv(tmp_path: Path, monkeypatch, capsys) -> None:
    connection, verified_path = _seed_review_data(tmp_path)
    output_path = tmp_path / "review" / "saved-jobs-review.csv"

    monkeypatch.setattr(cli_main, "VERIFIED_COMPANIES_CONFIG_PATH", verified_path)
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


def test_dashboard_import_smoke() -> None:
    module = importlib.import_module("dashboard.app")

    assert hasattr(module, "main")
