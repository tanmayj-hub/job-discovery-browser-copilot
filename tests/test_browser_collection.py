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
from collectors.browser_collector import (
    _source_navigation_timeout_ms,
    _url_uses_location_scope,
    collect_browser_jobs,
    collect_company_jobs,
    load_audit_max_pages_per_source,
    load_audit_scope_locations,
    load_browser_max_pages_per_source,
    load_source_scope_locations,
)
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


def test_detect_browser_barriers_ignores_nav_sign_in_and_invisible_recaptcha() -> None:
    signals = detect_browser_barriers(
        page_text=(
            "Sign in Jobs Search jobs Cloud Engineer Toronto, Ontario, Canada "
            "Posted 2 days ago"
        ),
        page_html=(
            '<iframe aria-hidden="true" src="https://www.google.com/recaptcha/api2/'
            'anchor?size=invisible"></iframe>'
            '<textarea class="g-recaptcha-response" style="display: none;"></textarea>'
        ),
        extracted_count=3,
        has_search_input=True,
    )

    assert signals == []


def test_detect_browser_barriers_flags_bot_protection_captcha_page() -> None:
    signals = detect_browser_barriers(
        page_text=(
            "Your activity and behavior on this site made us think that you are a bot. "
            "Please solve this CAPTCHA to request unblock to the website."
        ),
        page_html="<main>Radware Captcha Page</main>",
        extracted_count=0,
        has_search_input=False,
    )

    assert BARRIER_SIGNAL_CAPTCHA in signals


def test_detect_browser_barriers_does_not_flag_search_location_filter() -> None:
    signals = detect_browser_barriers(
        page_text=(
            "Search jobs at Accenture 184 Results Search locations Location Filter Results"
        ),
        page_html=(
            '<input type="search" aria-label="Search locations" />'
            '<div class="filters">Location</div>'
        ),
        extracted_count=2,
        has_search_input=True,
    )

    assert BARRIER_SIGNAL_LOCATION not in signals


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


def test_load_source_scope_locations_uses_location_only_config(tmp_path: Path) -> None:
    config_path = tmp_path / "discovery.yaml"
    config_path.write_text(
        """
source_scope:
  locations:
    - Canada
    - Toronto
    - Remote
""",
        encoding="utf-8",
    )

    assert load_source_scope_locations(config_path) == ("Canada", "Toronto", "Remote")


def test_load_browser_max_pages_per_source_uses_discovery_config(tmp_path: Path) -> None:
    config_path = tmp_path / "discovery.yaml"
    config_path.write_text(
        """
source_scope:
  locations:
    - Canada
browser:
  max_pages_per_source: 8
""",
        encoding="utf-8",
    )

    assert load_browser_max_pages_per_source(config_path) == 8


def test_load_audit_scope_locations_uses_canada_only_audit_config(tmp_path: Path) -> None:
    config_path = tmp_path / "discovery.yaml"
    config_path.write_text(
        """
source_scope:
  locations:
    - Canada
    - Toronto
audit_scope:
  locations:
    - Canada
""",
        encoding="utf-8",
    )

    assert load_audit_scope_locations(config_path) == ("Canada",)


def test_load_audit_max_pages_per_source_uses_audit_config(tmp_path: Path) -> None:
    config_path = tmp_path / "discovery.yaml"
    config_path.write_text(
        """
audit_scope:
  locations:
    - Canada
  max_pages_per_source: 10
browser:
  max_pages_per_source: 8
""",
        encoding="utf-8",
    )

    assert load_audit_max_pages_per_source(config_path) == 10


def test_source_navigation_timeout_extends_for_tech_mahindra() -> None:
    assert (
        _source_navigation_timeout_ms(
            "Tech Mahindra",
            "https://careers.techmahindra.com/",
        )
        == 30_000
    )
    assert (
        _source_navigation_timeout_ms(
            "Example Browser Co",
            "https://careers.example.com",
        )
        == 15_000
    )


def test_url_uses_location_scope_supports_workday_location_country_format() -> None:
    assert _url_uses_location_scope(
        "https://sunlife.wd3.myworkdayjobs.com/Experienced-Jobs"
        "?Location_Country=a30a87ed25634629aa6c3958aa2b91ea"
    ) is True
