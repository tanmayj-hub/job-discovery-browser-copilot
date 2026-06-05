"""Helpers for source-level observability across reports and dashboard views."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

SUCCESS_STATUSES = {"success", "completed", "no_jobs_found"}
ERROR_STATUSES = {"error", "api_error", "parse_error", "unsupported_source_mode"}
SKIPPED_STATUSES = {
    "manual_only",
    "needs_url",
    "api_collector_not_implemented",
    "avoid",
    "skipped",
}
API_COLLECTORS = {"greenhouse_api", "lever_api", "ashby_api"}
BROWSER_COLLECTORS = {"browser", "browser_after_jsonld", "browser_fallback"}

REMEDIATION_BY_REASON = {
    "login_required": (
        "login_required",
        "Open the public careers URL manually and confirm whether sign-in is mandatory. "
        "If login is required for job listings, keep the source manual-only.",
    ),
    "captcha_detected": (
        "captcha_pause",
        "Do not bypass CAPTCHA. Review the source manually and either mark it resolved "
        "after the public page is usable or keep it manual-only.",
    ),
    "cookie_blocked": (
        "cookie_banner",
        "Open the source, clear or accept the blocking cookie banner, then rerun the source.",
    ),
    "location_selection_required": (
        "location_gate",
        "Select the Canada or local region manually, then rerun the source.",
    ),
    "unclear_layout": (
        "layout_review",
        "Open the source manually and identify the public careers results page before another run.",
    ),
    "extraction_failed": (
        "extraction_review",
        "Review the page manually to confirm whether selectors need updating or the source "
        "should stay manual-only.",
    ),
}


def is_success_status(status: object) -> bool:
    """Return True when a source outcome represents a successful check."""

    return str(status or "").strip() in SUCCESS_STATUSES


def is_error_status(status: object) -> bool:
    """Return True when a source outcome should be treated as an error."""

    return str(status or "").strip() in ERROR_STATUSES


def is_skipped_status(status: object) -> bool:
    """Return True when a source outcome is an intentional skip or non-run."""

    return str(status or "").strip() in SKIPPED_STATUSES


def compute_source_readiness(source: Mapping[str, Any]) -> str:
    """Map source execution state into a human-readable readiness label."""

    status = str(source.get("status") or source.get("last_status") or "").strip()
    source_mode = str(source.get("source_mode") or "").strip()
    collector = str(source.get("collector") or source.get("last_collector") or "").strip()
    intervention_required = bool(source.get("intervention_required", False))

    if is_error_status(status):
        return "error"
    if status == "api_collector_not_implemented":
        return "api_not_implemented"
    if status == "needs_url" or source_mode == "needs_url":
        return "needs_url"
    if status == "manual_only" or source_mode == "manual_only":
        return "manual_only"
    if status == "paused" or intervention_required:
        return "needs_human"
    if collector == "static_jsonld" and is_success_status(status):
        return "ready_static_jsonld"
    if collector in BROWSER_COLLECTORS and is_success_status(status):
        return "ready_browser"
    if source_mode == "api_allowed":
        return "ready_api"
    if source_mode == "browser_allowed":
        return "ready_browser"
    return "needs_human" if source_mode == "human_in_loop" else "ready_browser"


def build_source_remediation(source: Mapping[str, Any]) -> dict[str, str]:
    """Return a stable remediation label and suggested action for a source or intervention."""

    reason = str(
        source.get("latest_pending_reason")
        or source.get("reason")
        or source.get("intervention_reason")
        or ""
    ).strip()
    status = str(source.get("status") or source.get("last_status") or "").strip()
    source_mode = str(source.get("source_mode") or "").strip()
    readiness = str(
        source.get("readiness_label") or compute_source_readiness(source)
    ).strip()

    if reason in REMEDIATION_BY_REASON:
        label, action = REMEDIATION_BY_REASON[reason]
        return {"remediation_label": label, "suggested_action": action}

    if readiness == "needs_url" or status == "needs_url" or source_mode == "needs_url":
        return {
            "remediation_label": "source_url_review",
            "suggested_action": (
                "Add or correct the public careers URL, then reclassify the source."
            ),
        }
    if readiness == "manual_only" or status == "manual_only" or source_mode == "manual_only":
        return {
            "remediation_label": "manual_tracking",
            "suggested_action": (
                "Keep this source in manual-only mode and use manual job entry when relevant "
                "roles appear."
            ),
        }
    if readiness == "api_not_implemented" or status == "api_collector_not_implemented":
        return {
            "remediation_label": "api_pending",
            "suggested_action": (
                "Keep this source paused for now or use a safe public browser path only after "
                "manual review."
            ),
        }
    if readiness == "error" or is_error_status(status):
        return {
            "remediation_label": "source_error",
            "suggested_action": (
                "Review the latest source error and rerun only after the public page is reachable."
            ),
        }
    if readiness == "needs_human" or status == "paused":
        return {
            "remediation_label": "human_review",
            "suggested_action": (
                "Open the source manually, resolve the blocker, and rerun when the "
                "public flow is clear."
            ),
        }
    if is_success_status(status):
        return {
            "remediation_label": "monitor_only",
            "suggested_action": (
                "No remediation needed. Keep the source in the normal monitoring cycle."
            ),
        }
    return {
        "remediation_label": "review_needed",
        "suggested_action": "Review this source manually before the next run.",
    }


def summarize_source_metrics(sources: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """Return aggregate source-routing metrics for reports and dashboard cards."""

    items = list(sources)
    collectors = Counter(
        str(item.get("collector") or item.get("last_collector") or "")
        for item in items
    )
    statuses = Counter(
        str(item.get("status") or item.get("last_status") or "")
        for item in items
    )

    return {
        "sources_checked": len(items),
        "sources_skipped": sum(
            1
            for item in items
            if is_skipped_status(item.get("status") or item.get("last_status"))
        ),
        "api_sources_used": sum(collectors[name] for name in API_COLLECTORS),
        "static_jsonld_used": collectors["static_jsonld"],
        "browser_collector_used": sum(collectors[name] for name in BROWSER_COLLECTORS),
        "browser_fallback_used": sum(1 for item in items if bool(item.get("fallback_used", False))),
        "api_not_implemented": statuses["api_collector_not_implemented"],
        "manual_only_skipped": statuses["manual_only"],
        "needs_url_skipped": statuses["needs_url"],
        "interventions_required": sum(
            1 for item in items if bool(item.get("intervention_required", False))
        ),
        "errors": sum(
            1
            for item in items
            if is_error_status(item.get("status") or item.get("last_status"))
        ),
        "jobs_discovered": sum(int(item.get("jobs_discovered", 0) or 0) for item in items),
        "jobs_scored": sum(int(item.get("jobs_scored", 0) or 0) for item in items),
        "jobs_relevant": sum(int(item.get("jobs_relevant", 0) or 0) for item in items),
        "jobs_saved": sum(int(item.get("jobs_saved", 0) or 0) for item in items),
        "jobs_inserted": sum(int(item.get("jobs_inserted", 0) or 0) for item in items),
        "jobs_updated": sum(int(item.get("jobs_updated", 0) or 0) for item in items),
        "jobs_unchanged": sum(int(item.get("jobs_unchanged", 0) or 0) for item in items),
        "duplicates_skipped": sum(int(item.get("duplicates_skipped", 0) or 0) for item in items),
    }
