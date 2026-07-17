from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

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
    SOURCE_SCOPE_CONFIRMED,
    BrowserPagePolicy,
    _apply_sort_policy,
    _apply_source_scope_job_safety_gate,
    _build_source_scope_status,
    _compute_max_cards_per_source,
    _detect_national_bank_canada_page_evidence,
    _initial_source_scope_status,
    _source_navigation_timeout_ms,
    _url_uses_location_scope,
    collect_browser_jobs,
    collect_company_jobs,
    load_audit_max_pages_per_source,
    load_audit_scope_locations,
    load_browser_max_pages_for_company,
    load_browser_max_pages_per_source,
    load_browser_page_policy,
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


def test_default_trusted_page_policy_uses_twenty_pages(tmp_path: Path) -> None:
    config_path = tmp_path / "discovery.yaml"
    config_path.write_text("browser:\n  max_pages_per_source: 20\n", encoding="utf-8")

    policy = load_browser_page_policy("Example Browser Co", config_path)

    assert policy.page_policy == "capped"
    assert policy.max_pages(audit=False) == 20
    assert policy.max_pages(audit=True) == 20


def test_special_page_policies_cover_all_pages_and_rbc_audit_override(tmp_path: Path) -> None:
    config_path = tmp_path / "discovery.yaml"
    config_path.write_text(
        """
browser:
  max_pages_per_source: 20
  safety_ceiling_pages: 500
  per_company_page_policies:
    Scotiabank:
      page_policy: all_available
      sort_policy: source_default_all_pages
    Cognizant:
      page_policy: all_available
      sort_policy: source_default_all_pages
    RBC:
      production_page_cap: 20
      audit_page_cap: 75
      sort_policy: most_recent
""",
        encoding="utf-8",
    )

    scotiabank = load_browser_page_policy("Scotiabank", config_path)
    cognizant = load_browser_page_policy("Cognizant", config_path)
    rbc = load_browser_page_policy("RBC", config_path)

    assert scotiabank.page_policy == "all_available"
    assert scotiabank.max_pages(audit=False) == 500
    assert cognizant.sort_policy == "source_default_all_pages"
    assert rbc.max_pages(audit=False) == 20
    assert rbc.max_pages(audit=True) == 75


def test_sort_unavailable_source_reports_source_default_policy() -> None:
    result = _apply_sort_policy(
        object(),
        policy=BrowserPagePolicy(
            page_policy="all_available",
            sort_policy="source_default_all_pages",
        ),
    )

    assert result["sort_status"] == "unavailable_by_source"
    assert result["sort_method"] == "none"


def test_newest_sort_is_confirmed_before_pagination_when_available() -> None:
    class SortPage:
        def evaluate(self, _: str) -> dict[str, object]:
            return {"applied": True, "used": "Most Recent", "method": "ui_control"}

        def wait_for_timeout(self, _: int) -> None:
            return None

    result = _apply_sort_policy(SortPage(), policy=BrowserPagePolicy())

    assert result["sort_status"] == "confirmed"
    assert result["sort_used"] == "Most Recent"


def test_load_browser_max_pages_for_company_uses_company_override(tmp_path: Path) -> None:
    config_path = tmp_path / "discovery.yaml"
    config_path.write_text(
        """
source_scope:
  locations:
    - Canada
browser:
  max_pages_per_source: 8
  per_company_max_pages:
    Scotiabank: 15
""",
        encoding="utf-8",
    )

    assert load_browser_max_pages_for_company("Scotiabank", config_path) == 15
    assert load_browser_max_pages_for_company("RBC", config_path) == 8


def test_compute_max_cards_per_source_allows_dense_public_boards() -> None:
    assert _compute_max_cards_per_source(1) == 100
    assert _compute_max_cards_per_source(10) == 600


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


def test_url_uses_location_scope_supports_ibm_canada_query_param() -> None:
    assert _url_uses_location_scope(
        "https://www.ibm.com/careers/search?field_keyword_05%5B0%5D=Canada&p=2"
    ) is True


