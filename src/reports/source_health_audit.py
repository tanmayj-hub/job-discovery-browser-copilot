"""Source-health audit helpers for full watchlist diagnostics."""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from reports.source_observability import build_source_remediation, is_error_status

SOURCE_HEALTH_FIELDS = [
    "company_name",
    "source_url",
    "source_url_used",
    "source_mode",
    "ats_type",
    "status",
    "source_scope_status",
    "source_scope_confirmed",
    "source_scope_method",
    "source_scope_reason",
    "candidates_discovered",
    "candidates_scored",
    "relevant_saved",
    "non_canada_rejected",
    "unknown_location_relevant",
    "inserted",
    "updated",
    "unchanged",
    "duplicates_skipped",
    "pages_visited",
    "pagination_stop_reason",
    "intervention_reason",
    "suspicious_saved_rows",
    "recommended_action",
    "priority",
]
SUCCESS_STATUSES = {"completed", "success", "no_jobs_found"}


def _source_key(company_name: object, source_name: object) -> tuple[str, str]:
    return (
        str(company_name or "").strip(),
        str(source_name or "").strip(),
    )


def _priority_rank(priority: object) -> int:
    normalized = str(priority or "").strip().lower()
    if normalized == "high":
        return 0
    if normalized == "medium":
        return 1
    if normalized == "low":
        return 2
    return 3


