from __future__ import annotations

from pathlib import Path

from browser.extraction import extract_location
from browser.interventions import (
    BARRIER_SIGNAL_CAPTCHA,
    BARRIER_SIGNAL_COOKIE,
    BARRIER_SIGNAL_LOCATION,
    BARRIER_SIGNAL_LOGIN,
    BARRIER_SIGNAL_UNCLEAR,
    detect_browser_barriers,
)
from collectors.browser_collector import collect_browser_jobs, collect_company_jobs
from storage.db import get_interventions, initialize_database, upsert_companies


def _browser_company(**overrides: object) -> dict[str, object]:
    company = {
        "name": "Example Browser Co",
        "sector": "IT Consulting & Systems Integrators",
        "category": "Consulting/SI",
        "careers_url": "https://careers.example.com",
        "website_category": "company-careers",
        "ats_hint": "",
        "canada_hubs_notes": "Toronto",
        "role_families": ["Cloud", "DevOps"],
        "keywords": ["cloud", "devops", "terraform"],
        "priority": "High",
        "monitoring_hint": "Manual check",
        "status": "Watching",
        "source_mode": "browser_allowed",
    }
    company.update(overrides)
    return company


def test_detect_browser_barriers_finds_expected_signals() -> None:
    signals = detect_browser_barriers(
        page_text=(
            "Please sign in to continue. Complete the CAPTCHA. Accept cookies. "
            "Select location before viewing jobs."
        ),
        page_html=(
            '<input type="password" />'
            '<div class="g-recaptcha"></div>'
            '<select id="location"></select>'
        ),
        extracted_count=0,
        has_search_input=False,
    )

    assert BARRIER_SIGNAL_LOGIN in signals
    assert BARRIER_SIGNAL_CAPTCHA in signals
    assert BARRIER_SIGNAL_COOKIE in signals
    assert BARRIER_SIGNAL_LOCATION in signals


def test_detect_browser_barriers_marks_unclear_page_when_no_signals() -> None:
    signals = detect_browser_barriers(
        page_text="Welcome to our corporate site.",
        page_html="<main><p>Welcome</p></main>",
        extracted_count=0,
        has_search_input=False,
    )

    assert signals == [BARRIER_SIGNAL_UNCLEAR]


def test_extract_location_returns_known_location_line() -> None:
    description = "Cloud Engineer Toronto, Ontario, Canada AWS Kubernetes Terraform"

    location = extract_location(description)

    assert location is not None
    assert "Toronto" in location


def test_collect_browser_jobs_returns_empty_without_browser_allowed_companies(
    tmp_path: Path,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(
        connection,
        [_browser_company(source_mode="needs_url", careers_url=None)],
    )

    results = collect_browser_jobs(connection, limit=3, headless=True)

    assert results == []


def test_collect_company_jobs_skips_when_source_is_not_browser_allowed(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    company = _browser_company(source_mode="needs_url", careers_url=None)
    upsert_companies(connection, [company])

    result = collect_company_jobs(
        connection,
        company=company,
        page=None,
    )

    assert result["status"] == "skipped"
    assert "needs_url" in result["reason"]
    assert get_interventions(connection) == []