def test_url_uses_location_scope_supports_njoyn_country_id_canada_param() -> None:
    assert _url_uses_location_scope(
        "https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=joblisting"
        "&CountryID=CA&lang=1"
    ) is True


def test_url_uses_location_scope_supports_country_equals_ca_param() -> None:
    assert _url_uses_location_scope(
        "https://jobs.canadalife.com/search/?optionsFacetsDD_country=CA&startrow=25"
    ) is True


def test_url_uses_location_scope_supports_scotiabank_locationsearch_canada() -> None:
    assert _url_uses_location_scope(
        "https://jobs.scotiabank.com/search/?createNewAlert=false&q=&locationsearch=canada"
    ) is True


def test_initial_source_scope_status_detects_confirmed_workday_canada_url() -> None:
    status = _initial_source_scope_status(
        "https://manulife.wd3.myworkdayjobs.com/en-US/MFCJH_Jobs"
        "?Location_Country=a30a87ed25634629aa6c3958aa2b91ea"
    )

    assert status.confirmed is True
    assert status.status == "canada_scope_confirmed"
    assert status.method == "url_filter"


def test_initial_source_scope_status_marks_bmo_locale_url_unconfirmed() -> None:
    status = _initial_source_scope_status("https://jobs.bmo.com/ca/en/search-results")

    assert status.confirmed is False
    assert status.status == "canada_scope_unconfirmed"
    assert status.method == "manual_audit_url"


def test_initial_source_scope_status_detects_confirmed_scotiabank_canada_url() -> None:
    status = _initial_source_scope_status(
        "https://jobs.scotiabank.com/search/?createNewAlert=false&q=&locationsearch=canada"
    )

    assert status.confirmed is True
    assert status.status == "canada_scope_confirmed"
    assert status.method == "url_filter"


def test_initial_source_scope_status_marks_broad_listing_unconfirmed() -> None:
    status = _initial_source_scope_status("https://careers.example.com/jobs")

    assert status.confirmed is False
    assert status.status == "canada_scope_unconfirmed"
    assert status.method == "broad_unconfirmed"


def test_apply_source_scope_job_safety_gate_rejects_explicit_us_locations() -> None:
    source_scope = _build_source_scope_status(
        status=SOURCE_SCOPE_CONFIRMED,
        confirmed=True,
        method="url_filter",
        reason="Canada URL confirmed.",
        source_url_used="https://example.com/jobs?country=Canada",
    )
    rejected_job = {"title": "Cloud Engineer", "location": "Chicago, IL", "risk_flags": []}
    allowed_jobs, rejected_count, unknown_count = _apply_source_scope_job_safety_gate(
        [
            rejected_job,
            {"title": "DevOps Engineer", "location": "Toronto, Ontario, Canada"},
            {"title": "Linux Administrator", "location": ""},
        ],
        source_scope_status=source_scope,
    )

    assert [job["title"] for job in allowed_jobs] == [
        "DevOps Engineer",
        "Linux Administrator",
    ]
    assert rejected_count == 1
    assert unknown_count == 1
    assert rejected_job["risk_flags"] == ["outside_location_scope", "non_canada_location"]


def test_apply_source_scope_job_safety_gate_rejects_bmo_enus_urls_without_location() -> None:
    source_scope = _build_source_scope_status(
        status=SOURCE_SCOPE_CONFIRMED,
        confirmed=True,
        method="page_evidence",
        reason="Visible BMO results were ENCA only.",
        source_url_used="https://jobs.bmo.com/ca/en/search-results",
    )
    rejected_job = {
        "title": "Bank Manager",
        "location": "",
        "job_url": "https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260012209EXTERNALENUS/Bank-Manager",
        "risk_flags": [],
    }
    allowed_jobs, rejected_count, unknown_count = _apply_source_scope_job_safety_gate(
        [
            rejected_job,
            {
                "title": "Software Developer",
                "location": "",
                "job_url": "https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260000290EXTERNALENCA/Software-Developer",
            },
        ],
        source_scope_status=source_scope,
    )

    assert [job["title"] for job in allowed_jobs] == ["Software Developer"]
    assert rejected_count == 1
    assert unknown_count == 1
    assert rejected_job["risk_flags"] == ["outside_location_scope", "non_canada_location"]


