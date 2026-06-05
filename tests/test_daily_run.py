from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from reports.daily_run import run_daily_workflow
from storage.db import get_companies, get_jobs, initialize_database


def _write_companies_yaml(path: Path) -> None:
    payload = {
        "companies": [
            {
                "name": "Browser Co",
                "sector": "IT Consulting & Systems Integrators",
                "category": "Consulting/SI",
                "careers_url": "https://careers.browser.example.com",
                "website_category": "company-careers",
                "ats_hint": "",
                "canada_hubs_notes": "Toronto",
                "role_families": ["Cloud", "DevOps"],
                "keywords": ["cloud", "terraform"],
                "priority": "High",
                "monitoring_hint": "Manual check",
                "status": "Watching",
                "source_mode": "browser_allowed",
            },
            {
                "name": "API Co",
                "sector": "IT Consulting & Systems Integrators",
                "category": "Consulting/SI",
                "careers_url": "https://jobs.api.example.com",
                "website_category": "greenhouse",
                "ats_hint": "greenhouse",
                "canada_hubs_notes": "Toronto",
                "role_families": ["Cloud"],
                "keywords": ["aws", "python"],
                "priority": "High",
                "monitoring_hint": "Manual check",
                "status": "Watching",
                "source_mode": "api_allowed",
            },
            {
                "name": "Human Co",
                "sector": "Banking & Capital Markets",
                "category": "Bank/Market",
                "careers_url": "https://workday.human.example.com",
                "website_category": "workday",
                "ats_hint": "workday",
                "canada_hubs_notes": "Canada",
                "role_families": ["Platform"],
                "keywords": ["devops", "linux"],
                "priority": "Medium",
                "monitoring_hint": "Manual check",
                "status": "Watching",
                "source_mode": "human_in_loop",
            },
            {
                "name": "Missing URL Co",
                "sector": "Banking & Capital Markets",
                "category": "Bank/Market",
                "careers_url": None,
                "website_category": "jobs.",
                "ats_hint": "jobs",
                "canada_hubs_notes": "Canada",
                "role_families": ["Cloud"],
                "keywords": ["cloud"],
                "priority": "High",
                "monitoring_hint": "Manual check",
                "status": "Watching",
                "source_mode": "needs_url",
            },
            {
                "name": "Avoid Co",
                "sector": "Banking & Capital Markets",
                "category": "Bank/Market",
                "careers_url": "https://careers.avoid.example.com",
                "website_category": "company-careers",
                "ats_hint": "",
                "canada_hubs_notes": "Canada",
                "role_families": ["Cloud"],
                "keywords": ["cloud"],
                "priority": "Low",
                "monitoring_hint": "Manual check",
                "status": "Watching",
                "source_mode": "avoid",
            },
        ]
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_daily_run_uses_sample_collectors_and_creates_exports(tmp_path: Path) -> None:
    config_path = tmp_path / "companies.yaml"
    db_path = tmp_path / "job_discovery.db"
    exports_dir = tmp_path / "exports"
    _write_companies_yaml(config_path)

    def sample_collector(
        _connection,
        companies: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        company = companies[0]
        company_job_url = f"https://{company['name'].lower().replace(' ', '')}.example.com/jobs/1"
        if company["name"] == "Human Co":
            return [
                {
                    "company_name": "Human Co",
                    "source_name": "workday",
                    "status": "completed",
                    "jobs_seen": 1,
                    "jobs_new": 0,
                    "jobs": [
                        {
                            "company_name": "Human Co",
                            "title": "Junior DevOps Engineer",
                            "location": "Remote Canada",
                            "job_url": "https://workday.human.example.com/jobs/1",
                            "description": "Linux, CI/CD, support, troubleshooting.",
                            "source_name": "workday",
                            "source_mode": "human_in_loop",
                        }
                    ],
                }
            ]
        return [
            {
                "company_name": str(company["name"]),
                "source_name": str(company.get("website_category") or company["name"]),
                "status": "completed",
                "jobs_seen": 2,
                "jobs_new": 0,
                "jobs": [
                    {
                        "company_name": str(company["name"]),
                        "title": "Cloud Engineer",
                        "location": "Toronto, Ontario, Canada",
                        "job_url": company_job_url,
                        "description": "AWS Kubernetes Terraform Python support role.",
                        "source_name": str(company.get("website_category") or company["name"]),
                        "source_mode": str(company["source_mode"]),
                    },
                    {
                        "company_name": str(company["name"]),
                        "title": "Cloud Engineer",
                        "location": "Toronto, Ontario, Canada",
                        "job_url": company_job_url,
                        "description": "Duplicate job listing that should be deduped.",
                        "source_name": str(company.get("website_category") or company["name"]),
                        "source_mode": str(company["source_mode"]),
                    },
                ],
            }
        ]

    collectors = {
        "api_allowed": sample_collector,
        "browser_allowed": sample_collector,
        "human_in_loop": sample_collector,
    }

    result = run_daily_workflow(
        config_path=config_path,
        db_path=db_path,
        exports_dir=exports_dir,
        run_date=date(2026, 6, 2),
        collectors=collectors,
    )

    assert result.run_date == "2026-06-02"
    assert set(result.companies_checked) == {"Browser Co", "API Co", "Human Co"}
    assert {item["company_name"] for item in result.companies_skipped} == {
        "Missing URL Co",
        "Avoid Co",
    }
    assert result.jobs_discovered == 5
    assert result.jobs_scored == 3
    assert result.jobs_relevant == 3
    assert result.jobs_inserted == 3
    assert result.jobs_updated == 0
    assert result.jobs_unchanged == 0
    assert result.duplicates_skipped == 2
    assert len(result.jobs_saved) == 3
    assert result.keyword_scope_used is False
    assert result.artifacts.report_path.exists()
    assert result.artifacts.csv_path.exists()

    report_text = result.artifacts.report_path.read_text(encoding="utf-8")
    assert "Run Summary" in report_text
    assert "Jobs discovered before scoring: 5" in report_text
    assert "Jobs scored: 3" in report_text
    assert "Jobs relevant: 3" in report_text
    assert "Jobs inserted: 3" in report_text
    assert "Jobs updated: 0" in report_text
    assert "Jobs unchanged: 0" in report_text
    assert "Duplicates skipped before scoring: 2" in report_text
    assert "Keyword scope used: False" in report_text
    assert "Top Matched Jobs" in report_text
    assert "Companies Skipped" in report_text

    csv_text = result.artifacts.csv_path.read_text(encoding="utf-8")
    assert "external_job_id,ats_type,board_slug,content_hash" in csv_text

    connection = initialize_database(db_path)
    companies = {company["name"]: company for company in get_companies(connection)}
    assert companies["API Co"]["source_mode"] == "api_allowed"
    assert companies["Human Co"]["source_mode"] == "human_in_loop"
    assert companies["Missing URL Co"]["source_mode"] == "needs_url"


def test_daily_run_preserves_api_and_static_metadata_in_storage(tmp_path: Path) -> None:
    config_path = tmp_path / "companies.yaml"
    db_path = tmp_path / "job_discovery.db"
    exports_dir = tmp_path / "exports"
    _write_companies_yaml(config_path)

    def sample_collector(
        _connection,
        companies: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        company = companies[0]
        if company["name"] == "API Co":
            return [
                {
                    "company_name": "API Co",
                    "source_name": "ashby",
                    "status": "completed",
                    "jobs": [
                        {
                            "company_name": "API Co",
                            "title": "Cloud Engineer",
                            "location": "Toronto, Ontario, Canada",
                            "job_url": "https://jobs.ashbyhq.com/example/job-12345",
                            "apply_url": "https://jobs.ashbyhq.com/example/job-12345/apply",
                            "description": "AWS Terraform Linux support role.",
                            "source_name": "ashby",
                            "source_mode": "api_allowed",
                            "external_job_id": "job-12345",
                            "ats_type": "ashby",
                            "board_slug": "example",
                            "raw_payload_json": '{"id":"job-12345"}',
                        }
                    ],
                }
            ]
        if company["name"] == "Browser Co":
            return [
                {
                    "company_name": "Browser Co",
                    "source_name": "company-careers",
                    "status": "completed",
                    "jobs": [
                        {
                            "company_name": "Browser Co",
                            "title": "Cloud Support Engineer",
                            "location": "Remote Canada",
                            "job_url": "https://careers.browser.example.com/jobs/1",
                            "apply_url": "https://careers.browser.example.com/jobs/1",
                            "description": "Linux troubleshooting support role.",
                            "source_name": "company-careers",
                            "source_mode": "browser_allowed",
                            "external_job_id": "browser-jsonld-1",
                            "ats_type": "jsonld",
                            "board_slug": "careers.browser.example.com",
                            "raw_payload_json": (
                                '{"@type":"JobPosting",'
                                '"identifier":{"value":"browser-jsonld-1"}}'
                            ),
                        }
                    ],
                }
            ]
        return [
            {
                "company_name": "Human Co",
                "source_name": "lever",
                "status": "completed",
                "jobs": [
                    {
                        "company_name": "Human Co",
                        "title": "Junior DevOps Engineer",
                        "location": "Remote Canada",
                        "job_url": "https://jobs.lever.co/human/abc123",
                        "apply_url": "https://jobs.lever.co/human/abc123/apply",
                        "description": "Linux CI/CD support role.",
                        "source_name": "lever",
                        "source_mode": "api_allowed",
                        "external_job_id": "abc123",
                        "ats_type": "lever",
                        "board_slug": "human",
                        "raw_payload_json": '{"id":"abc123"}',
                    }
                ],
            }
        ]

    collectors = {
        "api_allowed": sample_collector,
        "browser_allowed": sample_collector,
        "human_in_loop": sample_collector,
    }

    run_daily_workflow(
        config_path=config_path,
        db_path=db_path,
        exports_dir=exports_dir,
        run_date=date(2026, 6, 3),
        collectors=collectors,
    )

    connection = initialize_database(db_path)
    jobs = {job["company_name"]: job for job in get_jobs(connection)}

    assert jobs["API Co"]["external_job_id"] == "job-12345"
    assert jobs["API Co"]["ats_type"] == "ashby"
    assert jobs["API Co"]["board_slug"] == "example"
    assert jobs["API Co"]["raw_payload_json"] == '{"id":"job-12345"}'
    assert jobs["Browser Co"]["external_job_id"] == "browser-jsonld-1"
    assert jobs["Browser Co"]["ats_type"] == "jsonld"
    assert jobs["Browser Co"]["board_slug"] == "careers.browser.example.com"
    assert jobs["Human Co"]["external_job_id"] == "abc123"
    assert jobs["Human Co"]["ats_type"] == "lever"
    assert jobs["Human Co"]["board_slug"] == "human"


def test_repeated_daily_run_does_not_duplicate_api_jobs(tmp_path: Path) -> None:
    config_path = tmp_path / "companies.yaml"
    db_path = tmp_path / "job_discovery.db"
    exports_dir = tmp_path / "exports"
    _write_companies_yaml(config_path)

    def sample_collector(
        _connection,
        companies: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        company = companies[0]
        return [
            {
                "company_name": str(company["name"]),
                "source_name": str(company.get("website_category") or company["name"]),
                "status": "completed",
                "jobs": [
                    {
                        "company_name": str(company["name"]),
                        "title": "Cloud Engineer",
                        "location": "Toronto, Ontario, Canada",
                        "job_url": (
                            "https://jobs.example.com/"
                            f"{company['name'].lower().replace(' ', '-')}/1"
                        ),
                        "description": "AWS Kubernetes Terraform Python support role.",
                        "source_name": str(company.get("website_category") or company["name"]),
                        "source_mode": str(company["source_mode"]),
                        "external_job_id": "12345" if company["name"] == "API Co" else None,
                        "ats_type": "greenhouse" if company["name"] == "API Co" else None,
                        "board_slug": "example" if company["name"] == "API Co" else None,
                    }
                ],
            }
        ]

    collectors = {
        "api_allowed": sample_collector,
        "browser_allowed": sample_collector,
        "human_in_loop": sample_collector,
    }

    first_run = run_daily_workflow(
        config_path=config_path,
        db_path=db_path,
        exports_dir=exports_dir,
        run_date=date(2026, 6, 3),
        collectors=collectors,
    )
    second_run = run_daily_workflow(
        config_path=config_path,
        db_path=db_path,
        exports_dir=exports_dir,
        run_date=date(2026, 6, 4),
        collectors=collectors,
    )

    connection = initialize_database(db_path)
    jobs = get_jobs(connection)

    assert first_run.jobs_inserted == 3
    assert second_run.jobs_inserted == 0
    assert second_run.jobs_unchanged == 3
    assert len(jobs) == 3
