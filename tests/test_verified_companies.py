from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import yaml

import main as cli_main
from dashboard.verified_view import (
    filter_jobs_to_latest_verified_run,
    filter_jobs_to_verified_companies,
)
from reports.daily_run import run_daily_workflow
from verified_companies import (
    get_usable_verified_company_names,
    load_verified_company_records,
)


def _write_companies_yaml(path: Path) -> None:
    payload = {
        "companies": [
            {
                "name": "Verified Co",
                "sector": "IT Consulting & Systems Integrators",
                "category": "Consulting/SI",
                "careers_url": "https://verified.example.com/careers",
                "website_category": "company-careers",
                "priority": "High",
                "status": "Watching",
                "source_mode": "browser_allowed",
            },
            {
                "name": "Needs Review Co",
                "sector": "Insurance & Wealth",
                "category": "Insurance/Wealth",
                "careers_url": "https://review.example.com/careers",
                "website_category": "workday",
                "ats_hint": "workday",
                "priority": "High",
                "status": "Watching",
                "source_mode": "human_in_loop",
            },
            {
                "name": "Unverified Co",
                "sector": "IT Consulting & Systems Integrators",
                "category": "Consulting/SI",
                "careers_url": "https://other.example.com/careers",
                "website_category": "company-careers",
                "priority": "Medium",
                "status": "Watching",
                "source_mode": "browser_allowed",
            },
        ]
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_verified_yaml(path: Path) -> None:
    payload = {
        "verified_companies": [
            {
                "company_name": "Verified Co",
                "verified": True,
                "verified_at": "2026-06-10",
                "scope": "Canada",
                "status": "usable",
                "notes": "Ready",
            },
            {
                "company_name": "Needs Review Co",
                "verified": False,
                "verified_at": "2026-06-10",
                "scope": "Canada",
                "status": "needs_review",
                "notes": "Waiting on audit",
            },
            {
                "company_name": "Unverified Co",
                "verified": True,
                "verified_at": "2026-06-10",
                "scope": "Canada",
                "status": "needs_review",
                "notes": "Not usable yet",
            },
        ]
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_verified_company_loader_reads_only_usable_records(tmp_path: Path) -> None:
    verified_path = tmp_path / "verified_companies.yaml"
    _write_verified_yaml(verified_path)

    records = load_verified_company_records(verified_path)
    usable_names = get_usable_verified_company_names(verified_path)

    assert len(records) == 3
    assert usable_names == ["Verified Co"]


def test_verified_only_daily_run_selects_only_usable_companies(tmp_path: Path) -> None:
    config_path = tmp_path / "companies.yaml"
    verified_path = tmp_path / "verified_companies.yaml"
    db_path = tmp_path / "job_discovery.db"
    exports_dir = tmp_path / "exports"
    _write_companies_yaml(config_path)
    _write_verified_yaml(verified_path)
    seen_companies: list[str] = []

    def sample_collector(
        _connection,
        companies: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        company = companies[0]
        seen_companies.append(str(company["name"]))
        job_url = (
            f"https://{str(company['name']).lower().replace(' ', '')}"
            ".example/jobs/1"
        )
        return [
            {
                "company_name": str(company["name"]),
                "source_name": str(company.get("website_category") or company["name"]),
                "status": "completed",
                "location_scope_used": True,
                "jobs": [
                    {
                        "company_name": str(company["name"]),
                        "title": "Cloud Engineer",
                        "location": "Canada",
                        "job_url": job_url,
                        "description": "AWS Terraform support role.",
                        "source_name": str(company.get("website_category") or company["name"]),
                        "source_mode": str(company["source_mode"]),
                    }
                ],
            }
        ]

    result = run_daily_workflow(
        config_path=config_path,
        db_path=db_path,
        exports_dir=exports_dir,
        run_date=date(2026, 6, 10),
        collectors={
            "api_allowed": sample_collector,
            "browser_allowed": sample_collector,
            "human_in_loop": sample_collector,
        },
        company_names=get_usable_verified_company_names(verified_path),
        run_scope="verified_only",
    )

    assert seen_companies == ["Verified Co"]
    assert result.run_scope == "verified_only"
    assert result.location_scope_used is True
    assert result.companies_checked == ["Verified Co"]


def test_list_verified_prints_statuses_without_running_collection(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    verified_path = tmp_path / "verified_companies.yaml"
    _write_verified_yaml(verified_path)

    monkeypatch.setattr(cli_main, "VERIFIED_COMPANIES_CONFIG_PATH", verified_path)
    monkeypatch.setattr(
        cli_main,
        "get_reports_api",
        lambda: (_ for _ in ()).throw(AssertionError("run workflow should not load")),
    )

    exit_code = cli_main.main(["daily-run", "--list-verified"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "Verified Co" in captured
    assert "usable" in captured
    assert "Needs Review Co" in captured
    assert "needs_review" in captured


def test_verified_only_cli_passes_usable_company_names(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    verified_path = tmp_path / "verified_companies.yaml"
    _write_verified_yaml(verified_path)
    captured_call: dict[str, object] = {}

    @dataclass
    class FakeArtifacts:
        report_path: Path
        csv_path: Path

    def fake_run_daily_workflow(**kwargs):
        captured_call.update(kwargs)
        return SimpleNamespace(
            run_date="2026-06-10",
            run_scope="verified_only",
            companies_checked=["Verified Co"],
            companies_skipped=[],
            jobs_discovered=1,
            jobs_scored=1,
            jobs_relevant=1,
            jobs_saved=[{"company_name": "Verified Co"}],
            jobs_inserted=1,
            jobs_updated=0,
            jobs_unchanged=0,
            location_scope_used=True,
            keyword_scope_used=False,
            artifacts=FakeArtifacts(
                report_path=tmp_path / "report.md",
                csv_path=tmp_path / "jobs.csv",
            ),
        )

    monkeypatch.setattr(cli_main, "VERIFIED_COMPANIES_CONFIG_PATH", verified_path)
    monkeypatch.setattr(
        cli_main,
        "get_storage_api",
        lambda: {
            "initialize_database": lambda _path: object(),
            "get_dashboard_overview": lambda _connection: {"total_companies": 1},
            "upsert_companies": lambda _connection, _companies: None,
        },
    )
    monkeypatch.setattr(cli_main, "load_companies_config", lambda: [])
    monkeypatch.setattr(
        cli_main,
        "get_reports_api",
        lambda: {"run_daily_workflow": fake_run_daily_workflow},
    )
    monkeypatch.setattr(cli_main, "get_collection_api", lambda: {})
    monkeypatch.setattr(cli_main, "get_onboarding_api", lambda: {})
    monkeypatch.setattr(cli_main, "get_audit_api", lambda: {})

    exit_code = cli_main.main(["daily-run", "--verified-only"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert captured_call["company_names"] == ["Verified Co"]
    assert captured_call["run_scope"] == "verified_only"
    assert "verified_only" in captured


def test_dashboard_verified_helper_filters_jobs() -> None:
    jobs = [
        {"company_name": "Verified Co", "title": "Cloud Engineer"},
        {"company_name": "Other Co", "title": "Support Engineer"},
    ]

    filtered = filter_jobs_to_verified_companies(jobs, {"Verified Co"})

    assert filtered == [{"company_name": "Verified Co", "title": "Cloud Engineer"}]


def test_dashboard_verified_helper_filters_to_latest_verified_run() -> None:
    jobs = [
        {
            "company_name": "Verified Co",
            "title": "Current Canada Job",
            "last_seen_at": "2026-06-11T03:56:29Z",
        },
        {
            "company_name": "Verified Co",
            "title": "Older Historical Job",
            "last_seen_at": "2026-06-05T21:10:53Z",
        },
        {
            "company_name": "Other Co",
            "title": "Other Company Job",
            "last_seen_at": "2026-06-11T03:56:29Z",
        },
    ]
    source_rows = [
        {
            "company_name": "Verified Co",
            "last_checked": "2026-06-11 03:56:29",
        },
        {
            "company_name": "Other Co",
            "last_checked": "2026-06-11 03:56:29",
        },
    ]

    filtered = filter_jobs_to_latest_verified_run(jobs, source_rows, {"Verified Co"})

    assert [job["title"] for job in filtered] == ["Current Canada Job"]
