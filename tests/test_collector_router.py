from __future__ import annotations

from pathlib import Path

import collectors.router as router_module
from collectors.router import collect_company_jobs_routed, load_api_browser_fallback_flag
from storage.db import initialize_database, upsert_companies


def _company(**overrides: object) -> dict[str, object]:
    company = {
        "name": "Example Co",
        "sector": "IT Consulting & Systems Integrators",
        "category": "Consulting/SI",
        "careers_url": "https://careers.example.com",
        "website_category": "company-careers",
        "ats_hint": "",
        "canada_hubs_notes": "Toronto",
        "role_families": ["Cloud"],
        "keywords": ["cloud"],
        "priority": "High",
        "monitoring_hint": "Manual check",
        "status": "Watching",
        "source_mode": "browser_allowed",
    }
    company.update(overrides)
    return company


def test_load_api_browser_fallback_flag_defaults_false(tmp_path: Path) -> None:
    config_path = tmp_path / "discovery.yaml"
    config_path.write_text("routing:\n  api_fallback_to_browser: false\n", encoding="utf-8")

    assert load_api_browser_fallback_flag(config_path) is False


def test_manual_only_source_does_not_call_browser_collector(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(connection, [_company(source_mode="manual_only")])

    def fail_browser(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("browser collector should not be called")

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fail_browser)

    result = collect_company_jobs_routed(connection, _company(source_mode="manual_only"))

    assert result.status == "manual_only"
    assert result.collector == "manual_only"
    assert result.intervention_required is True


def test_restricted_linkedin_source_does_not_call_browser_collector(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    def fail_browser(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("browser collector should not be called")

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fail_browser)

    result = collect_company_jobs_routed(
        connection,
        _company(
            source_mode="browser_allowed",
            source_name="LinkedIn",
            website_category="LinkedIn",
            careers_url="https://www.linkedin.com/jobs/view/example",
        ),
    )

    assert result.status == "manual_only"
    assert result.collector == "manual_only"


def test_restricted_indeed_source_does_not_call_browser_collector(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    def fail_browser(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("browser collector should not be called")

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fail_browser)

    result = collect_company_jobs_routed(
        connection,
        _company(careers_url="https://www.indeed.com/viewjob?jk=123"),
    )

    assert result.status == "manual_only"
    assert result.collector == "manual_only"


def test_restricted_glassdoor_source_does_not_call_browser_collector(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    def fail_browser(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("browser collector should not be called")

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fail_browser)

    result = collect_company_jobs_routed(
        connection,
        _company(careers_url="https://www.glassdoor.com/job-listing/example"),
    )

    assert result.status == "manual_only"
    assert result.collector == "manual_only"


def test_missing_url_returns_needs_url_and_does_not_call_browser_collector(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    def fail_browser(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("browser collector should not be called")

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fail_browser)

    result = collect_company_jobs_routed(connection, _company(careers_url=None))

    assert result.status == "needs_url"
    assert result.collector == "needs_url"


def test_unknown_public_source_routes_to_browser_collector(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    def fake_browser(*args, **kwargs):  # noqa: ARG001
        return [
            {
                "company_name": "Example Co",
                "source_name": "company-careers",
                "status": "completed",
                "jobs_discovered": 1,
                "jobs_scored": 0,
                "jobs_relevant": 0,
                "jobs_saved": 0,
                "jobs": [],
            }
        ]

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fake_browser)

    result = collect_company_jobs_routed(connection, _company())

    assert result.status == "completed"
    assert result.collector == "browser"
    assert result.source_mode == "browser_allowed"


def test_browser_allowed_routes_to_browser_collector(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    def fake_browser(*args, **kwargs):  # noqa: ARG001
        return [
            {
                "company_name": "Example Co",
                "source_name": "company-careers",
                "status": "completed",
                "jobs_discovered": 2,
                "jobs_scored": 1,
                "jobs_relevant": 1,
                "jobs_saved": 1,
                "jobs": [],
            }
        ]

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fake_browser)

    result = collect_company_jobs_routed(
        connection,
        _company(source_mode="browser_allowed"),
        save_jobs=True,
    )

    assert result.collector == "browser"
    assert result.jobs_discovered == 2
    assert result.jobs_saved == 1


def test_human_in_loop_routes_to_browser_collector(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    def fake_browser(*args, **kwargs):  # noqa: ARG001
        return [
            {
                "company_name": "Example Co",
                "source_name": "workday",
                "status": "paused",
                "jobs_discovered": 0,
                "jobs_scored": 0,
                "jobs_relevant": 0,
                "jobs_saved": 0,
                "jobs": [],
            }
        ]

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fake_browser)

    result = collect_company_jobs_routed(
        connection,
        _company(
            source_mode="human_in_loop",
            ats_hint="workday",
            website_category="workday",
            careers_url="https://example.myworkdayjobs.com/en-US/careers",
        ),
    )

    assert result.collector == "browser"
    assert result.source_mode == "human_in_loop"
    assert result.intervention_required is True


def test_api_allowed_greenhouse_returns_not_implemented_when_fallback_disabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    def fail_browser(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("browser collector should not be called")

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fail_browser)
    monkeypatch.setattr(
        router_module,
        "collect_greenhouse_jobs",
        lambda company: router_module.CollectorResult(  # noqa: ARG005
            company_name="Example Co",
            source_name="greenhouse",
            status="success",
            collector="greenhouse_api",
            ats_type="greenhouse",
            source_mode="api_allowed",
            jobs_discovered=1,
            jobs=[{"title": "Cloud Engineer"}],
        ),
    )

    result = collect_company_jobs_routed(
        connection,
        _company(
            source_mode="api_allowed",
            ats_hint="greenhouse",
            website_category="greenhouse",
            careers_url="https://boards.greenhouse.io/example",
        ),
        allow_api_browser_fallback=False,
    )

    assert result.status == "success"
    assert result.collector == "greenhouse_api"
    assert result.jobs_discovered == 1
    assert result.fallback_used is False


def test_api_allowed_lever_calls_api_collector_when_fallback_disabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    def fail_browser(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("browser collector should not be called")

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fail_browser)
    monkeypatch.setattr(
        router_module,
        "collect_lever_jobs",
        lambda company: router_module.CollectorResult(  # noqa: ARG005
            company_name="Example Co",
            source_name="lever",
            status="success",
            collector="lever_api",
            ats_type="lever",
            source_mode="api_allowed",
            jobs_discovered=2,
            jobs=[{"title": "DevOps Engineer"}, {"title": "Support Engineer"}],
        ),
    )

    result = collect_company_jobs_routed(
        connection,
        _company(
            source_mode="api_allowed",
            ats_hint="lever",
            website_category="lever",
            careers_url="https://jobs.lever.co/example",
        ),
        allow_api_browser_fallback=False,
    )

    assert result.status == "success"
    assert result.collector == "lever_api"
    assert result.jobs_discovered == 2


def test_api_allowed_ashby_returns_not_implemented_when_fallback_disabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    def fail_browser(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("browser collector should not be called")

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fail_browser)

    result = collect_company_jobs_routed(
        connection,
        _company(
            source_mode="api_allowed",
            ats_hint="ashby",
            website_category="ashby",
            careers_url="https://jobs.ashbyhq.com/example",
        ),
        allow_api_browser_fallback=False,
    )

    assert result.status == "api_collector_not_implemented"
    assert result.collector == "api_not_implemented"


def test_api_allowed_smartrecruiters_returns_not_implemented_when_fallback_disabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    def fail_browser(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("browser collector should not be called")

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fail_browser)

    result = collect_company_jobs_routed(
        connection,
        _company(
            source_mode="api_allowed",
            ats_hint="smartrecruiters",
            website_category="smartrecruiters",
            careers_url="https://jobs.smartrecruiters.com/Example/example",
        ),
        allow_api_browser_fallback=False,
    )

    assert result.status == "api_collector_not_implemented"
    assert result.collector == "api_not_implemented"


def test_api_failure_does_not_silently_browser_fallback_when_disabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    def fail_browser(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("browser collector should not be called")

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fail_browser)
    monkeypatch.setattr(
        router_module,
        "collect_greenhouse_jobs",
        lambda company: router_module.CollectorResult(  # noqa: ARG005
            company_name="Example Co",
            source_name="greenhouse",
            status="api_error",
            collector="greenhouse_api",
            ats_type="greenhouse",
            source_mode="api_allowed",
            error="API unavailable",
        ),
    )

    result = collect_company_jobs_routed(
        connection,
        _company(
            source_mode="api_allowed",
            ats_hint="greenhouse",
            website_category="greenhouse",
            careers_url="https://boards.greenhouse.io/example",
        ),
        allow_api_browser_fallback=False,
    )

    assert result.status == "api_error"
    assert result.collector == "greenhouse_api"
    assert result.fallback_used is False


def test_api_allowed_greenhouse_can_use_browser_fallback_when_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    def fake_browser(*args, **kwargs):  # noqa: ARG001
        return [
            {
                "company_name": "Example Co",
                "source_name": "greenhouse",
                "status": "completed",
                "jobs_discovered": 3,
                "jobs_scored": 0,
                "jobs_relevant": 0,
                "jobs_saved": 0,
                "jobs": [],
            }
        ]

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fake_browser)
    monkeypatch.setattr(
        router_module,
        "collect_greenhouse_jobs",
        lambda company: router_module.CollectorResult(  # noqa: ARG005
            company_name="Example Co",
            source_name="greenhouse",
            status="api_error",
            collector="greenhouse_api",
            ats_type="greenhouse",
            source_mode="api_allowed",
            error="API unavailable",
        ),
    )

    result = collect_company_jobs_routed(
        connection,
        _company(
            source_mode="api_allowed",
            ats_hint="greenhouse",
            website_category="greenhouse",
            careers_url="https://boards.greenhouse.io/example",
        ),
        allow_api_browser_fallback=True,
    )

    assert result.collector == "browser_fallback"
    assert result.fallback_used is True
    assert result.jobs_discovered == 3


def test_router_result_includes_core_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")

    def fake_browser(*args, **kwargs):  # noqa: ARG001
        return [
            {
                "company_name": "Example Co",
                "source_name": "company-careers",
                "status": "completed",
                "jobs_discovered": 1,
                "jobs_scored": 1,
                "jobs_relevant": 1,
                "jobs_saved": 1,
                "jobs": [],
            }
        ]

    monkeypatch.setattr(router_module, "collect_companies_with_browser", fake_browser)

    result = collect_company_jobs_routed(connection, _company(), save_jobs=True)
    payload = result.to_dict()

    assert payload["collector"] == "browser"
    assert payload["source_mode"] == "browser_allowed"
    assert payload["ats_type"] is None
    assert payload["status"] == "completed"
    assert payload["jobs_discovered"] == 1
    assert payload["jobs_saved"] == 1
