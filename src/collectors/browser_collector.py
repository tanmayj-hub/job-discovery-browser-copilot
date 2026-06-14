"""Browser-assisted job collection using Playwright."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError

from browser.extraction import (
    _wait_for_visible_bmo_job_links,
    apply_ibm_canada_filter,
    apply_ntt_canada_filter,
    detect_bmo_canada_page_evidence,
    dismiss_cookie_banner,
    dismiss_ibm_language_prompt,
    extract_visible_job_cards_with_diagnostics,
    find_search_input,
    is_ibm_careers_search_url,
    is_probable_job_listing,
    navigate_to_job_search_page,
    search_with_location_term,
)
from browser.interventions import (
    BARRIER_SIGNAL_EXTRACTION_FAILED,
    build_intervention_result,
    create_browser_intervention,
    detect_browser_barriers,
)
from browser.session import BrowserSessionConfig, open_browser_session
from classifier.source_classifier import classify_source
from processing.score import is_relevant_score, score_job
from storage.db import (
    create_daily_run,
    finish_daily_run,
    get_companies_by_source_mode,
    mark_source_checked,
    resolve_pending_interventions_for_company,
    update_company_source,
    upsert_job,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DISCOVERY_CONFIG_PATH = PROJECT_ROOT / "config" / "discovery.yaml"
DEFAULT_LOCATION_SCOPE = ("Canada", "Toronto", "Ontario", "Remote Canada", "Remote")
DEFAULT_AUDIT_LOCATION_SCOPE = ("Canada",)
DEFAULT_MAX_PAGES_PER_SOURCE = 10
CANADA_SCOPE_NAME = "Canada"
SOURCE_SCOPE_CONFIRMED = "canada_scope_confirmed"
SOURCE_SCOPE_UNCONFIRMED = "canada_scope_unconfirmed"
SOURCE_SCOPE_NEEDS_USER_URL = "needs_user_canada_url"
SOURCE_SCOPE_FILTER_BLOCKED = "filter_blocked"
SOURCE_SCOPE_MANUAL_INTERVENTION = "manual_intervention_required"
CANADIAN_LOCATION_HINTS = (
    "alberta",
    "british columbia",
    "calgary",
    "canada",
    "edmonton",
    "halifax",
    "manitoba",
    "montreal",
    "montréal",
    "new brunswick",
    "newfoundland",
    "nova scotia",
    "northwest territories",
    "nunavut",
    "ontario",
    "prince edward",
    "quebec",
    "québec",
    "regina",
    "saskatchewan",
    "saint-georges",
    "st. john",
    "st. john's",
    "toronto",
    "vancouver",
    "victoria",
    "winnipeg",
    "yukon",
)
US_STATE_ABBREVIATIONS = (
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DC",
    "DE",
    "FL",
    "GA",
    "HI",
    "IA",
    "ID",
    "IL",
    "IN",
    "KS",
    "KY",
    "LA",
    "MA",
    "MD",
    "ME",
    "MI",
    "MN",
    "MO",
    "MS",
    "MT",
    "NC",
    "ND",
    "NE",
    "NH",
    "NJ",
    "NM",
    "NV",
    "NY",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VA",
    "VT",
    "WA",
    "WI",
    "WV",
    "WY",
)
US_CITY_STATE_PATTERN = re.compile(
    r"\b[a-z0-9 .'/&()-]+,\s*(?:"
    + "|".join(state.lower() for state in US_STATE_ABBREVIATIONS)
    + r")\b"
)


@dataclass(slots=True)
class BrowserCollectionConfig:
    """Configuration for browser-assisted collection."""

    limit: int = 3
    headless: bool = False
    timeout_ms: int = 15_000
    slow_mo_ms: int = 0
    db_path: Path | None = None
    location_scope: tuple[str, ...] = DEFAULT_LOCATION_SCOPE


@dataclass(slots=True)
class SourceScopeStatus:
    """Structured Canada-scope status for one collection attempt."""

    scope_name: str = CANADA_SCOPE_NAME
    status: str = SOURCE_SCOPE_UNCONFIRMED
    confirmed: bool = False
    method: str = "unknown"
    reason: str = ""
    source_url_used: str = ""
    broad_diagnostic_collection: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_scope_name": self.scope_name,
            "source_scope_status": self.status,
            "source_scope_confirmed": self.confirmed,
            "source_scope_method": self.method,
            "source_scope_reason": self.reason,
            "source_url_used": self.source_url_used,
            "broad_diagnostic_collection": self.broad_diagnostic_collection,
        }


def _source_navigation_timeout_ms(
    company_name: str,
    careers_url: str,
    *,
    default_timeout_ms: int = 15_000,
) -> int:
    """Allow a small source-specific timeout bump for known slow public pages."""

    normalized_name = company_name.lower()
    normalized_url = careers_url.lower()
    if "tech mahindra" in normalized_name or "techmahindra" in normalized_url:
        return max(default_timeout_ms, 30_000)
    return default_timeout_ms


def collect_browser_jobs(
    connection: sqlite3.Connection,
    *,
    limit: int = 3,
    headless: bool = False,
) -> list[dict[str, Any]]:
    """Run browser collection for up to `limit` browser-allowed companies."""

    companies = get_companies_by_source_mode(
        connection,
        "browser_allowed",
        limit=limit,
    )
    if not companies:
        return []

    return collect_companies_with_browser(
        connection,
        companies=companies,
        headless=headless,
        save_jobs=True,
        allowed_source_modes={"browser_allowed"},
    )


def collect_companies_with_browser(
    connection: sqlite3.Connection,
    *,
    companies: list[dict[str, Any]],
    headless: bool = False,
    save_jobs: bool = True,
    allowed_source_modes: set[str] | None = None,
    allow_broad_diagnostic_collection: bool = False,
) -> list[dict[str, Any]]:
    """Collect jobs for a provided company batch using one headed browser session."""

    if not companies:
        return []

    config = BrowserSessionConfig(
        headless=headless,
        timeout_ms=15_000,
    )

    results: list[dict[str, Any]] = []
    with open_browser_session(config) as session:
        for company in companies:
            results.append(
                collect_company_jobs(
                    connection,
                    company=company,
                    page=session.page,
                    save_jobs=save_jobs,
                    allowed_source_modes=allowed_source_modes,
                    allow_broad_diagnostic_collection=allow_broad_diagnostic_collection,
                )
            )
    return results


def collect_single_company_with_browser(
    connection: sqlite3.Connection,
    *,
    company: dict[str, Any],
    headless: bool = False,
    save_jobs: bool = False,
    allowed_source_modes: set[str] | None = None,
    location_scope_override: tuple[str, ...] | None = None,
    max_pages_per_source_override: int | None = None,
    force_location_scope_search: bool = False,
    capture_page_html: bool = False,
    allow_broad_diagnostic_collection: bool = False,
) -> dict[str, Any]:
    """Collect one company through a dedicated browser session."""

    config = BrowserSessionConfig(
        headless=headless,
        timeout_ms=15_000,
    )
    with open_browser_session(config) as session:
        return collect_company_jobs(
            connection,
            company=company,
            page=session.page,
            save_jobs=save_jobs,
            allowed_source_modes=allowed_source_modes,
            location_scope_override=location_scope_override,
            max_pages_per_source_override=max_pages_per_source_override,
            force_location_scope_search=force_location_scope_search,
            capture_page_html=capture_page_html,
            allow_broad_diagnostic_collection=allow_broad_diagnostic_collection,
        )


def collect_company_jobs(
    connection: sqlite3.Connection,
    *,
    company: dict[str, Any],
    page,
    save_jobs: bool = True,
    allowed_source_modes: set[str] | None = None,
    location_scope_override: tuple[str, ...] | None = None,
    max_pages_per_source_override: int | None = None,
    force_location_scope_search: bool = False,
    capture_page_html: bool = False,
    allow_broad_diagnostic_collection: bool = False,
) -> dict[str, Any]:
    """Collect jobs for a single browser-allowed company."""

    company_name = str(company["name"])
    source_name = str(company.get("website_category") or company_name)
    careers_url = str(company.get("careers_url") or "").strip()
    location_scope = location_scope_override or load_source_scope_locations()
    max_pages_per_source = max_pages_per_source_override or load_browser_max_pages_per_source()
    max_cards_per_source = _compute_max_cards_per_source(max_pages_per_source)

    classification = classify_source(
        {
            "name": company_name,
            "source_name": source_name,
            "careers_url": careers_url,
            "ats_hint": company.get("ats_hint"),
            "website_category": company.get("website_category"),
        }
    )
    initial_scope_status = _initial_source_scope_status(careers_url)
    update_company_source(
        connection,
        company_name=company_name,
        careers_url=careers_url or None,
        source_mode=classification.source_mode,
        source_name=source_name,
    )
    permitted_modes = allowed_source_modes or {"browser_allowed"}
    if classification.source_mode not in permitted_modes:
        return {
            "company_name": company_name,
            "source_name": source_name,
            "status": "skipped",
            "reason": f"source mode is {classification.source_mode}",
            "jobs_seen": 0,
            "jobs_new": 0,
            "jobs_discovered": 0,
            "jobs_scored": 0,
            "jobs_relevant": 0,
            "jobs_saved": 0,
            "location_scope_used": False,
            "keyword_scope_used": False,
            "jobs": [],
            **initial_scope_status.to_dict(),
        }

    run_id = create_daily_run(
        connection,
        source_name=f"{company_name}:{source_name}",
        notes="browser collection started",
    )

    try:
        starting_url = careers_url
        page.goto(
            careers_url,
            wait_until="domcontentloaded",
            timeout=_source_navigation_timeout_ms(company_name, careers_url),
        )
        page.wait_for_timeout(1_000)
        dismissed_cookie_steps: list[str] = []
        dismissed_language_steps: list[str] = []
        location_filter_method = "none"
        initial_cookie = dismiss_cookie_banner(page)
        if initial_cookie:
            dismissed_cookie_steps.append(initial_cookie)
        initial_language = dismiss_ibm_language_prompt(page)
        if initial_language:
            dismissed_language_steps.append(initial_language)
        navigated_url = navigate_to_job_search_page(page)
        if navigated_url:
            navigated_cookie = dismiss_cookie_banner(page)
            if navigated_cookie:
                dismissed_cookie_steps.append(navigated_cookie)
            navigated_language = dismiss_ibm_language_prompt(page)
            if navigated_language:
                dismissed_language_steps.append(navigated_language)
        dismissed_cookie = " -> ".join(dismissed_cookie_steps) or None
        dismissed_language_prompt = " -> ".join(dismissed_language_steps) or None
        source_scope_status = _initial_source_scope_status(page.url or careers_url)

        initial_html = page.content()
        initial_text = page.locator("body").inner_text(timeout=3_000)
        has_search_input = find_search_input(page) is not None
        early_barriers = detect_browser_barriers(
            page_text=initial_text,
            page_html=initial_html,
            extracted_count=0,
            has_search_input=has_search_input,
        )
        if early_barriers:
            intervention_id = create_browser_intervention(
                connection,
                company_name=company_name,
                source_name=source_name,
                signals=early_barriers,
                source_url=page.url or careers_url,
            )
            finish_daily_run(
                connection,
                run_id,
                status="paused",
                notes=f"paused due to {', '.join(early_barriers)}",
            )
            mark_source_checked(
                connection,
                company_name=company_name,
                source_name=source_name,
            )
            intervention_result = build_intervention_result(
                company_name=company_name,
                source_name=source_name,
                signals=early_barriers,
                intervention_id=intervention_id,
            )
            intervention_result.update(initial_scope_status.to_dict())
            return intervention_result

        location_queries: list[str] = []
        location_scope_used = bool(source_scope_status.confirmed)
        keyword_scope_used = False
        if source_scope_status.confirmed:
            if is_ibm_careers_search_url(page.url or careers_url):
                location_queries.append("Canada (IBM URL filter)")
                location_filter_method = "ibm_canada_url_filter"
            else:
                location_queries.append("Canada (URL filter)")
                location_filter_method = "url_filter"
        if not source_scope_status.confirmed:
            ibm_filter_query = apply_ibm_canada_filter(page, location_scope)
            if ibm_filter_query:
                location_queries.append(ibm_filter_query)
                location_filter_method = "ibm_location_facet"
                source_scope_status = _build_source_scope_status(
                    status=SOURCE_SCOPE_CONFIRMED,
                    confirmed=True,
                    method="ui_filter",
                    reason="IBM's public Canada facet was applied before pagination.",
                    source_url_used=page.url or careers_url,
                )
                location_scope_used = True
        if not source_scope_status.confirmed:
            ntt_filter_query = apply_ntt_canada_filter(page, location_scope)
            if ntt_filter_query:
                location_queries.append(ntt_filter_query)
                location_filter_method = "ntt_country_facet"
                source_scope_status = _build_source_scope_status(
                    status=SOURCE_SCOPE_CONFIRMED,
                    confirmed=True,
                    method="ui_filter",
                    reason="NTT DATA's public Country facet was applied before pagination.",
                    source_url_used=page.url or careers_url,
                )
                location_scope_used = True
        if not source_scope_status.confirmed:
            bmo_evidence = None
            _wait_for_visible_bmo_job_links(page)
            for _ in range(10):
                bmo_evidence = detect_bmo_canada_page_evidence(page)
                if bmo_evidence:
                    break
                page.wait_for_timeout(500)
            if bmo_evidence:
                location_queries.append("Canada (BMO visible filter)")
                location_filter_method = "bmo_page_evidence"
                source_scope_status = _build_source_scope_status(
                    status=SOURCE_SCOPE_CONFIRMED,
                    confirmed=True,
                    method=str(bmo_evidence.get("method") or "page_evidence"),
                    reason=str(bmo_evidence.get("reason") or "").strip()
                    or (
                        "BMO's visible results page showed an active Canada filter and "
                        "Canada-only visible job links."
                    ),
                    source_url_used=page.url or careers_url,
                )
                location_scope_used = True
        if not source_scope_status.confirmed:
            national_bank_evidence = _detect_national_bank_canada_page_evidence(page)
            if national_bank_evidence:
                location_queries.append("Canada (National Bank page evidence)")
                location_filter_method = "national_bank_page_evidence"
                source_scope_status = _build_source_scope_status(
                    status=SOURCE_SCOPE_CONFIRMED,
                    confirmed=True,
                    method=str(national_bank_evidence.get("method") or "page_evidence"),
                    reason=str(national_bank_evidence.get("reason") or "").strip()
                    or (
                        "National Bank's public Canada careers board showed Canadian "
                        "job locations before pagination."
                    ),
                    source_url_used=page.url or careers_url,
                )
                location_scope_used = True
        if (
            force_location_scope_search
            and find_search_input(page) is not None
            and not source_scope_status.confirmed
        ):
            for location_term in location_scope:
                query = search_with_location_term(
                    page,
                    location_term,
                    allow_visible_results=True,
                )
                if query is None:
                    continue
                location_queries.append(query)
                location_filter_method = "location_search_input"
                if _url_uses_location_scope(page.url or careers_url):
                    source_scope_status = _build_source_scope_status(
                        status=SOURCE_SCOPE_CONFIRMED,
                        confirmed=True,
                        method="ui_filter",
                        reason=(
                            "The source exposed an explicit Canada-scoped results URL after "
                            "applying a public location filter."
                        ),
                        source_url_used=page.url or careers_url,
                    )
                    location_scope_used = True
                else:
                    source_scope_status = _build_source_scope_status(
                        status=SOURCE_SCOPE_UNCONFIRMED,
                        confirmed=False,
                        method="broad_unconfirmed",
                        reason=(
                            "A location search term was entered, but the source still did not "
                            "expose a confirmable Canada-scoped URL before pagination."
                        ),
                        source_url_used=page.url or careers_url,
                    )
                break

        if not source_scope_status.confirmed and not allow_broad_diagnostic_collection:
            blocked_status = source_scope_status
            blocked_result = {
                "company_name": company_name,
                "source_name": source_name,
                "source_mode": classification.source_mode,
                "ats_type": classification.ats_type,
                "status": blocked_status.status,
                "jobs_seen": 0,
                "jobs_new": 0,
                "jobs_discovered": 0,
                "jobs_scored": 0,
                "jobs_relevant": 0,
                "jobs_saved": 0,
                "starting_url": starting_url,
                "final_url": page.url or navigated_url or careers_url,
                "location_scope_used": False,
                "location_scope": list(location_scope),
                "location_queries": location_queries,
                "location_filter_method": location_filter_method,
                "keyword_scope_used": keyword_scope_used,
                "query": None,
                "navigated_url": navigated_url,
                "cookie_dismissed": dismissed_cookie,
                "language_prompt_action": dismissed_language_prompt,
                "pagination_detected": False,
                "pagination_stop_reason": "scope_not_confirmed_before_pagination",
                "pages_visited": [page.url or careers_url] if (page.url or careers_url) else [],
                "jobs_extracted_per_page": [],
                "page_html_snapshots": [],
                "max_pages_per_source": max_pages_per_source,
                "jobs": [],
                "candidate_jobs": [],
                "scored_jobs": [],
                "relevant_jobs": [],
                "non_canada_rejected": 0,
                "unknown_location_relevant": 0,
                **blocked_status.to_dict(),
            }
            finish_daily_run(
                connection,
                run_id,
                status=blocked_status.status,
                jobs_seen=0,
                jobs_new=0,
                notes=blocked_status.reason,
            )
            mark_source_checked(
                connection,
                company_name=company_name,
                source_name=source_name,
            )
            return blocked_result

        if not source_scope_status.confirmed and allow_broad_diagnostic_collection:
            source_scope_status = _diagnostic_scope_status(
                source_scope_status,
                reason=(
                    f"{source_scope_status.reason} Broad collection continued only for a "
                    "diagnostic run and must not be treated as verification evidence."
                ),
            )

        extraction_jobs, extraction_diagnostics = extract_visible_job_cards_with_diagnostics(
            page,
            company_name=company_name,
            source_name=source_name,
            source_mode=classification.source_mode,
            max_cards=max_cards_per_source,
            max_pages=max_pages_per_source,
            capture_page_html=capture_page_html,
        )
        extracted_jobs = extraction_jobs
        if not extracted_jobs and find_search_input(page) is not None:
            for location_term in location_scope:
                query = search_with_location_term(
                    page,
                    location_term,
                    allow_visible_results=force_location_scope_search,
                )
                if query is None:
                    continue
                location_queries.append(query)
                location_filter_method = "location_search_input"
                if _url_uses_location_scope(page.url or careers_url):
                    source_scope_status = _build_source_scope_status(
                        status=SOURCE_SCOPE_CONFIRMED,
                        confirmed=True,
                        method="ui_filter",
                        reason=(
                            "The source exposed an explicit Canada-scoped results URL after "
                            "applying a public location filter."
                        ),
                        source_url_used=page.url or careers_url,
                    )
                    location_scope_used = True
                search_jobs, extraction_diagnostics = extract_visible_job_cards_with_diagnostics(
                    page,
                    company_name=company_name,
                    source_name=source_name,
                    source_mode=classification.source_mode,
                    max_cards=max_cards_per_source,
                    max_pages=max_pages_per_source,
                    capture_page_html=capture_page_html,
                )
                extracted_jobs.extend(search_jobs)
            extracted_jobs = _dedupe_collected_jobs(extracted_jobs)

        post_search_cookie = dismiss_cookie_banner(page)
        if post_search_cookie:
            dismissed_cookie_steps.append(post_search_cookie)
            dismissed_cookie = " -> ".join(dismissed_cookie_steps)
        post_search_language = dismiss_ibm_language_prompt(page)
        if post_search_language:
            dismissed_language_steps.append(post_search_language)
            dismissed_language_prompt = " -> ".join(dismissed_language_steps)
        current_html = page.content()
        current_text = page.locator("body").inner_text(timeout=3_000)
        late_barriers = detect_browser_barriers(
            page_text=current_text,
            page_html=current_html,
            extracted_count=len(extracted_jobs),
            has_search_input=find_search_input(page) is not None,
        )
        if late_barriers:
            intervention_id = create_browser_intervention(
                connection,
                company_name=company_name,
                source_name=source_name,
                signals=late_barriers,
                source_url=page.url or careers_url,
                notes=(
                    "Paused after page inspection. "
                    f"location_queries={location_queries or 'none'}; "
                    f"location_filter_method={location_filter_method}; "
                    f"keyword_scope_used={keyword_scope_used}; "
                    f"navigated_url={navigated_url or 'none'}; "
                    f"cookie_dismissed={dismissed_cookie or 'none'}; "
                    f"language_prompt_dismissed={dismissed_language_prompt or 'none'}"
                ),
            )
            finish_daily_run(
                connection,
                run_id,
                status="paused",
                jobs_seen=len(extracted_jobs),
                jobs_new=0,
                notes=f"paused due to {', '.join(late_barriers)}",
            )
            mark_source_checked(
                connection,
                company_name=company_name,
                source_name=source_name,
            )
            intervention_result = build_intervention_result(
                company_name=company_name,
                source_name=source_name,
                signals=late_barriers,
                intervention_id=intervention_id,
            )
            intervention_result.update(source_scope_status.to_dict())
            return intervention_result

        jobs_new = 0
        scored_jobs = [_score_collected_job(job) for job in extracted_jobs]
        relevant_jobs = [
            job
            for job in scored_jobs
            if is_probable_job_listing(job, base_url=careers_url) and _is_relevant_scored_job(job)
        ]
        relevant_jobs, non_canada_rejected, unknown_location_relevant = (
            _apply_source_scope_job_safety_gate(
                relevant_jobs,
                source_scope_status=source_scope_status,
            )
        )
        if save_jobs:
            for job in relevant_jobs:
                existing = None
                if job.get("job_url"):
                    existing = connection.execute(
                        "SELECT id FROM jobs WHERE job_url = ?",
                        (job["job_url"],),
                    ).fetchone()
                upsert_job(connection, job)
                if existing is None:
                    jobs_new += 1

        finish_daily_run(
            connection,
            run_id,
            status="completed",
            jobs_seen=len(extracted_jobs),
            jobs_new=jobs_new,
            notes=(
                "browser collection completed; "
                f"location_queries={location_queries or 'none'}; "
                f"location_filter_method={location_filter_method}; "
                f"keyword_scope_used={keyword_scope_used}; "
                f"source_scope_status={source_scope_status.status}; "
                f"source_scope_method={source_scope_status.method}"
            ),
        )
        mark_source_checked(
            connection,
            company_name=company_name,
            source_name=source_name,
        )
        resolve_pending_interventions_for_company(connection, company_name=company_name)
        return {
            "company_name": company_name,
            "source_name": source_name,
            "source_mode": classification.source_mode,
            "ats_type": classification.ats_type,
            "status": "completed",
            "jobs_seen": len(extracted_jobs),
            "jobs_new": jobs_new,
            "jobs_discovered": len(extracted_jobs),
            "jobs_scored": len(scored_jobs),
            "jobs_relevant": len(relevant_jobs),
            "jobs_saved": jobs_new,
            "starting_url": starting_url,
            "final_url": page.url or navigated_url or careers_url,
            "location_scope_used": location_scope_used,
            "location_scope": list(location_scope),
            "location_queries": location_queries,
            "location_filter_method": location_filter_method,
            "keyword_scope_used": keyword_scope_used,
            "query": None,
            "navigated_url": navigated_url,
            "cookie_dismissed": dismissed_cookie,
            "language_prompt_action": dismissed_language_prompt,
            "pagination_detected": extraction_diagnostics.pagination_detected,
            "pagination_stop_reason": extraction_diagnostics.pagination_stop_reason,
            "pages_visited": extraction_diagnostics.pages_visited,
            "jobs_extracted_per_page": extraction_diagnostics.jobs_extracted_per_page,
            "page_html_snapshots": extraction_diagnostics.page_html_snapshots,
            "max_pages_per_source": max_pages_per_source,
            "jobs": extracted_jobs,
            "candidate_jobs": extracted_jobs,
            "scored_jobs": scored_jobs,
            "relevant_jobs": relevant_jobs,
            "non_canada_rejected": non_canada_rejected,
            "unknown_location_relevant": unknown_location_relevant,
            **source_scope_status.to_dict(),
        }
    except PlaywrightError as exc:
        create_browser_intervention(
            connection,
            company_name=company_name,
            source_name=source_name,
            signals=[BARRIER_SIGNAL_EXTRACTION_FAILED],
            source_url=careers_url,
            notes=f"Playwright error: {exc}",
        )
        finish_daily_run(
            connection,
            run_id,
            status="error",
            notes=f"Playwright error: {exc}",
        )
        return {
            "company_name": company_name,
            "source_name": source_name,
            "status": "error",
            "jobs_seen": 0,
            "jobs_new": 0,
            "jobs_discovered": 0,
            "jobs_scored": 0,
            "jobs_relevant": 0,
            "jobs_saved": 0,
            "location_scope_used": False,
            "keyword_scope_used": False,
            "error": str(exc),
            "jobs": [],
            **initial_scope_status.to_dict(),
        }
    except Exception as exc:  # noqa: BLE001
        create_browser_intervention(
            connection,
            company_name=company_name,
            source_name=source_name,
            signals=[BARRIER_SIGNAL_EXTRACTION_FAILED],
            source_url=careers_url,
            notes=f"Unhandled collector error: {exc}",
        )
        finish_daily_run(
            connection,
            run_id,
            status="error",
            notes=f"Unhandled collector error: {exc}",
        )
        return {
            "company_name": company_name,
            "source_name": source_name,
            "status": "error",
            "jobs_seen": 0,
            "jobs_new": 0,
            "jobs_discovered": 0,
            "jobs_scored": 0,
            "jobs_relevant": 0,
            "jobs_saved": 0,
            "location_scope_used": False,
            "keyword_scope_used": False,
            "error": str(exc),
            "jobs": [],
            **initial_scope_status.to_dict(),
        }


def load_source_scope_locations(
    path: Path = DEFAULT_DISCOVERY_CONFIG_PATH,
) -> tuple[str, ...]:
    """Load location-only source scope terms for pre-extraction discovery."""

    if not path.exists():
        return DEFAULT_LOCATION_SCOPE
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    source_scope = payload.get("source_scope", {})
    locations = source_scope.get("locations", []) if isinstance(source_scope, dict) else []
    normalized = tuple(str(location).strip() for location in locations if str(location).strip())
    return normalized or DEFAULT_LOCATION_SCOPE


def load_audit_scope_locations(
    path: Path = DEFAULT_DISCOVERY_CONFIG_PATH,
) -> tuple[str, ...]:
    """Load Canada-only audit scope terms without changing production defaults."""

    if not path.exists():
        return DEFAULT_AUDIT_LOCATION_SCOPE
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    audit_scope = payload.get("audit_scope", {})
    locations = audit_scope.get("locations", []) if isinstance(audit_scope, dict) else []
    normalized = tuple(str(location).strip() for location in locations if str(location).strip())
    return normalized or DEFAULT_AUDIT_LOCATION_SCOPE


def load_browser_max_pages_per_source(
    path: Path = DEFAULT_DISCOVERY_CONFIG_PATH,
) -> int:
    """Load the safe per-source pagination cap from discovery config."""

    if not path.exists():
        return DEFAULT_MAX_PAGES_PER_SOURCE
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    browser_config = payload.get("browser", {})
    raw_value = (
        browser_config.get("max_pages_per_source")
        if isinstance(browser_config, dict)
        else DEFAULT_MAX_PAGES_PER_SOURCE
    )
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_MAX_PAGES_PER_SOURCE
    return max(1, value)


def load_audit_max_pages_per_source(
    path: Path = DEFAULT_DISCOVERY_CONFIG_PATH,
) -> int:
    """Load audit pagination settings without changing production defaults."""

    if not path.exists():
        return DEFAULT_MAX_PAGES_PER_SOURCE
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    audit_scope = payload.get("audit_scope", {})
    raw_value = (
        audit_scope.get("max_pages_per_source")
        if isinstance(audit_scope, dict)
        else DEFAULT_MAX_PAGES_PER_SOURCE
    )
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_MAX_PAGES_PER_SOURCE
    return max(1, value)


def _score_collected_job(job: dict[str, Any]) -> dict[str, Any]:
    scored = dict(job)
    score_result = score_job(scored)
    scored["match_score"] = score_result.match_score
    scored["match_reasons"] = score_result.match_reasons
    scored["risk_flags"] = score_result.risk_flags
    scored["relevance_tier"] = score_result.relevance_tier
    return scored


def _is_relevant_scored_job(job: dict[str, Any]) -> bool:
    return is_relevant_score(
        int(job.get("match_score", 0) or 0),
        [str(reason) for reason in job.get("match_reasons", [])],
    )


def _url_uses_location_scope(url: str) -> bool:
    normalized = str(url or "").lower()
    return (
        "locationcountry=" in normalized
        or "location_country=" in normalized
        or "locationsearch=canada" in normalized
        or "field_keyword_05[0]=canada" in normalized
        or "field_keyword_05%5b0%5d=canada" in normalized
        or "country=ca" in normalized
        or "countryid=ca" in normalized
    )


def _url_looks_like_canada_locale_only(url: str) -> bool:
    parsed = urlparse(str(url or "").strip().lower())
    return "/ca/en/" in parsed.path or parsed.path.startswith("/ca/")


def _build_source_scope_status(
    *,
    status: str,
    confirmed: bool,
    method: str,
    reason: str,
    source_url_used: str,
    broad_diagnostic_collection: bool = False,
) -> SourceScopeStatus:
    return SourceScopeStatus(
        status=status,
        confirmed=confirmed,
        method=method,
        reason=reason,
        source_url_used=source_url_used,
        broad_diagnostic_collection=broad_diagnostic_collection,
    )


def _initial_source_scope_status(url: str) -> SourceScopeStatus:
    normalized_url = str(url or "").strip()
    if not normalized_url:
        return _build_source_scope_status(
            status=SOURCE_SCOPE_NEEDS_USER_URL,
            confirmed=False,
            method="unknown",
            reason="No official careers URL is configured for this source.",
            source_url_used="",
        )
    if _url_uses_location_scope(normalized_url):
        return _build_source_scope_status(
            status=SOURCE_SCOPE_CONFIRMED,
            confirmed=True,
            method="url_filter",
            reason="The source URL contains an explicit Canada filter signal.",
            source_url_used=normalized_url,
        )
    if _url_looks_like_canada_locale_only(normalized_url):
        return _build_source_scope_status(
            status=SOURCE_SCOPE_UNCONFIRMED,
            confirmed=False,
            method="manual_audit_url",
            reason=(
                "The source URL uses a Canada locale path, but that alone does not prove "
                "the job listing itself is location-scoped to Canada."
            ),
            source_url_used=normalized_url,
        )
    return _build_source_scope_status(
        status=SOURCE_SCOPE_UNCONFIRMED,
        confirmed=False,
        method="broad_unconfirmed",
        reason=(
            "The source started from a broad or global listing without an explicit "
            "Canada filter."
        ),
        source_url_used=normalized_url,
    )


def _diagnostic_scope_status(scope_status: SourceScopeStatus, *, reason: str) -> SourceScopeStatus:
    return _build_source_scope_status(
        status=scope_status.status,
        confirmed=scope_status.confirmed,
        method=scope_status.method,
        reason=reason,
        source_url_used=scope_status.source_url_used,
        broad_diagnostic_collection=True,
    )


def _is_explicit_non_canada_location(location: str | None) -> bool:
    normalized = str(location or "").strip().lower()
    if not normalized:
        return False
    if "any cgi location" in normalized and "canada" not in normalized:
        return True
    if any(
        marker in normalized
        for marker in (
            "united states",
            "united states of america",
            " usa",
            ", usa",
            "u.s.",
        )
    ):
        return True
    return bool(US_CITY_STATE_PATTERN.search(normalized))


def _is_explicit_non_canada_job_url(job_url: str | None) -> bool:
    normalized = str(job_url or "").strip().lower()
    return "jobs.bmo.com" in normalized and "externalenus" in normalized


def _detect_national_bank_canada_page_evidence(page) -> dict[str, str] | None:
    parsed = urlparse(str(page.url or "").strip())
    hostname = parsed.netloc.lower()
    path = parsed.path.lower()
    if "emplois.bnc.ca" not in hostname or "/careers/searchjobs" not in path:
        return None

    soup = BeautifulSoup(page.content(), "html.parser")
    location_cells = [
        _clean_location_text(cell.get_text(" ", strip=True))
        for cell in soup.select("td[data-th*='Location']")
    ]
    visible_locations = [location for location in location_cells if location]
    if len(visible_locations) < 3:
        return None
    if any(
        _looks_explicitly_non_canadian_visible_location(location)
        for location in visible_locations
    ):
        return None
    if not any(_looks_canadian_visible_location(location) for location in visible_locations):
        return None
    return {
        "confirmed": "true",
        "method": "page_evidence",
        "reason": (
            "National Bank's public search-results page exposed Canadian job locations "
            "before pagination without requiring a hidden location search workaround."
        ),
    }


def _clean_location_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().split())


def _looks_canadian_visible_location(location: str) -> bool:
    normalized = str(location or "").strip().lower()
    return any(hint in normalized for hint in CANADIAN_LOCATION_HINTS)


def _looks_explicitly_non_canadian_visible_location(location: str) -> bool:
    normalized = str(location or "").strip().lower()
    if not normalized:
        return False
    if any(marker in normalized for marker in ("united states", "usa", "new york")):
        return True
    return bool(US_CITY_STATE_PATTERN.search(normalized))


def _apply_source_scope_job_safety_gate(
    jobs: list[dict[str, Any]],
    *,
    source_scope_status: SourceScopeStatus,
) -> tuple[list[dict[str, Any]], int, int]:
    if not source_scope_status.confirmed:
        return jobs, 0, 0

    allowed_jobs: list[dict[str, Any]] = []
    non_canada_rejected = 0
    unknown_location_relevant = 0
    for job in jobs:
        location_text = str(job.get("location") or "").strip()
        if _is_explicit_non_canada_location(location_text) or _is_explicit_non_canada_job_url(
            job.get("job_url")
        ):
            risk_flags = list(job.get("risk_flags") or [])
            if "outside_location_scope" not in risk_flags:
                risk_flags.append("outside_location_scope")
            if "non_canada_location" not in risk_flags:
                risk_flags.append("non_canada_location")
            job["risk_flags"] = risk_flags
            non_canada_rejected += 1
            continue
        if not location_text:
            unknown_location_relevant += 1
        allowed_jobs.append(job)
    return allowed_jobs, non_canada_rejected, unknown_location_relevant


def _dedupe_collected_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_fallbacks: set[tuple[str, str, str]] = set()
    for job in jobs:
        job_url = str(job.get("job_url") or "").strip()
        title = str(job.get("title") or "").strip()
        company = str(job.get("company_name") or "").strip()
        location = str(job.get("location") or "").strip()
        if job_url:
            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)
        else:
            fallback = (company, title, location)
            if fallback in seen_fallbacks:
                continue
            seen_fallbacks.add(fallback)
        deduped.append(job)
    return deduped


def _compute_max_cards_per_source(max_pages_per_source: int) -> int:
    """Size the per-source candidate cap to fit dense public boards safely."""

    return max(100, max_pages_per_source * 60)
