from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from reports.daily_run import (
    _apply_canada_location_safety_gate,
    is_actionable_job,
    run_daily_workflow,
)
from storage.db import (
    get_companies,
    get_jobs,
    get_source_status_rows,
    initialize_database,
    upsert_companies,
    upsert_job_record,
)


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
                    "location_scope_used": True,
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
    assert result.active_saved_jobs == 0
    assert result.review_export_rows == 0
    assert result.duplicates_skipped == 2
    assert len(result.jobs_saved) == 3
    assert result.location_scope_used is True
    assert result.keyword_scope_used is False
    assert result.artifacts.report_path.exists()
    assert result.artifacts.csv_path.exists()

    report_text = result.artifacts.report_path.read_text(encoding="utf-8")
    assert "Run Summary" in report_text
    assert "Jobs discovered before scoring: 5" in report_text
    assert "Jobs scored: 3" in report_text
    assert "Jobs relevant in current run: 3" in report_text
    assert "Jobs new: 3" in report_text
    assert "Jobs updated: 0" in report_text
    assert "Jobs unchanged: 0" in report_text
    assert "Active saved jobs: 0" in report_text
    assert "Review export rows: 0" in report_text
    assert "Duplicates skipped before scoring: 2" in report_text
    assert "## Collection" in report_text
    assert "## Evaluation" in report_text
    assert "## Storage And Dedupe" in report_text
    assert "## Routing Summary" in report_text
    assert "## Source Outcomes" in report_text
    assert "## Active Pending Interventions" in report_text
    assert "## Resolved Intervention History" in report_text
    assert "## Suspicious Saved Rows" in report_text
    assert "| Browser Co | company-careers | browser_allowed | - |" in report_text
    assert "| API Co | greenhouse | api_allowed | - |" in report_text
    assert "Location scope used: True" in report_text
    assert "Keyword scope used: False" in report_text
    assert "Top Matched Jobs" in report_text
    assert "Companies Skipped" in report_text
    assert result.suspicious_saved_rows == []

    csv_text = result.artifacts.csv_path.read_text(encoding="utf-8")
    assert "external_job_id,ats_type,board_slug,content_hash" in csv_text

    connection = initialize_database(db_path)
    companies = {company["name"]: company for company in get_companies(connection)}
    source_rows = {row["company_name"]: row for row in get_source_status_rows(connection)}
    assert companies["API Co"]["source_mode"] == "api_allowed"
    assert companies["Human Co"]["source_mode"] == "human_in_loop"
    assert companies["Missing URL Co"]["source_mode"] == "needs_url"
    assert source_rows["API Co"]["status"] == "completed"
    assert source_rows["API Co"]["jobs_discovered"] == 2
    assert source_rows["API Co"]["jobs_inserted"] == 1
    assert source_rows["Missing URL Co"]["status"] == "needs_url"
    assert source_rows["Missing URL Co"]["readiness_label"] == "needs_url"


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