def _pages_visited_count(value: object) -> int:
    if isinstance(value, list):
        return len(value)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def classify_source_health_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Classify one source-health row into a stable issue bucket."""

    status = str(row.get("status") or "").strip()
    source_mode = str(row.get("source_mode") or "").strip()
    candidates_discovered = int(row.get("candidates_discovered", 0) or 0)
    relevant_saved = int(row.get("relevant_saved", 0) or 0)
    suspicious_saved_rows = int(row.get("suspicious_saved_rows", 0) or 0)
    pagination_stop_reason = str(row.get("pagination_stop_reason") or "").strip()
    intervention_reason = str(row.get("intervention_reason") or "").strip()
    location_scope_used = bool(row.get("location_scope_used", False))
    source_scope_status = str(row.get("source_scope_status") or "").strip()
    source_scope_confirmed = bool(row.get("source_scope_confirmed", False))
    remediation = build_source_remediation(row)

    issue_category = "monitor"
    recommended_action = "Monitor normally."
    attention_score = 10

    if source_mode == "needs_url" or status == "needs_url":
        issue_category = "source_url_fix"
        recommended_action = (
            "Add or correct the public careers URL, then reclassify the source."
        )
        attention_score = 100
    elif source_mode == "manual_only" or status == "manual_only":
        issue_category = "manual_tracking"
        recommended_action = remediation["suggested_action"]
        attention_score = 40
    elif status == "paused" or is_error_status(status) or intervention_reason:
        issue_category = "paused_or_error"
        recommended_action = remediation["suggested_action"]
        attention_score = 95
    elif source_scope_status == "needs_user_canada_url":
        issue_category = "needs_user_canada_url"
        recommended_action = remediation["suggested_action"]
        attention_score = 92
    elif source_scope_status in {"canada_scope_unconfirmed", "filter_blocked"}:
        issue_category = "canada_scope_unconfirmed"
        recommended_action = remediation["suggested_action"]
        attention_score = 90
    elif candidates_discovered == 0 and status in SUCCESS_STATUSES:
        issue_category = "zero_discovery"
        recommended_action = (
            "Review the public careers flow and Canada scoping because the run "
            "completed with zero discovered jobs."
        )
        attention_score = 85
    elif candidates_discovered >= 25 and relevant_saved == 0 and status in SUCCESS_STATUSES:
        issue_category = "high_discovery_zero_relevant"
        recommended_action = (
            "Review collected candidates against scoring and normalization for this "
            "source because many jobs were seen but none were saved as relevant."
        )
        attention_score = 80
    elif suspicious_saved_rows > 0:
        issue_category = "suspicious_saved_rows"
        recommended_action = (
            "Manually review suspicious saved rows for false positives before trusting "
            "this source output."
        )
        attention_score = 75
    elif pagination_stop_reason == "max_pages_reached":
        issue_category = "pagination_cap"
        recommended_action = (
            "Consider a manual audit or a per-company page-cap override if relevant "
            "jobs may exist beyond the current safe pagination limit."
        )
        attention_score = 65
    elif status in SUCCESS_STATUSES and (not location_scope_used or not source_scope_confirmed):
        issue_category = "broad_scope_limit"
        recommended_action = (
            "This source did not confirm Canada-only scoping in the automated flow. "
            "Prefer a stable Canada-filtered source URL if one exists, otherwise "
            "document the broad-listing limitation."
        )
        attention_score = 60

    attention_score += max(0, 3 - _priority_rank(row.get("priority"))) * 5
    return {
        "issue_category": issue_category,
        "recommended_action": recommended_action,
        "attention_score": attention_score,
    }


def build_source_health_rows(
    *,
    companies: Sequence[Mapping[str, Any]],
    routing_results: Sequence[Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]],
    suspicious_saved_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build stable source-health rows from the latest full-run inputs."""

    routing_by_key = {
        _source_key(item.get("company_name"), item.get("source_name")): dict(item)
        for item in routing_results
    }
    source_by_key = {
        _source_key(item.get("company_name"), item.get("source_name")): dict(item)
        for item in source_rows
    }
    suspicious_counts = Counter(
        str(item.get("company_name") or "").strip()
        for item in suspicious_saved_rows
        if str(item.get("company_name") or "").strip()
    )

    rows: list[dict[str, Any]] = []
    for watchlist_order, company in enumerate(companies, start=1):
        source_name = str(company.get("website_category") or company.get("name") or "")
        key = _source_key(company.get("name"), source_name)
        routing = routing_by_key.get(key, {})
        source_row = source_by_key.get(key, {})

        row = {
            "company_name": str(company.get("name") or ""),
            "watchlist_order": watchlist_order,
            "sector": company.get("sector") or source_row.get("sector"),
            "category": company.get("category") or source_row.get("category"),
            "priority": company.get("priority") or source_row.get("priority"),
            "source_name": source_name,
            "source_url": (
                routing.get("source_url")
                or source_row.get("source_url")
                or company.get("careers_url")
            ),
            "source_url_used": (
                routing.get("source_url_used")
                or source_row.get("source_url_used")
                or routing.get("source_url")
                or source_row.get("source_url")
                or company.get("careers_url")
            ),
            "source_mode": (
                routing.get("source_mode")
                or source_row.get("source_mode")
                or company.get("source_mode")
            ),
            "ats_type": (
                routing.get("ats_type")
                or source_row.get("ats_type")
                or company.get("ats_type")
                or company.get("ats_hint")
            ),
            "collector": routing.get("collector") or source_row.get("collector"),
            "status": routing.get("status") or source_row.get("status") or "not_run",
            "readiness_label": (
                source_row.get("readiness_label")
                or routing.get("readiness_label")
                or "unknown"
            ),
            "candidates_discovered": int(
                routing.get("jobs_discovered")
                or source_row.get("jobs_discovered")
                or 0
            ),
            "candidates_scored": int(
                routing.get("jobs_scored")
                or source_row.get("jobs_scored")
                or 0
            ),
            "relevant_saved": int(
                routing.get("jobs_saved")
                or source_row.get("jobs_saved")
                or 0
            ),
            "source_scope_status": (
                routing.get("source_scope_status")
                or source_row.get("source_scope_status")
            ),
            "source_scope_confirmed": bool(
                routing.get(
                    "source_scope_confirmed",
                    source_row.get("source_scope_confirmed", False),
                )
            ),
            "source_scope_method": (
                routing.get("source_scope_method")
                or source_row.get("source_scope_method")
            ),
            "source_scope_reason": (
                routing.get("source_scope_reason")
                or source_row.get("source_scope_reason")
            ),
            "inserted": int(
                routing.get("jobs_inserted")
                or source_row.get("jobs_inserted")
                or 0
            ),
            "updated": int(
                routing.get("jobs_updated")
                or source_row.get("jobs_updated")
                or 0
            ),
            "unchanged": int(
                routing.get("jobs_unchanged")
                or source_row.get("jobs_unchanged")
                or 0
            ),
            "duplicates_skipped": int(
                routing.get("duplicates_skipped")
                or source_row.get("duplicates_skipped")
                or 0
            ),
            "non_canada_rejected": int(
                routing.get("non_canada_rejected")
                or source_row.get("non_canada_rejected")
                or 0
            ),
            "unknown_location_relevant": int(
                routing.get("unknown_location_relevant")
                or source_row.get("unknown_location_relevant")
                or 0
            ),
            "pages_visited": _pages_visited_count(routing.get("pages_visited")),
            "pagination_stop_reason": routing.get("pagination_stop_reason"),
            "intervention_reason": (
                routing.get("intervention_reason")
                or source_row.get("latest_pending_reason")
            ),
            "suspicious_saved_rows": suspicious_counts.get(
                str(company.get("name") or "").strip(),
                0,
            ),
            "fallback_used": bool(
                routing.get("fallback_used", source_row.get("fallback_used", False))
            ),
            "location_scope_used": bool(routing.get("location_scope_used", False)),
            "keyword_scope_used": bool(routing.get("keyword_scope_used", False)),
            "error": routing.get("error") or source_row.get("error"),
            "suggested_action": source_row.get("suggested_action"),
            "remediation_label": source_row.get("remediation_label"),
            "company_status": company.get("status") or source_row.get("company_status"),
        }
        row.update(classify_source_health_row(row))
        rows.append(row)

    rows.sort(
        key=lambda item: (
            -int(item.get("attention_score", 0) or 0),
            _priority_rank(item.get("priority")),
            int(item.get("watchlist_order", 9999) or 9999),
            str(item.get("company_name") or ""),
        )
    )
    return rows


def select_top_attention_sources(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    return [dict(row) for row in list(rows)[:limit]]


def select_zero_discovery_sources(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in rows
        if str(row.get("issue_category") or "") == "zero_discovery"
    ]


def select_high_discovery_zero_relevant_sources(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in rows
        if str(row.get("issue_category") or "") == "high_discovery_zero_relevant"
    ]


def select_paused_or_error_sources(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in rows
        if str(row.get("issue_category") or "") == "paused_or_error"
    ]


def select_pagination_cap_sources(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in rows
        if str(row.get("pagination_stop_reason") or "") == "max_pages_reached"
    ]


def select_source_url_remediation_candidates(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in rows
        if str(row.get("issue_category") or "") in {"source_url_fix", "broad_scope_limit"}
    ]


def select_next_manual_audit_candidates(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    base_candidates = [
        dict(row)
        for row in rows
        if str(row.get("status") or "") in SUCCESS_STATUSES
        and str(row.get("source_mode") or "") not in {"manual_only", "needs_url", "avoid"}
        and (
            int(row.get("suspicious_saved_rows", 0) or 0) > 0
            or str(row.get("issue_category") or "")
            in {
                "zero_discovery",
                "high_discovery_zero_relevant",
                "pagination_cap",
                "broad_scope_limit",
            }
        )
    ]
    zero_discovery_human_in_loop = [
        row
        for row in base_candidates
        if str(row.get("issue_category") or "") == "zero_discovery"
        and str(row.get("source_mode") or "") == "human_in_loop"
    ]
    zero_discovery_human_in_loop.sort(
        key=lambda item: (
            -int(item.get("attention_score", 0) or 0),
            _priority_rank(item.get("priority")),
            int(item.get("watchlist_order", 9999) or 9999),
            -int(item.get("candidates_discovered", 0) or 0),
            str(item.get("company_name") or ""),
        )
    )

    pagination_candidates = [
        row
        for row in base_candidates
        if str(row.get("issue_category") or "") == "pagination_cap"
        and int(row.get("candidates_discovered", 0) or 0) >= 100
    ]
    pagination_candidates.sort(
        key=lambda item: (
            _priority_rank(item.get("priority")),
            int(item.get("watchlist_order", 9999) or 9999),
            -int(item.get("candidates_discovered", 0) or 0),
            str(item.get("company_name") or ""),
        )
    )

    general_candidates = list(base_candidates)
    general_candidates.sort(
        key=lambda item: (
            -int(item.get("attention_score", 0) or 0),
            _priority_rank(item.get("priority")),
            int(item.get("watchlist_order", 9999) or 9999),
            -int(item.get("candidates_discovered", 0) or 0),
            str(item.get("company_name") or ""),
        )
    )

    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add_rows(candidates: Sequence[Mapping[str, Any]], max_to_add: int | None = None) -> None:
        added = 0
        for candidate in candidates:
            key = _source_key(candidate.get("company_name"), candidate.get("source_name"))
            if key in seen:
                continue
            selected.append(dict(candidate))
            seen.add(key)
            added += 1
            if max_to_add is not None and added >= max_to_add:
                break

    add_rows(zero_discovery_human_in_loop, max_to_add=2)
    add_rows(pagination_candidates, max_to_add=3)
    if len(selected) < limit:
        add_rows(general_candidates)
    return selected[:limit]


def write_source_health_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    """Write the machine-readable full source-health export."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SOURCE_HEALTH_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in SOURCE_HEALTH_FIELDS})


def _render_company_table(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    lines = [
        (
            "| Company | Source URL | Used URL | Mode | ATS | Status | Scope | "
            "Method | Pages | Candidates | Scored | Relevant Saved | Non-Canada "
            "Rejected | Inserted | Updated | Unchanged | Pagination Stop | "
            "Intervention | Suspicious | Recommended Action |"
        ),
        (
            "| --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | "
            "---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |"
        ),
    ]
    for row in rows:
        lines.append(
            f"| {row.get('company_name') or '-'} | {row.get('source_url') or '-'} | "
            f"{row.get('source_url_used') or '-'} | {row.get('source_mode') or '-'} | "
            f"{row.get('ats_type') or '-'} | {row.get('status') or '-'} | "
            f"{row.get('source_scope_status') or '-'} | {row.get('source_scope_method') or '-'} | "
            f"{int(row.get('pages_visited', 0) or 0)} | "
            f"{int(row.get('candidates_discovered', 0) or 0)} | "
            f"{int(row.get('candidates_scored', 0) or 0)} | "
            f"{int(row.get('relevant_saved', 0) or 0)} | "
            f"{int(row.get('non_canada_rejected', 0) or 0)} | "
            f"{int(row.get('inserted', 0) or 0)} | "
            f"{int(row.get('updated', 0) or 0)} | "
            f"{int(row.get('unchanged', 0) or 0)} | "
            f"{row.get('pagination_stop_reason') or '-'} | "
            f"{row.get('intervention_reason') or '-'} | "
            f"{int(row.get('suspicious_saved_rows', 0) or 0)} | "
            f"{row.get('recommended_action') or '-'} |"
        )
    return lines


def _render_issue_list(rows: Sequence[Mapping[str, Any]], *, show_reason: bool = True) -> list[str]:
    if not rows:
        return ["- None"]
    rendered: list[str] = []
    for row in rows:
        reason = f" | issue={row.get('issue_category')}" if show_reason else ""
        candidates = int(row.get("candidates_discovered", 0) or 0)
        saved = int(row.get("relevant_saved", 0) or 0)
        rendered.append(
            f"- {row.get('company_name') or '-'} | status={row.get('status') or '-'} | "
            f"mode={row.get('source_mode') or '-'} | candidates={candidates} | "
            f"saved={saved}{reason} | "
            f"{row.get('recommended_action') or '-'}"
        )
    return rendered


def write_source_health_report(
    path: Path,
    *,
    run_date: str,
    rows: Sequence[Mapping[str, Any]],
    run_summary: Mapping[str, Any],
    source_scope_locations: Sequence[str],
    max_pages_per_source: int,
) -> None:
    """Write the full source-health Markdown audit report."""

    path.parent.mkdir(parents=True, exist_ok=True)

    completed = sum(1 for row in rows if str(row.get("status") or "") == "completed")
    paused = sum(1 for row in rows if str(row.get("status") or "") == "paused")
    errors = sum(1 for row in rows if is_error_status(row.get("status")))
    manual_only = sum(1 for row in rows if str(row.get("status") or "") == "manual_only")
    needs_url = sum(1 for row in rows if str(row.get("status") or "") == "needs_url")
    top_attention = select_top_attention_sources(rows, limit=10)
    zero_discovery = select_zero_discovery_sources(rows)
    high_discovery_zero_relevant = select_high_discovery_zero_relevant_sources(rows)
    paused_or_error = select_paused_or_error_sources(rows)
    pagination_caps = select_pagination_cap_sources(rows)
    source_url_candidates = select_source_url_remediation_candidates(rows)
    next_manual_audit = select_next_manual_audit_candidates(rows, limit=5)

    lines = [
        "# Full 43-Company Source Health Audit",
        "",
        "## Executive Summary",
        f"- Run date: {run_date}",
        f"- Configured companies reviewed: {len(rows)}",
        (
            "- Companies checked in the run: "
            f"{int(run_summary.get('companies_checked_count', 0) or 0)}"
        ),
        f"- Completed sources: {completed}",
        f"- Paused sources: {paused}",
        f"- Error sources: {errors}",
        f"- Manual-only sources: {manual_only}",
        f"- Needs-URL sources: {needs_url}",
        f"- Jobs discovered: {int(run_summary.get('jobs_discovered', 0) or 0)}",
        f"- Jobs scored: {int(run_summary.get('jobs_scored', 0) or 0)}",
        f"- Relevant jobs saved: {int(run_summary.get('jobs_saved', 0) or 0)}",
        f"- Pending interventions: {int(run_summary.get('interventions_needed', 0) or 0)}",
        f"- Suspicious saved rows: {int(run_summary.get('suspicious_saved_rows', 0) or 0)}",
        "",
        "## Run Configuration",
        f"- Active collection scope: {', '.join(source_scope_locations)}",
        "- Canada-only scope confirmed: yes",
        "- City/province/remote filters used globally: no",
        f"- Max pages per source: {max_pages_per_source}",
        (
            "- Keyword fallback used before extraction: "
            f"{bool(run_summary.get('keyword_scope_used', False))}"
        ),
        "- Relevance tiers confirmed: `core_target_fit`, `adjacent_customer_facing_technical_fit`",
        "",
        "## Overall Metrics",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Configured companies | {len(rows)} |",
        f"| Companies checked | {int(run_summary.get('companies_checked_count', 0) or 0)} |",
        f"| Completed | {completed} |",
        f"| Paused | {paused} |",
        f"| Errors | {errors} |",
        f"| Manual-only | {manual_only} |",
        f"| Needs-URL | {needs_url} |",
        f"| Jobs discovered | {int(run_summary.get('jobs_discovered', 0) or 0)} |",
        f"| Jobs scored | {int(run_summary.get('jobs_scored', 0) or 0)} |",
        f"| Relevant saved | {int(run_summary.get('jobs_saved', 0) or 0)} |",
        f"| Jobs inserted | {int(run_summary.get('jobs_inserted', 0) or 0)} |",
        f"| Jobs updated | {int(run_summary.get('jobs_updated', 0) or 0)} |",
        f"| Jobs unchanged | {int(run_summary.get('jobs_unchanged', 0) or 0)} |",
        f"| Duplicates skipped | {int(run_summary.get('duplicates_skipped', 0) or 0)} |",
        "",
        "## Company-By-Company Source Table",
    ]
    lines.extend(_render_company_table(rows))

    lines.extend(["", "## Top 10 Companies Needing Attention"])
    lines.extend(_render_issue_list(top_attention))

    lines.extend(["", "## Zero-Discovery Companies"])
    lines.extend(_render_issue_list(zero_discovery, show_reason=False))

    lines.extend(["", "## High-Discovery / Zero-Relevant Companies"])
    lines.extend(_render_issue_list(high_discovery_zero_relevant, show_reason=False))

    lines.extend(["", "## Paused Or Error Companies"])
    lines.extend(_render_issue_list(paused_or_error))

    lines.extend(["", "## Pagination-Cap Companies"])
    lines.extend(_render_issue_list(pagination_caps, show_reason=False))

    lines.extend(["", "## Source URL Remediation Candidates"])
    lines.extend(_render_issue_list(source_url_candidates, show_reason=False))

    lines.extend(["", "## Recommended Next Manual Audit Slice"])
    if next_manual_audit:
        for row in next_manual_audit:
            candidates = int(row.get("candidates_discovered", 0) or 0)
            saved = int(row.get("relevant_saved", 0) or 0)
            lines.append(
                f"- {row.get('company_name') or '-'} | priority={row.get('priority') or '-'} | "
                f"status={row.get('status') or '-'} | candidates={candidates} | "
                f"saved={saved} | "
                f"reason={row.get('issue_category') or '-'}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Notes"])
    lines.append(
        "- The first 3-company manual URL audit reports remain unchanged and are still the "
        "authoritative manual-recall audit artifacts."
    )
    lines.append(
        "- This report focuses on source health, run behavior, and next debugging priorities "
        "across the configured 43-company watchlist."
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