def test_apply_source_scope_job_safety_gate_rejects_cgi_any_location_without_canada() -> None:
    source_scope = _build_source_scope_status(
        status=SOURCE_SCOPE_CONFIRMED,
        confirmed=True,
        method="url_filter",
        reason="Canada URL confirmed.",
        source_url_used="https://cgi.njoyn.com/CORP/xweb/xweb.asp?page=joblisting&CountryID=CA",
    )
    rejected_job = {
        "title": "Azure DevOps / Cloud Infrastructure Engineer (Azure)",
        "location": "Warsaw, Any CGI location",
        "risk_flags": [],
    }
    allowed_jobs, rejected_count, unknown_count = _apply_source_scope_job_safety_gate(
        [
            rejected_job,
            {
                "title": "Control-M System Administrator",
                "location": "Toronto, Canada",
                "job_url": "https://cgi.njoyn.com/CORP/xweb/xweb.asp?Jobid=J0426-1288",
            },
        ],
        source_scope_status=source_scope,
    )

    assert [job["title"] for job in allowed_jobs] == ["Control-M System Administrator"]
    assert rejected_count == 1
    assert unknown_count == 0
    assert rejected_job["risk_flags"] == ["outside_location_scope", "non_canada_location"]


class _FakeLocator:
    def inner_text(self, timeout: int | None = None) -> str:
        _ = timeout
        return "Public careers page"


class _FakePage:
    def __init__(self, url: str) -> None:
        self.url = url

    def goto(self, url: str, wait_until: str, timeout: int) -> None:
        _ = wait_until, timeout
        self.url = url

    def wait_for_timeout(self, timeout_ms: int) -> None:
        _ = timeout_ms

    def content(self) -> str:
        return "<main>Public careers page</main>"

    def locator(self, selector: str) -> _FakeLocator:
        _ = selector
        return _FakeLocator()


class _FakeNationalBankPage(_FakePage):
    def __init__(self, html: str) -> None:
        super().__init__("https://emplois.bnc.ca/en_CA/careers/searchjobs")
        self._html = html

    def content(self) -> str:
        return self._html