def test_daily_run_company_filter_limits_checked_sources(tmp_path: Path) -> None:
    config_path = tmp_path / "companies.yaml"
    db_path = tmp_path / "job_discovery.db"
    exports_dir = tmp_path / "exports"
    _write_companies_yaml(config_path)
    seen_companies: list[str] = []

    def sample_collector(
        _connection,
        companies: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        company = companies[0]
        seen_companies.append(str(company["name"]))
        return [
            {
                "company_name": str(company["name"]),
                "source_name": str(company.get("website_category") or company["name"]),
                "status": "completed",
                "jobs": [],
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
        run_date=date(2026, 6, 3),
        collectors=collectors,
        company_names=["Browser Co"],
    )

    assert seen_companies == ["Browser Co"]
    assert result.companies_checked == ["Browser Co"]
    assert result.jobs_discovered == 0
    assert result.companies_skipped == []

    connection = initialize_database(db_path)
    companies = {company["name"]: company for company in get_companies(connection)}
    assert set(companies) == {"Browser Co"}


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


def test_daily_run_surfaces_manual_only_and_api_not_implemented_sources(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "companies.yaml"
    db_path = tmp_path / "job_discovery.db"
    exports_dir = tmp_path / "exports"
    payload = {
        "companies": [
            {
                "name": "Manual Co",
                "sector": "IT Consulting & Systems Integrators",
                "category": "Consulting/SI",
                "careers_url": "https://www.linkedin.com/jobs/view/example",
                "website_category": "LinkedIn",
                "ats_hint": "",
                "canada_hubs_notes": "Toronto",
                "role_families": ["Cloud"],
                "keywords": ["cloud"],
                "priority": "High",
                "monitoring_hint": "Manual check",
                "status": "Watching",
                "source_mode": "manual_only",
            },
            {
                "name": "API NI Co",
                "sector": "IT Consulting & Systems Integrators",
                "category": "Consulting/SI",
                "careers_url": "https://jobs.smartrecruiters.com/Example/example",
                "website_category": "smartrecruiters",
                "ats_hint": "smartrecruiters",
                "canada_hubs_notes": "Toronto",
                "role_families": ["Cloud"],
                "keywords": ["cloud"],
                "priority": "High",
                "monitoring_hint": "Manual check",
                "status": "Watching",
                "source_mode": "api_allowed",
            },
        ]
    }
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    result = run_daily_workflow(
        config_path=config_path,
        db_path=db_path,
        exports_dir=exports_dir,
        run_date=date(2026, 6, 5),
    )

    report_text = result.artifacts.report_path.read_text(encoding="utf-8")
    connection = initialize_database(db_path)
    source_rows = {
        row["company_name"]: row for row in get_source_status_rows(connection)
    }

    assert result.jobs_discovered == 0
    assert "manual_only" in report_text
    assert "api_collector_not_implemented" in report_text
    assert result.errors == []
    assert source_rows["Manual Co"]["status"] == "manual_only"
    assert source_rows["Manual Co"]["readiness_label"] == "manual_only"
    assert source_rows["API NI Co"]["status"] == "api_collector_not_implemented"
    assert source_rows["API NI Co"]["readiness_label"] == "api_not_implemented"


def test_is_actionable_job_rejects_url_less_browser_rows_but_keeps_external_identity() -> None:
    assert is_actionable_job(
        {
            "company_name": "Accenture",
            "title": "Technical Support Coordinator",
            "location": "Toronto",
            "job_url": None,
            "description": "Technical Support Coordinator Toronto Full-time",
            "source_mode": "browser_allowed",
        }
    ) is False
    assert is_actionable_job(
        {
            "company_name": "API Co",
            "title": "Cloud Engineer",
            "location": "Remote Canada",
            "job_url": None,
            "description": "Remote job",
            "source_mode": "api_allowed",
            "external_job_id": "12345",
            "ats_type": "greenhouse",
            "board_slug": "example",
        }
    ) is True


def test_daily_run_prefers_non_empty_yaml_careers_url_over_stale_db_value(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "companies.yaml"
    db_path = tmp_path / "job_discovery.db"
    exports_dir = tmp_path / "exports"
    _write_companies_yaml(config_path)

    connection = initialize_database(db_path)
    upsert_companies(
        connection,
        [
            {
                "name": "Browser Co",
                "sector": "IT Consulting & Systems Integrators",
                "category": "Consulting/SI",
                "careers_url": "https://stale.browser.example.com",
                "website_category": "company-careers",
                "ats_hint": "",
                "canada_hubs_notes": "Toronto",
                "role_families": ["Cloud", "DevOps"],
                "keywords": ["cloud", "terraform"],
                "priority": "High",
                "monitoring_hint": "Manual check",
                "status": "Watching",
                "source_mode": "browser_allowed",
            }
        ],
    )

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
                "jobs": [],
            }
        ]

    run_daily_workflow(
        config_path=config_path,
        db_path=db_path,
        exports_dir=exports_dir,
        run_date=date(2026, 6, 5),
        collectors={
            "api_allowed": sample_collector,
            "browser_allowed": sample_collector,
            "human_in_loop": sample_collector,
        },
    )

    refreshed = initialize_database(db_path)
    companies = {company["name"]: company for company in get_companies(refreshed)}

    assert companies["Browser Co"]["careers_url"] == "https://careers.browser.example.com"


def test_daily_run_rejects_existing_non_actionable_new_jobs(tmp_path: Path) -> None:
    config_path = tmp_path / "companies.yaml"
    db_path = tmp_path / "job_discovery.db"
    exports_dir = tmp_path / "exports"
    _write_companies_yaml(config_path)

    connection = initialize_database(db_path)
    upsert_companies(
        connection,
        [
            {
                "name": "Scotiabank",
                "sector": "Banking & Capital Markets",
                "category": "Bank/Market",
                "careers_url": "https://www.scotiabank.com/careers/en/careers.html",
                "website_category": "jobs.",
                "ats_hint": "",
                "canada_hubs_notes": "Canada",
                "role_families": ["Cloud"],
                "keywords": ["cloud"],
                "priority": "High",
                "monitoring_hint": "Manual check",
                "status": "Watching",
                "source_mode": "browser_allowed",
            }
        ],
    )
    upsert_job_record(
        connection,
        {
            "company_name": "Scotiabank",
            "title": "Helping drive equality for every future",
            "location": "Canada",
            "job_url": "https://www.womenofinfluence.ca/2026/04/27/katy-waugh",
            "apply_url": None,
            "source_name": "jobs.",
            "source_mode": "browser_allowed",
            "description": "Inclusion fuels innovation and drives better outcomes.",
            "date_posted": None,
            "match_score": 16,
            "match_reasons": ["support/ops signals: support"],
            "risk_flags": [],
            "status": "new",
        },
    )

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
                "jobs": [],
            }
        ]

    run_daily_workflow(
        config_path=config_path,
        db_path=db_path,
        exports_dir=exports_dir,
        run_date=date(2026, 6, 5),
        collectors={
            "api_allowed": sample_collector,
            "browser_allowed": sample_collector,
            "human_in_loop": sample_collector,
        },
    )

    refreshed = initialize_database(db_path)
    stored_jobs = [
        job
        for job in get_jobs(refreshed)
        if job["title"] == "Helping drive equality for every future"
    ]

    assert len(stored_jobs) == 1
    assert stored_jobs[0]["status"] == "rejected"


