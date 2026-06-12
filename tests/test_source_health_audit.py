from __future__ import annotations

import csv

from reports.source_health_audit import (
    SOURCE_HEALTH_FIELDS,
    build_source_health_rows,
    classify_source_health_row,
    write_source_health_csv,
)


def test_build_source_health_rows_preserves_run_details() -> None:
    companies = [
        {
            "name": "TD",
            "sector": "Banking & Capital Markets",
            "category": "Bank/Market",
            "priority": "High",
            "status": "Watching",
            "source_mode": "human_in_loop",
            "website_category": "workday",
            "careers_url": "https://example.com/jobs",
            "ats_hint": "workday",
        }
    ]
    routing_results = [
        {
            "company_name": "TD",
            "source_name": "workday",
            "source_mode": "human_in_loop",
            "ats_type": "workday",
            "status": "completed",
            "jobs_discovered": 55,
            "jobs_scored": 50,
            "jobs_saved": 3,
            "jobs_inserted": 2,
            "jobs_updated": 1,
            "jobs_unchanged": 0,
            "duplicates_skipped": 5,
            "pages_visited": 10,
            "pagination_stop_reason": "max_pages_reached",
            "location_scope_used": True,
            "keyword_scope_used": False,
        }
    ]
    source_rows = [
        {
            "company_name": "TD",
            "source_name": "workday",
            "source_mode": "human_in_loop",
            "source_url": "https://example.com/jobs",
            "readiness_label": "ready_browser",
            "suggested_action": "Monitor normally.",
        }
    ]
    suspicious_saved_rows = [
        {
            "company_name": "TD",
            "title": "Careers Home",
        }
    ]

    rows = build_source_health_rows(
        companies=companies,
        routing_results=routing_results,
        source_rows=source_rows,
        suspicious_saved_rows=suspicious_saved_rows,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["company_name"] == "TD"
    assert row["candidates_discovered"] == 55
    assert row["candidates_scored"] == 50
    assert row["relevant_saved"] == 3
    assert row["pages_visited"] == 10
    assert row["pagination_stop_reason"] == "max_pages_reached"
    assert row["suspicious_saved_rows"] == 1


def test_classify_source_health_row_prioritizes_paused_sources() -> None:
    classification = classify_source_health_row(
        {
            "status": "paused",
            "source_mode": "browser_allowed",
            "intervention_reason": "login_required",
            "priority": "High",
        }
    )

    assert classification["issue_category"] == "paused_or_error"
    assert "sign-in" in classification["recommended_action"].lower()


def test_classify_source_health_row_flags_zero_discovery() -> None:
    classification = classify_source_health_row(
        {
            "status": "completed",
            "source_mode": "browser_allowed",
            "candidates_discovered": 0,
            "relevant_saved": 0,
            "priority": "Medium",
            "location_scope_used": True,
        }
    )

    assert classification["issue_category"] == "zero_discovery"


def test_classify_source_health_row_flags_high_discovery_zero_relevant() -> None:
    classification = classify_source_health_row(
        {
            "status": "completed",
            "source_mode": "browser_allowed",
            "candidates_discovered": 80,
            "relevant_saved": 0,
            "priority": "High",
            "location_scope_used": True,
        }
    )

    assert classification["issue_category"] == "high_discovery_zero_relevant"


def test_classify_source_health_row_flags_pagination_cap() -> None:
    classification = classify_source_health_row(
        {
            "status": "completed",
            "source_mode": "browser_allowed",
            "candidates_discovered": 12,
            "relevant_saved": 2,
            "pagination_stop_reason": "max_pages_reached",
            "priority": "High",
            "location_scope_used": True,
        }
    )

    assert classification["issue_category"] == "pagination_cap"


def test_classify_source_health_row_flags_needs_user_canada_url() -> None:
    classification = classify_source_health_row(
        {
            "status": "needs_user_canada_url",
            "source_mode": "browser_allowed",
            "source_scope_status": "needs_user_canada_url",
            "priority": "High",
        }
    )

    assert classification["issue_category"] == "needs_user_canada_url"


def test_classify_source_health_row_flags_unconfirmed_canada_scope() -> None:
    classification = classify_source_health_row(
        {
            "status": "canada_scope_unconfirmed",
            "source_mode": "browser_allowed",
            "source_scope_status": "canada_scope_unconfirmed",
            "priority": "High",
        }
    )

    assert classification["issue_category"] == "canada_scope_unconfirmed"


def test_write_source_health_csv_contains_required_columns(tmp_path) -> None:
    output_path = tmp_path / "source-health.csv"
    write_source_health_csv(
        output_path,
        [
            {
                "company_name": "TD",
                "source_url": "https://example.com/jobs",
                "source_mode": "human_in_loop",
                "ats_type": "workday",
                "status": "completed",
                "candidates_discovered": 10,
                "candidates_scored": 10,
                "relevant_saved": 2,
                "inserted": 1,
                "updated": 1,
                "unchanged": 0,
                "duplicates_skipped": 0,
                "pages_visited": 3,
                "pagination_stop_reason": "no_next_button",
                "intervention_reason": "",
                "suspicious_saved_rows": 0,
                "recommended_action": "Monitor normally.",
                "priority": "High",
            }
        ],
    )

    with output_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == SOURCE_HEALTH_FIELDS
        rows = list(reader)

    assert rows[0]["company_name"] == "TD"
