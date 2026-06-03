"""Browser-assisted job collection using Playwright."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Error as PlaywrightError

from browser.extraction import (
    dismiss_cookie_banner,
    extract_visible_job_cards,
    find_search_input,
    navigate_to_job_search_page,
    search_with_keywords,
)
from browser.interventions import (
    BARRIER_SIGNAL_EXTRACTION_FAILED,
    build_intervention_result,
    create_browser_intervention,
    detect_browser_barriers,
)
from browser.session import BrowserSessionConfig, open_browser_session
from classifier.source_classifier import classify_source
from storage.db import (
    create_daily_run,
    finish_daily_run,
    get_companies_by_source_mode,
    mark_source_checked,
    update_company_source,
    upsert_job,
)


@dataclass(slots=True)
class BrowserCollectionConfig:
    """Configuration for browser-assisted collection."""

    limit: int = 3
    headless: bool = False
    timeout_ms: int = 15_000
    slow_mo_ms: int = 0
    db_path: Path | None = None


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


def collect_company_jobs(
    connection: sqlite3.Connection,
    *,
    company: dict[str, Any],
    page,
    save_jobs: bool = True,
    allowed_source_modes: set[str] | None = None,
) -> dict[str, Any]:
    """Collect jobs for a single browser-allowed company."""

    company_name = str(company["name"])
    source_name = str(company.get("website_category") or company_name)
    careers_url = str(company.get("careers_url") or "").strip()
    keywords = _normalize_keywords(company.get("keywords"))

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
            "jobs": [],
        }

    run_id = create_daily_run(
        connection,
        source_name=f"{company_name}:{source_name}",
        notes="browser collection started",
    )

    try:
        page.goto(careers_url, wait_until="load")
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

        query = search_with_keywords(page, keywords)
        post_search_cookie = dismiss_cookie_banner(page)
        if post_search_cookie:
            dismissed_cookie_steps.append(post_search_cookie)
            dismissed_cookie = " -> ".join(dismissed_cookie_steps)
        current_html = page.content()
        current_text = page.locator("body").inner_text(timeout=3_000)
        extracted_jobs = extract_visible_job_cards(
            page,
            company_name=company_name,
            source_name=source_name,
            source_mode=classification.source_mode,
        )
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
                    f"Paused after page inspection. Query={query or 'n/a'}; "
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
        if save_jobs:
            for job in extracted_jobs:
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
            notes=f"browser collection completed; query={query or 'none'}",
        )
        mark_source_checked(
            connection,
            company_name=company_name,
            source_name=source_name,
        )
        return {
            "company_name": company_name,
            "source_name": source_name,
            "status": "completed",
            "jobs_seen": len(extracted_jobs),
            "jobs_new": jobs_new,
            "query": query,
            "navigated_url": navigated_url,
            "cookie_dismissed": dismissed_cookie,
            "jobs": extracted_jobs,
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
            "error": str(exc),
            "jobs": [],
        }


def _normalize_keywords(value: object) -> list[str]:
    """Normalize company keyword config from YAML lists or SQLite JSON strings."""

    if value is None:
        return []
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            cleaned = value.strip()
            return [cleaned] if cleaned else []
        return _normalize_keywords(decoded)
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []
