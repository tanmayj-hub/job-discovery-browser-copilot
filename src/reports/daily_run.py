"""Daily run orchestration and report generation."""

from __future__ import annotations

import csv
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from browser.extraction import get_job_quality_signals, is_probable_job_listing
from classifier.source_classifier import classify_source
from collectors.router import collect_companies_routed
from processing.score import is_relevant_score, score_job
from reports.source_observability import (
    compute_source_readiness,
    is_error_status,
    summarize_source_metrics,
)
from storage.db import (
    build_job_identity,
    get_companies,
    get_intervention_history,
    get_intervention_queue,
    get_job_by_id,
    get_jobs,
    initialize_database,
    record_source_observation,
    update_job_status,
    upsert_companies,
    upsert_job_record,
)

CollectorFunc = Callable[[Any, list[dict[str, Any]]], list[Any]]

ELIGIBLE_SOURCE_MODES = {"api_allowed", "browser_allowed", "human_in_loop"}
SKIPPED_SOURCE_MODES = {"needs_url", "manual_only", "avoid"}
SKIPPED_SOURCE_STATUSES = {
    "manual_only",
    "needs_url",
    "api_collector_not_implemented",
    "canada_scope_unconfirmed",
    "needs_user_canada_url",
    "filter_blocked",
    "manual_intervention_required",
}
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
class DailyRunArtifacts:
    """Output paths for the daily run."""

    report_path: Path
    csv_path: Path


@dataclass(slots=True)
class DailyRunResult:
    """Structured daily run summary."""

    run_date: str
    run_scope: str
    companies_checked: list[str]
    companies_skipped: list[dict[str, str]]
    interventions_needed: list[dict[str, Any]]
    intervention_history: list[dict[str, Any]]
    errors: list[str]
    jobs_discovered: int
    jobs_scored: int
    jobs_relevant: int
    jobs_inserted: int
    jobs_updated: int
    jobs_unchanged: int
    duplicates_skipped: int
    jobs_saved: list[dict[str, Any]]
    suspicious_saved_rows: list[dict[str, Any]]
    location_scope_used: bool
    keyword_scope_used: bool
    source_metrics: dict[str, int]
    routing_results: list[dict[str, Any]]
    artifacts: DailyRunArtifacts


def load_companies_yaml(path: Path) -> list[dict[str, Any]]:
    """Load company records from YAML."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    companies = payload.get("companies", [])
    return companies if isinstance(companies, list) else []


def normalize_company_filter_names(company_names: list[str] | None) -> set[str]:
    """Normalize an optional company filter for exact-name daily-run slices."""

    return {
        str(name).strip().lower()
        for name in (company_names or [])
        if str(name).strip()
    }


def _existing_company_map(connection) -> dict[str, dict[str, Any]]:
    return {company["name"]: company for company in get_companies(connection)}


def classify_company_sources(
    companies: list[dict[str, Any]],
    existing_companies: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Classify sources while preserving deliberate skip/manual choices."""

    existing_companies = existing_companies or {}
    classified: list[dict[str, Any]] = []

    for company in companies:
        merged = dict(company)
        existing = existing_companies.get(str(company["name"]))
        if existing:
            if not merged.get("careers_url") and existing.get("careers_url"):
                merged["careers_url"] = existing["careers_url"]
            if existing.get("source_mode") in {"manual_only", "avoid"}:
                merged["source_mode"] = existing["source_mode"]
            if existing.get("status"):
                merged["status"] = existing["status"]

        explicit_mode = str(merged.get("source_mode") or "").strip()
        if explicit_mode == "avoid":
            classified.append(merged)
            continue
        if explicit_mode == "manual_only":
            classified.append(merged)
            continue

        result = classify_source(
            {
                "name": merged["name"],
                "source_name": merged.get("website_category") or merged["name"],
                "website_category": merged.get("website_category"),
                "careers_url": merged.get("careers_url"),
                "ats_hint": merged.get("ats_hint"),
            }
        )
        merged["source_mode"] = result.source_mode
        classified.append(merged)

    return classified


