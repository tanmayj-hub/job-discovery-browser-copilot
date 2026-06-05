"""Dashboard helpers for source readiness and collector-status views."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from reports.source_observability import compute_source_readiness


def prepare_source_status_rows(sources: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert persisted source rows into dashboard-friendly records."""

    rows: list[dict[str, Any]] = []
    for source in sources:
        rows.append(
            {
                "Company": source.get("company_name") or "-",
                "Source URL": source.get("source_url") or "-",
                "Source Mode": source.get("source_mode") or "-",
                "ATS Type": source.get("ats_type") or "-",
                "Collector": source.get("collector") or source.get("last_collector") or "-",
                "Status": source.get("status") or source.get("last_status") or "-",
                "Readiness": source.get("readiness_label") or compute_source_readiness(source),
                "Fallback Used": bool(source.get("fallback_used", False)),
                "Intervention Required": bool(source.get("intervention_required", False)),
                "Jobs Discovered": int(source.get("jobs_discovered", 0) or 0),
                "Jobs Relevant": int(source.get("jobs_relevant", 0) or 0),
                "Jobs Saved": int(source.get("jobs_saved", 0) or 0),
                "Jobs Inserted": int(source.get("jobs_inserted", 0) or 0),
                "Jobs Updated": int(source.get("jobs_updated", 0) or 0),
                "Jobs Unchanged": int(source.get("jobs_unchanged", 0) or 0),
                "Duplicates Skipped": int(source.get("duplicates_skipped", 0) or 0),
                "Last Error": source.get("error") or source.get("last_error") or "-",
                "Last Success": source.get("last_success_at") or "-",
                "Consecutive Failures": int(source.get("consecutive_failures", 0) or 0),
            }
        )
    return rows


def filter_source_status_items(
    sources: Iterable[dict[str, Any]],
    *,
    selected_source_mode: str,
    selected_ats_type: str,
    selected_collector: str,
    selected_status: str,
    selected_fallback: str,
    selected_intervention: str,
) -> list[dict[str, Any]]:
    """Apply dashboard filters to source status records."""

    filtered: list[dict[str, Any]] = []
    for source in sources:
        source_mode = str(source.get("source_mode") or "-")
        ats_type = str(source.get("ats_type") or "-")
        collector = str(source.get("collector") or source.get("last_collector") or "-")
        status = str(source.get("status") or source.get("last_status") or "-")
        fallback_used = bool(source.get("fallback_used", False))
        intervention_required = bool(source.get("intervention_required", False))

        if selected_source_mode != "All" and source_mode != selected_source_mode:
            continue
        if selected_ats_type != "All" and ats_type != selected_ats_type:
            continue
        if selected_collector != "All" and collector != selected_collector:
            continue
        if selected_status != "All" and status != selected_status:
            continue
        if selected_fallback == "Yes" and not fallback_used:
            continue
        if selected_fallback == "No" and fallback_used:
            continue
        if selected_intervention == "Yes" and not intervention_required:
            continue
        if selected_intervention == "No" and intervention_required:
            continue
        filtered.append(source)
    return filtered
