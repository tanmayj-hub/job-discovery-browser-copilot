"""Collector routing helpers for safe source-mode handling."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import yaml

from classifier.source_classifier import classify_source
from collectors.api import collect_greenhouse_jobs, collect_lever_jobs
from collectors.base import CollectorResult
from collectors.browser_collector import collect_companies_with_browser

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DISCOVERY_CONFIG_PATH = PROJECT_ROOT / "config" / "discovery.yaml"
API_FRIENDLY_ATS_TYPES = {"greenhouse", "lever", "ashby", "smartrecruiters"}


def _get_api_collector(ats_type: str | None):
    if ats_type == "greenhouse":
        return collect_greenhouse_jobs
    if ats_type == "lever":
        return collect_lever_jobs
    return None


def load_api_browser_fallback_flag(
    path: Path = DEFAULT_DISCOVERY_CONFIG_PATH,
) -> bool:
    """Load explicit API-to-browser fallback policy from discovery config."""

    if not path.exists():
        return False
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    routing = payload.get("routing", {})
    if not isinstance(routing, dict):
        return False
    return bool(routing.get("api_fallback_to_browser", False))


def _as_collector_result(
    result: dict[str, Any],
    *,
    collector: str,
    ats_type: str | None,
    source_mode: str | None,
    fallback_used: bool = False,
    intervention_required: bool = False,
) -> CollectorResult:
    jobs = result.get("jobs", [])
    return CollectorResult(
        company_name=str(result.get("company_name") or ""),
        source_name=result.get("source_name"),
        status=str(result.get("status") or "unknown"),
        collector=collector,
        ats_type=ats_type,
        source_mode=source_mode,
        jobs_discovered=int(result.get("jobs_discovered", 0) or 0),
        jobs_scored=int(result.get("jobs_scored", 0) or 0),
        jobs_relevant=int(result.get("jobs_relevant", 0) or 0),
        jobs_saved=int(result.get("jobs_saved", 0) or 0),
        jobs=jobs if isinstance(jobs, list) else [],
        error=result.get("error"),
        fallback_used=fallback_used,
        intervention_required=intervention_required,
    )


def collect_company_jobs_routed(
    conn: sqlite3.Connection,
    company: dict[str, Any],
    *,
    headless: bool = False,
    save_jobs: bool = False,
    allow_api_browser_fallback: bool | None = None,
) -> CollectorResult:
    """Route a company source to the correct collector skeleton."""

    company_name = str(company.get("name") or company.get("company_name") or "")
    source_name = str(company.get("website_category") or company_name or "") or None
    classification = classify_source(
        {
            "name": company_name,
            "company_name": company_name,
            "source_name": company.get("source_name") or source_name,
            "website_category": company.get("website_category"),
            "careers_url": company.get("careers_url"),
            "ats_hint": company.get("ats_hint"),
            "source_mode": company.get("source_mode"),
        }
    )
    fallback_enabled = (
        load_api_browser_fallback_flag()
        if allow_api_browser_fallback is None
        else allow_api_browser_fallback
    )
    routed_company = dict(company)
    routed_company["source_mode"] = classification.source_mode
    routed_company["source_name"] = company.get("source_name") or source_name
    routed_company["ats_type"] = classification.ats_type

    if classification.source_mode == "manual_only":
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="manual_only",
            collector="manual_only",
            ats_type=classification.ats_type,
            source_mode=classification.source_mode,
            intervention_required=True,
        )

    if classification.source_mode == "needs_url":
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="needs_url",
            collector="needs_url",
            ats_type=classification.ats_type,
            source_mode=classification.source_mode,
            intervention_required=False,
        )

    if classification.source_mode == "api_allowed":
        api_collector = _get_api_collector(classification.ats_type)
        if api_collector is not None:
            api_result = api_collector(routed_company)
            if api_result.status in {"success", "no_jobs_found"} or not fallback_enabled:
                return api_result

            browser_result = collect_companies_with_browser(
                conn,
                companies=[company],
                headless=headless,
                save_jobs=save_jobs,
                allowed_source_modes={"api_allowed", "browser_allowed", "human_in_loop"},
            )[0]
            return _as_collector_result(
                browser_result,
                collector="browser_fallback",
                ats_type=classification.ats_type,
                source_mode=classification.source_mode,
                fallback_used=True,
                intervention_required=browser_result.get("status") == "paused",
            )

        if classification.ats_type in API_FRIENDLY_ATS_TYPES and not fallback_enabled:
            return CollectorResult(
                company_name=company_name,
                source_name=source_name,
                status="api_collector_not_implemented",
                collector="api_not_implemented",
                ats_type=classification.ats_type,
                source_mode=classification.source_mode,
            )

        browser_result = collect_companies_with_browser(
            conn,
            companies=[company],
            headless=headless,
            save_jobs=save_jobs,
            allowed_source_modes={"api_allowed", "browser_allowed", "human_in_loop"},
        )[0]
        return _as_collector_result(
            browser_result,
            collector="browser_fallback" if fallback_enabled else "browser",
            ats_type=classification.ats_type,
            source_mode=classification.source_mode,
            fallback_used=fallback_enabled,
            intervention_required=browser_result.get("status") == "paused",
        )

    if classification.source_mode in {"browser_allowed", "human_in_loop"}:
        browser_result = collect_companies_with_browser(
            conn,
            companies=[company],
            headless=headless,
            save_jobs=save_jobs,
            allowed_source_modes={"browser_allowed", "human_in_loop"},
        )[0]
        return _as_collector_result(
            browser_result,
            collector="browser",
            ats_type=classification.ats_type,
            source_mode=classification.source_mode,
            intervention_required=browser_result.get("status") == "paused",
        )

    return CollectorResult(
        company_name=company_name,
        source_name=source_name,
        status="unsupported_source_mode",
        collector="needs_url",
        ats_type=classification.ats_type,
        source_mode=classification.source_mode,
        error=f"Unsupported source mode: {classification.source_mode}",
    )


def collect_companies_routed(
    conn: sqlite3.Connection,
    companies: list[dict[str, Any]],
    *,
    headless: bool = False,
    save_jobs: bool = False,
    allow_api_browser_fallback: bool | None = None,
) -> list[CollectorResult]:
    """Collect a company batch through the routing skeleton."""

    return [
        collect_company_jobs_routed(
            conn,
            company,
            headless=headless,
            save_jobs=save_jobs,
            allow_api_browser_fallback=allow_api_browser_fallback,
        )
        for company in companies
    ]