def normalize_job(raw_job: dict[str, Any], company: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw collector job object into the storage shape."""

    return {
        "company_name": str(raw_job.get("company_name") or company["name"]).strip(),
        "title": str(raw_job.get("title") or "").strip(),
        "location": str(raw_job.get("location") or "").strip() or None,
        "job_url": str(raw_job.get("job_url") or "").strip() or None,
        "apply_url": str(raw_job.get("apply_url") or "").strip() or None,
        "source_name": str(
            raw_job.get("source_name")
            or company.get("website_category")
            or company["name"]
        ).strip(),
        "source_mode": str(raw_job.get("source_mode") or company["source_mode"]).strip(),
        "description": str(raw_job.get("description") or "").strip() or None,
        "date_posted": raw_job.get("date_posted"),
        "external_job_id": str(raw_job.get("external_job_id") or "").strip() or None,
        "ats_type": str(raw_job.get("ats_type") or "").strip() or None,
        "board_slug": str(raw_job.get("board_slug") or "").strip() or None,
        "raw_payload_json": str(raw_job.get("raw_payload_json") or "").strip() or None,
        "status": str(raw_job.get("status") or "new").strip(),
    }


def score_normalized_job(job: dict[str, Any]) -> dict[str, Any]:
    """Apply deterministic relevance scoring after collection and dedupe."""

    scored = dict(job)
    score_result = score_job(scored)
    scored["match_score"] = score_result.match_score
    scored["match_reasons"] = score_result.match_reasons
    scored["risk_flags"] = score_result.risk_flags
    scored["relevance_tier"] = score_result.relevance_tier
    return scored


def is_relevant_scored_job(job: dict[str, Any]) -> bool:
    """Return True when a scored job has more than location-only relevance."""

    return is_relevant_score(
        int(job.get("match_score", 0) or 0),
        [str(reason) for reason in job.get("match_reasons", [])],
    )


def is_actionable_job(job: dict[str, Any]) -> bool:
    """Reject non-job or non-actionable records before persistence."""

    return is_probable_job_listing(job, base_url=job.get("job_url") or None)


def _is_explicit_non_canada_location(location: object) -> bool:
    normalized = str(location or "").strip().lower()
    if not normalized:
        return False
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


def _is_explicit_non_canada_job_url(job_url: object) -> bool:
    normalized = str(job_url or "").strip().lower()
    return "jobs.bmo.com" in normalized and "externalenus" in normalized


def _apply_canada_location_safety_gate(
    jobs: list[dict[str, Any]],
    source_scope_by_key: dict[tuple[str, str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], Counter[tuple[str, str]], Counter[tuple[str, str]]]:
    filtered: list[dict[str, Any]] = []
    rejected_by_source: Counter[tuple[str, str]] = Counter()
    unknown_by_source: Counter[tuple[str, str]] = Counter()
    for job in jobs:
        source_key = job.get("_source_key")
        if not isinstance(source_key, tuple):
            filtered.append(job)
            continue
        scope = source_scope_by_key.get(source_key, {})
        if str(scope.get("source_scope_status") or "") != "canada_scope_confirmed":
            filtered.append(job)
            continue
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
            rejected_by_source[source_key] += 1
            continue
        if not location_text:
            unknown_by_source[source_key] += 1
        filtered.append(job)
    return filtered, rejected_by_source, unknown_by_source


def deduplicate_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate normalized jobs in memory before persistence."""

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for job in jobs:
        identity = build_job_identity(job)
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append(job)
    return deduped


def save_jobs(connection, jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """Persist normalized jobs and return saved rows plus change counts."""

    jobs_inserted = 0
    jobs_updated = 0
    jobs_unchanged = 0
    saved_jobs: list[dict[str, Any]] = []
    source_actions: list[dict[str, Any]] = []
    for job in jobs:
        upsert_result = upsert_job_record(connection, job)
        if upsert_result.action == "inserted":
            jobs_inserted += 1
        elif upsert_result.action == "updated":
            jobs_updated += 1
        else:
            jobs_unchanged += 1
        job_id = upsert_result.job_id
        saved = get_job_by_id(connection, job_id)
        if saved is not None:
            saved["was_new"] = upsert_result.action == "inserted"
            saved["save_action"] = upsert_result.action
            saved_jobs.append(saved)
            source_actions.append(
                {
                    "company_name": saved["company_name"],
                    "source_name": saved.get("source_name"),
                    "action": upsert_result.action,
                }
            )
    return {
        "jobs": saved_jobs,
        "jobs_inserted": jobs_inserted,
        "jobs_updated": jobs_updated,
        "jobs_unchanged": jobs_unchanged,
        "source_actions": source_actions,
    }


def reject_non_actionable_new_jobs(connection) -> int:
    """Mark previously saved non-actionable rows as rejected."""

    rejected = 0
    for job in get_jobs(connection):
        if str(job.get("status") or "new") != "new":
            continue
        if is_actionable_job(job):
            continue
        update_job_status(connection, int(job["id"]), "rejected")
        rejected += 1
    return rejected


def find_suspicious_saved_rows(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return saved rows that still look suspicious enough for manual review."""

    suspicious: list[dict[str, Any]] = []
    for job in jobs:
        signals = get_job_quality_signals(job, base_url=job.get("job_url") or None)
        severe_signals = [
            signal
            for signal in signals
            if signal
            in {
                "missing_title",
                "generic_title",
                "facet_count_title",
                "marketing_title",
                "missing_url",
                "non_actionable_url",
                "index_or_category_url",
            }
        ]
        if not severe_signals:
            continue
        suspicious.append(
            {
                "company_name": job.get("company_name"),
                "title": job.get("title"),
                "job_url": job.get("job_url"),
                "source_mode": job.get("source_mode"),
                "signals": severe_signals,
            }
        )
    return suspicious


def default_collectors() -> dict[str, CollectorFunc]:
    """Return default collector functions keyed by source mode."""

    def routed_batch(connection, companies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            result.to_dict()
            for result in collect_companies_routed(
                connection,
                companies=companies,
                headless=False,
                save_jobs=False,
            )
        ]

    return {
        "api_allowed": routed_batch,
        "browser_allowed": routed_batch,
        "human_in_loop": routed_batch,
    }


def _routing_summary_line(item: dict[str, Any]) -> str:
    collector = str(item.get("collector") or "-")
    status = str(item.get("status") or "-")
    source_mode = str(item.get("source_mode") or "-")
    ats_type = str(item.get("ats_type") or "-")
    fallback_used = bool(item.get("fallback_used", False))
    intervention_required = bool(item.get("intervention_required", False))
    return (
        f"- {item['company_name']} | mode {source_mode} | ats {ats_type} | "
        f"collector {collector} | status {status} | "
        f"scope={item.get('source_scope_status') or '-'} | "
        f"fallback_used={fallback_used} | intervention_required={intervention_required}"
    )


def _coerce_collector_result(result: Any) -> dict[str, Any]:
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if isinstance(result, dict):
        return result
    raise TypeError(f"Unsupported collector result type: {type(result)!r}")


def _normalize_raw_jobs(raw_jobs: object) -> list[dict[str, Any]]:
    if not isinstance(raw_jobs, list):
        return []
    return [item for item in raw_jobs if isinstance(item, dict)]


def _source_key(company_name: str, source_name: str | None) -> tuple[str, str]:
    return (company_name, str(source_name or "").strip())


def _source_summary_defaults(company: dict[str, Any]) -> dict[str, Any]:
    source_name = str(company.get("website_category") or company["name"])
    return {
        "company_name": company["name"],
        "source_name": source_name,
        "source_url": company.get("careers_url"),
        "source_mode": company.get("source_mode"),
        "ats_type": company.get("ats_type"),
        "collector": "not_run",
        "status": "not_run",
        "fallback_used": False,
        "intervention_required": False,
        "jobs_discovered": 0,
        "jobs_scored": 0,
        "jobs_relevant": 0,
        "jobs_saved": 0,
        "jobs_inserted": 0,
        "jobs_updated": 0,
        "jobs_unchanged": 0,
        "duplicates_skipped": 0,
        "source_scope_name": "Canada",
        "source_scope_status": None,
        "source_scope_confirmed": False,
        "source_scope_method": None,
        "source_scope_reason": None,
        "source_url_used": company.get("careers_url"),
        "broad_diagnostic_collection": False,
        "non_canada_rejected": 0,
        "unknown_location_relevant": 0,
        "pages_visited": 0,
        "pagination_stop_reason": None,
        "intervention_reason": None,
        "error": None,
    }


def _enrich_source_summary(
    company: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    summary = _source_summary_defaults(company)
    summary.update(
        {
            "source_name": result.get("source_name") or summary["source_name"],
            "source_mode": result.get("source_mode") or summary["source_mode"],
            "ats_type": result.get("ats_type") or summary["ats_type"],
            "collector": result.get("collector") or summary["collector"],
            "status": result.get("status") or summary["status"],
            "fallback_used": bool(result.get("fallback_used", False)),
            "intervention_required": bool(result.get("intervention_required", False)),
            "jobs_discovered": int(result.get("jobs_discovered", 0) or 0),
            "jobs_scored": int(result.get("jobs_scored", 0) or 0),
            "jobs_relevant": int(result.get("jobs_relevant", 0) or 0),
            "jobs_saved": int(result.get("jobs_saved", 0) or 0),
            "jobs_inserted": int(result.get("jobs_inserted", 0) or 0),
            "jobs_updated": int(result.get("jobs_updated", 0) or 0),
            "jobs_unchanged": int(result.get("jobs_unchanged", 0) or 0),
            "duplicates_skipped": int(result.get("duplicates_skipped", 0) or 0),
            "source_scope_name": result.get("source_scope_name") or summary["source_scope_name"],
            "source_scope_status": result.get("source_scope_status"),
            "source_scope_confirmed": bool(result.get("source_scope_confirmed", False)),
            "source_scope_method": result.get("source_scope_method"),
            "source_scope_reason": result.get("source_scope_reason"),
            "source_url_used": result.get("source_url_used") or result.get("starting_url")
            or summary["source_url"],
            "broad_diagnostic_collection": bool(
                result.get("broad_diagnostic_collection", False)
            ),
            "non_canada_rejected": int(result.get("non_canada_rejected", 0) or 0),
            "unknown_location_relevant": int(
                result.get("unknown_location_relevant", 0) or 0
            ),
            "pages_visited": int(result.get("pages_visited", 0) or 0),
            "pagination_stop_reason": result.get("pagination_stop_reason"),
            "intervention_reason": result.get("intervention_reason"),
            "error": result.get("error"),
        }
    )
    summary["readiness_label"] = compute_source_readiness(summary)
    return summary


def _routing_summary_table_row(item: dict[str, Any]) -> str:
    return (
        f"| {item['company_name']} | {item.get('source_name') or '-'} | "
        f"{item.get('source_mode') or '-'} | {item.get('ats_type') or '-'} | "
        f"{item.get('collector') or '-'} | {item.get('status') or '-'} | "
        f"{item.get('source_scope_status') or '-'} | "
        f"{item.get('source_scope_method') or '-'} | "
        f"{item.get('readiness_label') or '-'} | "
        f"{'yes' if item.get('fallback_used') else 'no'} | "
        f"{'yes' if item.get('intervention_required') else 'no'} | "
        f"{int(item.get('jobs_discovered', 0) or 0)} | "
        f"{int(item.get('jobs_scored', 0) or 0)} | "
        f"{int(item.get('jobs_relevant', 0) or 0)} | "
        f"{int(item.get('jobs_saved', 0) or 0)} | "
        f"{int(item.get('non_canada_rejected', 0) or 0)} | "
        f"{int(item.get('jobs_inserted', 0) or 0)} | "
        f"{int(item.get('jobs_updated', 0) or 0)} | "
        f"{int(item.get('jobs_unchanged', 0) or 0)} | "
        f"{int(item.get('duplicates_skipped', 0) or 0)} | "
        f"{(item.get('error') or '-')} |"
    )


def build_daily_artifact_paths(
    exports_dir: Path,
    *,
    run_date: date,
) -> DailyRunArtifacts:
    """Build output paths for report and CSV export."""

    exports_dir.mkdir(parents=True, exist_ok=True)
    stamp = run_date.isoformat()
    return DailyRunArtifacts(
        report_path=exports_dir / f"daily-report-{stamp}.md",
        csv_path=exports_dir / f"jobs-{stamp}.csv",
    )


def write_daily_report(
    path: Path,
    *,
    run_date: str,
    run_scope: str,
    companies_checked: list[str],
    companies_skipped: list[dict[str, str]],
    interventions_needed: list[dict[str, Any]],
    intervention_history: list[dict[str, Any]],
    errors: list[str],
    jobs: list[dict[str, Any]],
    jobs_discovered: int,
    jobs_scored: int,
    jobs_relevant: int,
    jobs_inserted: int,
    jobs_updated: int,
    jobs_unchanged: int,
    duplicates_skipped: int,
    suspicious_saved_rows: list[dict[str, Any]],
    location_scope_used: bool,
    keyword_scope_used: bool,
    routing_results: list[dict[str, Any]],
) -> None:
    """Write a Markdown summary report."""

    top_jobs = sorted(jobs, key=lambda job: int(job.get("match_score", 0)), reverse=True)[:10]
    source_metrics = summarize_source_metrics(routing_results)
    non_canada_rejected = sum(
        int(item.get("non_canada_rejected", 0) or 0) for item in routing_results
    )

    lines = [
        f"# Daily Job Discovery Report - {run_date}",
        "",
        "## Run Summary",
        f"- Run scope: {run_scope}",
        f"- Companies checked: {len(companies_checked)}",
        f"- Companies skipped: {len(companies_skipped)}",
        f"- Jobs discovered before scoring: {jobs_discovered}",
        f"- Jobs scored: {jobs_scored}",
        f"- Jobs relevant: {jobs_relevant}",
        f"- Jobs saved: {len(jobs)}",
        f"- Jobs inserted: {jobs_inserted}",
        f"- Jobs updated: {jobs_updated}",
        f"- Jobs unchanged: {jobs_unchanged}",
        f"- Duplicates skipped before scoring: {duplicates_skipped}",
        f"- Explicit non-Canada jobs rejected by safety gate: {non_canada_rejected}",
        f"- Location scope used: {location_scope_used}",
        f"- Keyword scope used: {keyword_scope_used}",
        f"- Interventions needed: {len(interventions_needed)}",
        f"- Resolved intervention history: {len(intervention_history)}",
        f"- Errors: {len(errors)}",
        "",
        "## Collection",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Companies checked | {len(companies_checked)} |",
        f"| Sources checked | {source_metrics['sources_checked']} |",
        f"| Sources skipped | {source_metrics['sources_skipped']} |",
        f"| Jobs discovered | {jobs_discovered} |",
        f"| Non-Canada jobs rejected | {non_canada_rejected} |",
        "",
        "## Evaluation",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Jobs scored | {jobs_scored} |",
        f"| Jobs relevant | {jobs_relevant} |",
        f"| Jobs saved | {len(jobs)} |",
        "",
        "## Storage And Dedupe",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Jobs inserted | {jobs_inserted} |",
        f"| Jobs updated | {jobs_updated} |",
        f"| Jobs unchanged | {jobs_unchanged} |",
        f"| Duplicates skipped | {duplicates_skipped} |",
        "",
        "## Routing Summary",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| API collectors used | {source_metrics['api_sources_used']} |",
        f"| Static JSON-LD used | {source_metrics['static_jsonld_used']} |",
        f"| Browser collectors used | {source_metrics['browser_collector_used']} |",
        f"| Browser fallbacks used | {source_metrics['browser_fallback_used']} |",
        f"| API collectors not implemented | {source_metrics['api_not_implemented']} |",
        f"| Manual-only skipped | {source_metrics['manual_only_skipped']} |",
        f"| Needs-URL skipped | {source_metrics['needs_url_skipped']} |",
        f"| Interventions required | {source_metrics['interventions_required']} |",
        f"| Errors | {source_metrics['errors']} |",
        "",
        "## Top Matched Jobs",
    ]

    if top_jobs:
        for job in top_jobs:
            lines.append(
                f"- {job['company_name']} | {job['title']} | score {job['match_score']} | "
                f"{job.get('job_url') or 'no URL'}"
            )
    else:
        lines.append("- No jobs saved in this run.")

    lines.extend(["", "## Companies Checked"])
    if companies_checked:
        lines.extend(f"- {name}" for name in companies_checked)
    else:
        lines.append("- None")

    lines.extend(["", "## Routing Results"])
    if routing_results:
        lines.extend(_routing_summary_line(item) for item in routing_results)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Source Outcomes",
            (
                "| Company | Source | Mode | ATS | Collector | Status | Scope | "
                "Scope Method | Readiness | Fallback | Intervention | Discovered | "
                "Scored | Relevant | Saved | Non-Canada Rejected | Inserted | "
                "Updated | Unchanged | Duplicates | Last Error |"
            ),
            (
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | "
                "--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
                "---: | --- |"
            ),
        ]
    )
    if routing_results:
        lines.extend(_routing_summary_table_row(item) for item in routing_results)
    else:
        lines.append(
            "| None | - | - | - | - | - | - | - | - | - | - | 0 | 0 | 0 | 0 | 0 | "
            "0 | 0 | 0 | 0 | - |"
        )

    lines.extend(["", "## Companies Skipped"])
    if companies_skipped:
        lines.extend(
            f"- {item['company_name']} | {item['source_mode']} | {item['reason']}"
            for item in companies_skipped
        )
    else:
        lines.append("- None")

    lines.extend(["", "## Suspicious Saved Rows"])
    if suspicious_saved_rows:
        lines.extend(
            f"- {item.get('company_name') or '-'} | {item.get('title') or '-'} | "
            f"{item.get('job_url') or 'no URL'} | signals={', '.join(item.get('signals', []))}"
            for item in suspicious_saved_rows
        )
    else:
        lines.append("- None")

    lines.extend(["", "## Active Pending Interventions"])
    if interventions_needed:
        lines.extend(
            f"- {item.get('company_name') or '-'} | {item.get('reason') or '-'} | "
            f"{item.get('remediation_label') or '-'} | {item.get('action_required') or '-'} | "
            f"occurrences={int(item.get('occurrence_count', 1) or 1)}"
            for item in interventions_needed
        )
    else:
        lines.append("- None")

    lines.extend(["", "## Resolved Intervention History"])
    if intervention_history:
        lines.extend(
            f"- {item.get('company_name') or '-'} | {item.get('reason') or '-'} | "
            f"{item.get('status') or '-'} | {item.get('resolved_at') or '-'}"
            for item in intervention_history[:20]
        )
    else:
        lines.append("- None")

    lines.extend(["", "## Errors"])
    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("- None")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_jobs_csv(path: Path, jobs: list[dict[str, Any]]) -> None:
    """Write a CSV export of saved jobs."""

    fieldnames = [
        "id",
        "company_name",
        "title",
        "location",
        "job_url",
        "apply_url",
        "source_name",
        "source_mode",
        "description",
        "date_posted",
        "external_job_id",
        "ats_type",
        "board_slug",
        "content_hash",
        "first_seen",
        "last_seen",
        "first_seen_at",
        "last_seen_at",
        "last_updated_at",
        "match_score",
        "match_reasons",
        "risk_flags",
        "status",
        "created_at",
        "updated_at",
    ]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for job in jobs:
            row = {field: job.get(field) for field in fieldnames}
            row["match_reasons"] = yaml.safe_dump(
                job.get("match_reasons", []),
                default_flow_style=True,
            ).strip()
            row["risk_flags"] = yaml.safe_dump(
                job.get("risk_flags", []),
                default_flow_style=True,
            ).strip()
            writer.writerow(row)


def run_daily_workflow(
    *,
    config_path: Path,
    db_path: Path,
    exports_dir: Path,
    run_date: date | None = None,
    collectors: dict[str, CollectorFunc] | None = None,
    company_names: list[str] | None = None,
    run_scope: str = "all",
) -> DailyRunResult:
    """Execute the end-to-end daily workflow."""

    effective_date = run_date or date.today()
    connection = initialize_database(db_path)
    existing_companies = _existing_company_map(connection)
    loaded_companies = load_companies_yaml(config_path)
    selected_names = normalize_company_filter_names(company_names)
    if selected_names:
        loaded_companies = [
            company
            for company in loaded_companies
            if str(company.get("name") or "").strip().lower() in selected_names
        ]
    classified_companies = classify_company_sources(loaded_companies, existing_companies)
    upsert_companies(connection, classified_companies)

    by_name = {company["name"]: company for company in classified_companies}
    collectors_by_mode = collectors or default_collectors()

    companies_checked: list[str] = []
    companies_skipped: list[dict[str, str]] = []
    errors: list[str] = []
    normalized_jobs: list[dict[str, Any]] = []
    jobs_discovered = 0
    location_scope_used = False
    keyword_scope_used = False
    routing_results: list[dict[str, Any]] = []
    source_company_map: dict[tuple[str, str], dict[str, Any]] = {}

    for company in classified_companies:
        mode = str(company.get("source_mode") or "")
        source_name = str(company.get("website_category") or company["name"])
        company["source_name"] = source_name
        source_company_map[_source_key(company["name"], source_name)] = company
        if mode in SKIPPED_SOURCE_MODES:
            skipped_result = _source_summary_defaults(company)
            skipped_result["collector"] = mode
            skipped_result["status"] = mode
            skipped_result["readiness_label"] = compute_source_readiness(skipped_result)
            routing_results.append(skipped_result)
            companies_skipped.append(
                {
                    "company_name": company["name"],
                    "source_mode": mode,
                    "reason": f"source mode {mode}",
                }
            )
            continue
        if mode not in ELIGIBLE_SOURCE_MODES:
            unsupported_result = _source_summary_defaults(company)
            unsupported_result["collector"] = "unsupported"
            unsupported_result["status"] = "unsupported_source_mode"
            unsupported_result["error"] = "source mode not eligible"
            unsupported_result["readiness_label"] = compute_source_readiness(unsupported_result)
            routing_results.append(unsupported_result)
            companies_skipped.append(
                {
                    "company_name": company["name"],
                    "source_mode": mode or "unknown",
                    "reason": "source mode not eligible",
                }
            )
            continue

        companies_checked.append(company["name"])
        collector = collectors_by_mode.get(mode)
        if collector is None:
            errors.append(f"No collector configured for {company['name']} ({mode})")
            continue

        results = collector(connection, [company])
        for raw_result in results:
            result = _coerce_collector_result(raw_result)
            enriched_result = _enrich_source_summary(company, result)
            routing_results.append(enriched_result)
            status = str(result.get("status") or "")
            job_items = _normalize_raw_jobs(result.get("jobs", []))
            jobs_discovered += int(result.get("jobs_discovered", len(job_items)) or 0)
            location_scope_used = location_scope_used or bool(
                result.get("location_scope_used", False)
            )
            keyword_scope_used = keyword_scope_used or bool(
                result.get("keyword_scope_used", False)
            )
            if result.get("error") and (is_error_status(status) or status == "paused"):
                errors.append(
                    f"{result.get('company_name')}: {result.get('error') or 'collector error'}"
                )
            if status in {"skipped", *SKIPPED_SOURCE_STATUSES}:
                companies_skipped.append(
                    {
                        "company_name": str(result.get("company_name") or company["name"]),
                        "source_mode": str(result.get("source_mode") or mode),
                        "reason": str(result.get("status") or "collector skipped"),
                    }
                )
            for raw_job in job_items:
                company_key = str(raw_job.get("company_name") or company["name"])
                normalized = normalize_job(raw_job, by_name[company_key])
                normalized["_source_key"] = _source_key(
                    company_key,
                    raw_job.get("source_name") or enriched_result["source_name"],
                )
                normalized_jobs.append(normalized)

    deduped_jobs = deduplicate_jobs(normalized_jobs)
    duplicates_skipped = max(0, len(normalized_jobs) - len(deduped_jobs))
    scored_jobs = [score_normalized_job(job) for job in deduped_jobs]
    prefiltered_relevant_jobs = [
        job for job in scored_jobs if is_actionable_job(job) and is_relevant_scored_job(job)
    ]
    source_scope_by_key = {
        _source_key(item["company_name"], item.get("source_name")): item
        for item in routing_results
    }
    relevant_jobs, non_canada_rejected_by_source, unknown_location_relevant_by_source = (
        _apply_canada_location_safety_gate(
            prefiltered_relevant_jobs,
            source_scope_by_key,
        )
    )
    save_summary = save_jobs(connection, relevant_jobs)
    saved_jobs = save_summary["jobs"]
    suspicious_saved_rows = find_suspicious_saved_rows(saved_jobs)
    raw_count_by_source = Counter(
        job["_source_key"] for job in normalized_jobs if "_source_key" in job
    )
    deduped_count_by_source = Counter(
        job["_source_key"] for job in deduped_jobs if "_source_key" in job
    )
    relevant_count_by_source = Counter(
        job["_source_key"] for job in relevant_jobs if "_source_key" in job
    )
    source_actions = save_summary["source_actions"]
    source_inserted_by_key = Counter(
        _source_key(item["company_name"], item.get("source_name"))
        for item in source_actions
        if item["action"] == "inserted"
    )
    source_updated_by_key = Counter(
        _source_key(item["company_name"], item.get("source_name"))
        for item in source_actions
        if item["action"] == "updated"
    )
    source_unchanged_by_key = Counter(
        _source_key(item["company_name"], item.get("source_name"))
        for item in source_actions
        if item["action"] == "unchanged"
    )
    for item in routing_results:
        key = _source_key(item["company_name"], item.get("source_name"))
        item["jobs_discovered"] = int(
            item.get("jobs_discovered", 0) or raw_count_by_source.get(key, 0)
        )
        item["jobs_scored"] = deduped_count_by_source.get(key, 0)
        item["jobs_relevant"] = relevant_count_by_source.get(key, 0)
        item["jobs_saved"] = relevant_count_by_source.get(key, 0)
        item["jobs_inserted"] = source_inserted_by_key.get(key, 0)
        item["jobs_updated"] = source_updated_by_key.get(key, 0)
        item["jobs_unchanged"] = source_unchanged_by_key.get(key, 0)
        item["duplicates_skipped"] = max(
            0,
            raw_count_by_source.get(key, 0) - deduped_count_by_source.get(key, 0),
        )
        item["non_canada_rejected"] = int(non_canada_rejected_by_source.get(key, 0))
        item["unknown_location_relevant"] = int(unknown_location_relevant_by_source.get(key, 0))
        item["readiness_label"] = compute_source_readiness(item)
        source_company = source_company_map.get(key) or by_name.get(item["company_name"])
        if source_company is not None:
            record_source_observation(
                connection,
                company_name=item["company_name"],
                source_name=str(
                    item.get("source_name")
                    or source_company.get("source_name")
                    or source_company["name"]
                ),
                source_mode=str(item.get("source_mode") or source_company.get("source_mode") or ""),
                careers_url=source_company.get("careers_url"),
                website_category=source_company.get("website_category"),
                ats_hint=source_company.get("ats_hint"),
                ats_type=item.get("ats_type"),
                collector=item.get("collector"),
                status=item.get("status"),
                error=item.get("error"),
                fallback_used=bool(item.get("fallback_used", False)),
                intervention_required=bool(item.get("intervention_required", False)),
                jobs_discovered=int(item.get("jobs_discovered", 0) or 0),
                jobs_scored=int(item.get("jobs_scored", 0) or 0),
                jobs_relevant=int(item.get("jobs_relevant", 0) or 0),
                jobs_saved=int(item.get("jobs_saved", 0) or 0),
                jobs_inserted=int(item.get("jobs_inserted", 0) or 0),
                jobs_updated=int(item.get("jobs_updated", 0) or 0),
                jobs_unchanged=int(item.get("jobs_unchanged", 0) or 0),
                duplicates_skipped=int(item.get("duplicates_skipped", 0) or 0),
                source_scope_name=item.get("source_scope_name"),
                source_scope_status=item.get("source_scope_status"),
                source_scope_confirmed=bool(item.get("source_scope_confirmed", False)),
                source_scope_method=item.get("source_scope_method"),
                source_scope_reason=item.get("source_scope_reason"),
                source_url_used=item.get("source_url_used"),
                broad_diagnostic_collection=bool(
                    item.get("broad_diagnostic_collection", False)
                ),
                non_canada_rejected=int(item.get("non_canada_rejected", 0) or 0),
                unknown_location_relevant=int(
                    item.get("unknown_location_relevant", 0) or 0
                ),
            )

    reject_non_actionable_new_jobs(connection)
    source_metrics = summarize_source_metrics(routing_results)
    artifacts = build_daily_artifact_paths(exports_dir, run_date=effective_date)
    write_jobs_csv(artifacts.csv_path, saved_jobs)
    interventions_needed = get_intervention_queue(connection)
    intervention_history = get_intervention_history(connection)
    write_daily_report(
        artifacts.report_path,
        run_date=effective_date.isoformat(),
        run_scope=run_scope,
        companies_checked=companies_checked,
        companies_skipped=companies_skipped,
        interventions_needed=interventions_needed,
        intervention_history=intervention_history,
        errors=errors,
        jobs=saved_jobs,
        jobs_discovered=jobs_discovered,
        jobs_scored=len(scored_jobs),
        jobs_relevant=len(relevant_jobs),
        jobs_inserted=save_summary["jobs_inserted"],
        jobs_updated=save_summary["jobs_updated"],
        jobs_unchanged=save_summary["jobs_unchanged"],
        duplicates_skipped=duplicates_skipped,
        suspicious_saved_rows=suspicious_saved_rows,
        location_scope_used=location_scope_used,
        keyword_scope_used=keyword_scope_used,
        routing_results=routing_results,
    )

    return DailyRunResult(
        run_date=effective_date.isoformat(),
        run_scope=run_scope,
        companies_checked=companies_checked,
        companies_skipped=companies_skipped,
        interventions_needed=interventions_needed,
        intervention_history=intervention_history,
        errors=errors,
        jobs_discovered=jobs_discovered,
        jobs_scored=len(scored_jobs),
        jobs_relevant=len(relevant_jobs),
        jobs_inserted=save_summary["jobs_inserted"],
        jobs_updated=save_summary["jobs_updated"],
        jobs_unchanged=save_summary["jobs_unchanged"],
        duplicates_skipped=duplicates_skipped,
        jobs_saved=saved_jobs,
        suspicious_saved_rows=suspicious_saved_rows,
        location_scope_used=location_scope_used,
        keyword_scope_used=keyword_scope_used,
        source_metrics=source_metrics,
        routing_results=routing_results,
        artifacts=artifacts,
    )
