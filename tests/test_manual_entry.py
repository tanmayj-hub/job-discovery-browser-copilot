from __future__ import annotations

from pathlib import Path

from dashboard.manual_entry import normalize_manual_job_entry, score_and_save_manual_job
from storage.db import initialize_database, upsert_companies


def _sample_company() -> dict[str, object]:
    return {
        "name": "Example Co",
        "sector": "IT Consulting & Systems Integrators",
        "category": "Consulting/SI",
        "careers_url": "https://careers.example.com",
        "website_category": "company-careers",
        "ats_hint": None,
        "canada_hubs_notes": "Toronto",
        "role_families": ["Cloud", "DevOps"],
        "keywords": ["cloud", "terraform"],
        "priority": "High",
        "monitoring_hint": "Manual check",
        "status": "Watching",
        "source_mode": "manual_only",
    }


def test_normalize_manual_job_entry_scores_job() -> None:
    normalized = normalize_manual_job_entry(
        {
            "company_name": "Example Co",
            "title": "Cloud Support Engineer",
            "location": "Toronto, Ontario, Canada",
            "job_url": "https://linkedin.example/jobs/1",
            "apply_url": "",
            "source_name": "LinkedIn",
            "source_mode": "manual_only",
            "description": (
                "AWS, Kubernetes, Linux, Bash, Python, troubleshooting, "
                "support, CI/CD, and CloudWatch."
            ),
            "status": "new",
        }
    )

    assert normalized["source_mode"] == "manual_only"
    assert normalized["match_score"] >= 70
    assert any("title matches target role" in reason for reason in normalized["match_reasons"])
    assert normalized["risk_flags"] == []


def test_score_and_save_manual_job_inserts_scored_record(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_sample_company()])

    saved = score_and_save_manual_job(
        connection,
        {
            "company_name": "Example Co",
            "title": "Junior DevOps Engineer",
            "location": "Hybrid - Toronto, Ontario, Canada",
            "job_url": "https://indeed.example/jobs/2",
            "apply_url": "https://indeed.example/jobs/2/apply",
            "source_name": "Indeed",
            "source_mode": "manual_only",
            "description": (
                "Linux, Docker, Terraform, Jenkins, GitHub Actions, support, "
                "troubleshooting, and networking."
            ),
            "status": "new",
        },
    )

    assert saved["company_name"] == "Example Co"
    assert saved["source_name"] == "Indeed"
    assert saved["source_mode"] == "manual_only"
    assert saved["status"] == "new"
    assert saved["match_score"] > 0
    assert isinstance(saved["match_reasons"], list)
    assert isinstance(saved["risk_flags"], list)
