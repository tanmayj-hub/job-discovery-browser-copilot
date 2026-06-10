"""Browser-assisted job collection using Playwright."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from playwright.sync_api import Error as PlaywrightError

from browser.extraction import (
    dismiss_cookie_banner,
    extract_visible_job_cards_with_diagnostics,
    find_search_input,
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


@dataclass(slots=True)
class BrowserCollectionConfig:
    """Configuration for browser-assisted collection."""

    limit: int = 3
    headless: bool = False
    timeout_ms: int = 15_000
    slow_mo_ms: int = 0
    db_path: Path | None = None
    location_scope: tuple[str, ...] = DEFAULT_LOCATION_SCOPE


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
) -> dict[str, Any]:
    """Collect jobs for a single browser-allowed company."""

    company_name = str(company["name"])
    source_name = str(company.get("website_category") or company_name)
    careers_url = str(company.get("careers_url") or "").strip()
    location_scope = location_scope_override or load_source_scope_locations()
    max_pages_per_source = max_pages_per_source_override or load_browser_max_pages_per_source()
    max_cards_per_source = max(20, max_pages_per_source * 20)

    classification = classify_source(
        {
            "name": company_name,
            "source_name": source_name,
            "careers_url": careers_url,
            "ats_hint": company.get("ats_hint"),
            "website_category": company.get("website_category"),
        }
    )
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
        initial_cookie = dismiss_cookie_banner(page)
        if initial_cookie:
            dismissed_cookie_steps.append(initial_cookie)
        navigated_url = navigate_to_job_search_page(page)
        if navigated_url:
            navigated_cookie = dismiss_cookie_banner(page)
            if navigated_cookie:
                dismissed_cookie_steps.append(navigated_cookie)
        dismissed_cookie = " -> ".join(dismissed_cookie_steps) or None

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
            return build_intervention_result(
                company_name=company_name,
                source_name=source_name,
                signals=early_barriers,
                intervention_id=intervention_id,
            )

        location_queries: list[str] = []
        location_scope_used = _url_uses_location_scope(page.url or careers_url)
        keyword_scope_used = False
        if location_scope_used:
            location_queries.append("Canada (URL filter)")
        if (
            force_location_scope_search
            and find_search_input(page) is not None
            and not location_scope_used
        ):
            for location_term in location_scope:
                query = search_with_location_term(
                    page,
                    location_term,
                    allow_visible_results=True,
                )
                if query is None:
                    continue
                location_scope_used = True
                location_queries.append(query)
                break

        extraction_jobs, extraction_diagnostics = extract_visible_job_cards_with_diagnostics(
            page,
            company_name=company_name,
            source_name=source_name,
            source_mode=classification.source_mode,
            max_cards=max_cards_per_source,
            max_pages=max_pages_per_source,
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
                location_scope_used = True
                location_queries.append(query)
                search_jobs, extraction_diagnostics = extract_visible_job_cards_with_diagnostics(
                    page,
                    company_name=company_name,
                    source_name=source_name,
                    source_mode=classification.source_mode,
                    max_cards=max_cards_per_source,
                    max_pages=max_pages_per_source,
                )
                extracted_jobs.extend(search_jobs)
            extracted_jobs = _dedupe_collected_jobs(extracted_jobs)

        post_search_cookie = dismiss_cookie_banner(page)
        if post_search_cookie:
            dismissed_cookie_steps.append(post_search_cookie)
            dismissed_cookie = " -> ".join(dismissed_cookie_steps)
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
                    f"keyword_scope_used={keyword_scope_used}; "
                    f"navigated_url={navigated_url or 'none'}; "
                    f"cookie_dismissed={dismissed_cookie or 'none'}"
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
            return build_intervention_result(
                company_name=company_name,
                source_name=source_name,
                signals=late_barriers,
                intervention_id=intervention_id,
            )

        jobs_new = 0
        scored_jobs = [_score_collected_job(job) for job in extracted_jobs]
        relevant_jobs = [
            job
            for job in scored_jobs
            if is_probable_job_listing(job, base_url=careers_url) and _is_relevant_scored_job(job)
        ]
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
                f"keyword_scope_used={keyword_scope_used}"
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
            "keyword_scope_used": keyword_scope_used,
            "query": None,
            "navigated_url": navigated_url,
            "cookie_dismissed": dismissed_cookie,
            "pagination_detected": extraction_diagnostics.pagination_detected,
            "pagination_stop_reason": extraction_diagnostics.pagination_stop_reason,
            "pages_visited": extraction_diagnostics.pages_visited,
            "jobs_extracted_per_page": extraction_diagnostics.jobs_extracted_per_page,
            "max_pages_per_source": max_pages_per_source,
            "jobs": extracted_jobs,
            "candidate_jobs": extracted_jobs,
            "scored_jobs": scored_jobs,
            "relevant_jobs": relevant_jobs,
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
        or "country=ca" in normalized
    )


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
