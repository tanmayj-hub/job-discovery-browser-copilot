from __future__ import annotations

from dashboard.source_status import filter_source_status_items, prepare_source_status_rows
from reports.source_observability import (
    build_source_remediation,
    compute_source_readiness,
    summarize_source_metrics,
)


def test_compute_source_readiness_maps_expected_states() -> None:
    assert (
        compute_source_readiness({"source_mode": "api_allowed", "status": "success"})
        == "ready_api"
    )
    assert (
        compute_source_readiness(
            {
                "source_mode": "browser_allowed",
                "status": "success",
                "collector": "static_jsonld",
            }
        )
        == "ready_static_jsonld"
    )
    assert (
        compute_source_readiness(
            {"source_mode": "browser_allowed", "status": "completed"}
        )
        == "ready_browser"
    )
    assert (
        compute_source_readiness({"source_mode": "human_in_loop", "status": "paused"})
        == "needs_human"
    )
    assert (
        compute_source_readiness(
            {
                "source_mode": "human_in_loop",
                "status": "completed",
                "collector": "browser",
                "intervention_required": False,
            }
        )
        == "ready_browser"
    )
    assert (
        compute_source_readiness(
            {"source_mode": "manual_only", "status": "manual_only"}
        )
        == "manual_only"
    )
    assert (
        compute_source_readiness({"source_mode": "needs_url", "status": "needs_url"})
        == "needs_url"
    )
    assert (
        compute_source_readiness(
            {"source_mode": "api_allowed", "status": "api_collector_not_implemented"}
        )
        == "api_not_implemented"
    )
    assert compute_source_readiness({"source_mode": "api_allowed", "status": "error"}) == "error"


def test_summarize_source_metrics_counts_collectors_and_fallbacks() -> None:
    metrics = summarize_source_metrics(
        [
            {
                "status": "success",
                "collector": "greenhouse_api",
                "jobs_discovered": 2,
                "jobs_scored": 2,
                "jobs_relevant": 1,
                "jobs_saved": 1,
                "jobs_inserted": 1,
            },
            {
                "status": "completed",
                "collector": "browser_fallback",
                "fallback_used": True,
                "intervention_required": True,
            },
            {
                "status": "api_collector_not_implemented",
                "collector": "api_not_implemented",
            },
            {
                "status": "manual_only",
                "collector": "manual_only",
            },
        ]
    )

    assert metrics["sources_checked"] == 4
    assert metrics["api_sources_used"] == 1
    assert metrics["browser_collector_used"] == 1
    assert metrics["browser_fallback_used"] == 1
    assert metrics["api_not_implemented"] == 1
    assert metrics["manual_only_skipped"] == 1
    assert metrics["interventions_required"] == 1
    assert metrics["jobs_discovered"] == 2


def test_build_source_remediation_prefers_pending_reason() -> None:
    remediation = build_source_remediation(
        {
            "source_mode": "browser_allowed",
            "status": "paused",
            "latest_pending_reason": "cookie_blocked",
        }
    )

    assert remediation["remediation_label"] == "cookie_banner"
    assert "blocking cookie banner" in remediation["suggested_action"]


def test_build_source_remediation_handles_manual_only_and_needs_url() -> None:
    manual_only = build_source_remediation(
        {
            "source_mode": "manual_only",
            "status": "manual_only",
        }
    )
    needs_url = build_source_remediation(
        {
            "source_mode": "needs_url",
            "status": "needs_url",
        }
    )

    assert manual_only["remediation_label"] == "manual_tracking"
    assert needs_url["remediation_label"] == "source_url_review"


def test_prepare_and_filter_source_status_rows() -> None:
    source_rows = [
        {
            "company_name": "API Co",
            "source_url": "https://jobs.api.example.com",
            "source_mode": "api_allowed",
            "ats_type": "greenhouse",
            "collector": "greenhouse_api",
            "status": "success",
            "fallback_used": False,
            "intervention_required": False,
            "jobs_discovered": 2,
            "jobs_relevant": 1,
            "jobs_saved": 1,
            "jobs_inserted": 1,
            "jobs_updated": 0,
            "jobs_unchanged": 0,
            "duplicates_skipped": 0,
            "pending_intervention_count": 0,
            "resolved_history_count": 0,
        },
        {
            "company_name": "Browser Co",
            "source_url": "https://careers.browser.example.com",
            "source_mode": "browser_allowed",
            "ats_type": "jsonld",
            "collector": "browser_fallback",
            "status": "completed",
            "fallback_used": True,
            "intervention_required": False,
            "pending_intervention_count": 1,
            "resolved_history_count": 2,
            "latest_pending_reason": "extraction_failed",
        },
    ]

    rows = prepare_source_status_rows(source_rows)
    filtered = filter_source_status_items(
        source_rows,
        selected_source_mode="browser_allowed",
        selected_ats_type="All",
        selected_collector="browser_fallback",
        selected_status="completed",
        selected_fallback="Yes",
        selected_intervention="No",
    )

    assert rows[0]["Readiness"] == "ready_api"
    assert rows[1]["Fallback Used"] is True
    assert rows[1]["Pending Interventions"] == 1
    assert rows[1]["Resolved History"] == 2
    assert rows[1]["Remediation"] == "extraction_review"
    assert filtered == [source_rows[1]]