def test_collect_company_jobs_blocks_unconfirmed_scope_before_extraction(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    company = _browser_company(careers_url="https://jobs.bmo.com/ca/en/search-results")
    upsert_companies(connection, [company])

    monkeypatch.setattr("collectors.browser_collector.dismiss_cookie_banner", lambda page: None)
    monkeypatch.setattr(
        "collectors.browser_collector.dismiss_ibm_language_prompt",
        lambda page: None,
    )
    monkeypatch.setattr(
        "collectors.browser_collector.navigate_to_job_search_page",
        lambda page: None,
    )
    monkeypatch.setattr(
        "collectors.browser_collector.detect_browser_barriers",
        lambda **kwargs: [],
    )
    monkeypatch.setattr("collectors.browser_collector.find_search_input", lambda page: None)
    monkeypatch.setattr(
        "collectors.browser_collector.extract_visible_job_cards_with_diagnostics",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not extract")),
    )

    result = collect_company_jobs(
        connection,
        company=company,
        page=_FakePage(str(company["careers_url"])),
    )

    assert result["status"] == "canada_scope_unconfirmed"
    assert result["pagination_stop_reason"] == "scope_not_confirmed_before_pagination"
    assert result["source_scope_confirmed"] is False
    assert result["source_scope_method"] == "manual_audit_url"


def test_detect_national_bank_canada_page_evidence_confirms_visible_canadian_results() -> None:
    page = _FakeNationalBankPage(
        """
        <table>
          <tr>
            <td data-th="Location(s)">Montreal, Quebec</td>
          </tr>
          <tr>
            <td data-th="Location(s)">Toronto, Ontario</td>
          </tr>
          <tr>
            <td data-th="Location(s)">Calgary, Alberta</td>
          </tr>
        </table>
        """
    )

    evidence = _detect_national_bank_canada_page_evidence(page)

    assert evidence is not None
    assert evidence["method"] == "page_evidence"


def test_detect_national_bank_canada_page_evidence_rejects_non_canadian_rows() -> None:
    page = _FakeNationalBankPage(
        """
        <table>
          <tr>
            <td data-th="Location(s)">Montreal, Quebec</td>
          </tr>
          <tr>
            <td data-th="Location(s)">New York, NY</td>
          </tr>
          <tr>
            <td data-th="Location(s)">Toronto, Ontario</td>
          </tr>
        </table>
        """
    )

    assert _detect_national_bank_canada_page_evidence(page) is None


def test_collect_company_jobs_allows_broad_collection_only_for_diagnostics(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    company = _browser_company(careers_url="https://jobs.bmo.com/ca/en/search-results")
    upsert_companies(connection, [company])

    monkeypatch.setattr("collectors.browser_collector.dismiss_cookie_banner", lambda page: None)
    monkeypatch.setattr(
        "collectors.browser_collector.dismiss_ibm_language_prompt",
        lambda page: None,
    )
    monkeypatch.setattr(
        "collectors.browser_collector.navigate_to_job_search_page",
        lambda page: None,
    )
    monkeypatch.setattr(
        "collectors.browser_collector.detect_browser_barriers",
        lambda **kwargs: [],
    )
    monkeypatch.setattr("collectors.browser_collector.find_search_input", lambda page: None)
    monkeypatch.setattr(
        "collectors.browser_collector.extract_visible_job_cards_with_diagnostics",
        lambda *args, **kwargs: (
            [],
            SimpleNamespace(
                pagination_detected=False,
                pagination_stop_reason="no_jobs_found",
                pages_visited=["https://jobs.bmo.com/ca/en/search-results"],
                jobs_extracted_per_page=[0],
                page_html_snapshots=[],
            ),
        ),
    )

    result = collect_company_jobs(
        connection,
        company=company,
        page=_FakePage(str(company["careers_url"])),
        allow_broad_diagnostic_collection=True,
    )

    assert result["status"] == "completed"
    assert result["source_scope_confirmed"] is False
    assert result["broad_diagnostic_collection"] is True
    assert "diagnostic run" in str(result["source_scope_reason"])


def test_collect_company_jobs_confirms_bmo_scope_from_page_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    company = _browser_company(careers_url="https://jobs.bmo.com/ca/en/search-results")
    upsert_companies(connection, [company])

    monkeypatch.setattr("collectors.browser_collector.dismiss_cookie_banner", lambda page: None)
    monkeypatch.setattr(
        "collectors.browser_collector.dismiss_ibm_language_prompt",
        lambda page: None,
    )
    monkeypatch.setattr(
        "collectors.browser_collector.navigate_to_job_search_page",
        lambda page: None,
    )
    monkeypatch.setattr(
        "collectors.browser_collector.detect_browser_barriers",
        lambda **kwargs: [],
    )
    monkeypatch.setattr("collectors.browser_collector.find_search_input", lambda page: None)
    monkeypatch.setattr(
        "collectors.browser_collector.detect_bmo_canada_page_evidence",
        lambda page: {
            "confirmed": True,
            "method": "page_evidence",
            "reason": "Visible Canada chip plus visible ENCA result links.",
        },
    )
    monkeypatch.setattr(
        "collectors.browser_collector.extract_visible_job_cards_with_diagnostics",
        lambda *args, **kwargs: (
            [],
            SimpleNamespace(
                pagination_detected=False,
                pagination_stop_reason="no_jobs_found",
                pages_visited=["https://jobs.bmo.com/ca/en/search-results"],
                jobs_extracted_per_page=[0],
                page_html_snapshots=[],
            ),
        ),
    )

    result = collect_company_jobs(
        connection,
        company=company,
        page=_FakePage(str(company["careers_url"])),
    )

    assert result["status"] == "completed"
    assert result["source_scope_confirmed"] is True
    assert result["source_scope_method"] == "page_evidence"


def test_collect_company_jobs_confirms_ntt_scope_from_country_facet(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    company = _browser_company(
        name="NTT DATA",
        careers_url="https://careers.services.global.ntt/global/en/search-results",
    )
    upsert_companies(connection, [company])

    monkeypatch.setattr("collectors.browser_collector.dismiss_cookie_banner", lambda page: None)
    monkeypatch.setattr(
        "collectors.browser_collector.dismiss_ibm_language_prompt",
        lambda page: None,
    )
    monkeypatch.setattr(
        "collectors.browser_collector.navigate_to_job_search_page",
        lambda page: None,
    )
    monkeypatch.setattr(
        "collectors.browser_collector.detect_browser_barriers",
        lambda **kwargs: [],
    )
    monkeypatch.setattr("collectors.browser_collector.find_search_input", lambda page: None)
    monkeypatch.setattr(
        "collectors.browser_collector.apply_ntt_canada_filter",
        lambda page, location_scope: "Canada (NTT country facet)",
    )
    monkeypatch.setattr(
        "collectors.browser_collector.extract_visible_job_cards_with_diagnostics",
        lambda *args, **kwargs: (
            [],
            SimpleNamespace(
                pagination_detected=False,
                pagination_stop_reason="no_jobs_found",
                pages_visited=["https://careers.services.global.ntt/global/en/search-results"],
                jobs_extracted_per_page=[0],
                page_html_snapshots=[],
            ),
        ),
    )

    result = collect_company_jobs(
        connection,
        company=company,
        page=_FakePage(str(company["careers_url"])),
    )

    assert result["status"] == "completed"
    assert result["source_scope_confirmed"] is True
    assert result["source_scope_method"] == "ui_filter"
    assert result["location_filter_method"] == "ntt_country_facet"


def test_collect_company_jobs_confirms_rbc_scope_from_country_facet(
    tmp_path: Path,
    monkeypatch,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    company = _browser_company(
        name="RBC",
        careers_url="https://jobs.rbc.com/ca/en/search-results?from=140&s=1",
    )
    upsert_companies(connection, [company])

    monkeypatch.setattr("collectors.browser_collector.dismiss_cookie_banner", lambda page: None)
    monkeypatch.setattr(
        "collectors.browser_collector.dismiss_ibm_language_prompt",
        lambda page: None,
    )
    monkeypatch.setattr(
        "collectors.browser_collector.navigate_to_job_search_page",
        lambda page: None,
    )
    monkeypatch.setattr(
        "collectors.browser_collector.detect_browser_barriers",
        lambda **kwargs: [],
    )
    monkeypatch.setattr("collectors.browser_collector.find_search_input", lambda page: None)
    monkeypatch.setattr(
        "collectors.browser_collector.apply_rbc_canada_filter",
        lambda page, location_scope: "Canada (RBC country facet)",
    )
    monkeypatch.setattr(
        "collectors.browser_collector.extract_visible_job_cards_with_diagnostics",
        lambda *args, **kwargs: (
            [],
            SimpleNamespace(
                pagination_detected=False,
                pagination_stop_reason="no_jobs_found",
                pages_visited=["https://jobs.rbc.com/ca/en/search-results?from=140&s=1"],
                jobs_extracted_per_page=[0],
                page_html_snapshots=[],
            ),
        ),
    )

    result = collect_company_jobs(
        connection,
        company=company,
        page=_FakePage(str(company["careers_url"])),
    )

    assert result["status"] == "completed"
    assert result["source_scope_confirmed"] is True
    assert result["source_scope_method"] == "ui_filter"
    assert result["location_filter_method"] == "rbc_country_facet"