def test_canada_location_safety_gate_rejects_explicit_us_rows() -> None:
    source_key = ("BMO", "company-careers")
    rejected_job = {
        "company_name": "BMO",
        "source_name": "company-careers",
        "title": "Cloud Engineer",
        "location": "San Ramon, CA",
        "risk_flags": [],
        "_source_key": source_key,
    }
    filtered_jobs, rejected_by_source, unknown_by_source = _apply_canada_location_safety_gate(
        [
            rejected_job,
            {
                "company_name": "BMO",
                "source_name": "company-careers",
                "title": "Platform Engineer",
                "location": "Toronto, Ontario, Canada",
                "_source_key": source_key,
            },
            {
                "company_name": "BMO",
                "source_name": "company-careers",
                "title": "Linux Administrator",
                "location": "",
                "_source_key": source_key,
            },
        ],
        {source_key: {"source_scope_status": "canada_scope_confirmed"}},
    )

    assert [job["title"] for job in filtered_jobs] == [
        "Platform Engineer",
        "Linux Administrator",
    ]
    assert rejected_by_source[source_key] == 1
    assert unknown_by_source[source_key] == 1
    assert rejected_job["risk_flags"] == ["outside_location_scope", "non_canada_location"]


def test_canada_location_safety_gate_keeps_successfactors_canadian_country_code() -> None:
    source_key = ("Scotiabank", "jobs.")
    filtered_jobs, rejected_by_source, unknown_by_source = _apply_canada_location_safety_gate(
        [
            {
                "company_name": "Scotiabank",
                "source_name": "jobs.",
                "title": "Cloud Platform Engineer",
                "location": "Toronto, ON, CA, M5H 1H1",
                "_source_key": source_key,
            },
            {
                "company_name": "Scotiabank",
                "source_name": "jobs.",
                "title": "Cloud Engineer",
                "location": "San Ramon, CA",
                "_source_key": source_key,
            },
        ],
        {source_key: {"source_scope_status": "canada_scope_confirmed"}},
    )

    assert [job["title"] for job in filtered_jobs] == ["Cloud Platform Engineer"]
    assert rejected_by_source[source_key] == 1
    assert unknown_by_source[source_key] == 0


def test_canada_location_safety_gate_rejects_bmo_enus_urls_even_without_location() -> None:
    source_key = ("BMO", "company-careers")
    rejected_job = {
        "company_name": "BMO",
        "source_name": "company-careers",
        "title": "Bank Manager",
        "location": "",
        "job_url": "https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260012209EXTERNALENUS/Bank-Manager",
        "risk_flags": [],
        "_source_key": source_key,
    }
    filtered_jobs, rejected_by_source, unknown_by_source = _apply_canada_location_safety_gate(
        [
            rejected_job,
            {
                "company_name": "BMO",
                "source_name": "company-careers",
                "title": "Software Developer",
                "location": "",
                "job_url": "https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260000290EXTERNALENCA/Software-Developer",
                "_source_key": source_key,
            },
        ],
        {source_key: {"source_scope_status": "canada_scope_confirmed"}},
    )

    assert [job["title"] for job in filtered_jobs] == ["Software Developer"]
    assert rejected_by_source[source_key] == 1
    assert unknown_by_source[source_key] == 1
    assert rejected_job["risk_flags"] == ["outside_location_scope", "non_canada_location"]
