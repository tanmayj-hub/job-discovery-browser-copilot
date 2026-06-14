"""Export lightweight saved-job review artifacts for manual feedback."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

from dashboard.verified_view import (
    filter_jobs_to_verified_companies,
    filter_source_rows_to_verified_companies,
    parse_dashboard_timestamp,
)
from processing.score import score_job
from storage.db import get_jobs, get_source_status_rows
from verified_companies import (
    get_usable_verified_company_names,
    load_verified_company_records,
)

DEFAULT_REVIEW_EXPORT_PATH = Path("data/exports/review/saved-jobs-review.csv")
DEFAULT_VERIFIED_SNAPSHOT_PATH = Path("data/exports/review/latest-verified-saved-jobs.csv")
USER_DECISION_VALUES = (
    "useful",
    "maybe",
    "not_useful",
    "false_positive",
    "already_applied",
    "saved_for_later",
)
REVIEW_EXPORT_COLUMNS = [
    "company",
    "title",
    "location",
    "relevance_tier",
    "score",
    "job_url",
    "match_reasons",
    "first_seen",
    "last_seen",
    "user_decision",
    "user_notes",
]
SNAPSHOT_COLUMNS = [
    "company_name",
    "title",
    "location",
    "relevance_tier",
    "match_score",
    "job_url",
    "apply_url",
    "source_name",
    "source_mode",
    "match_reasons",
    "risk_flags",
    "first_seen",
    "last_seen",
    "status",
]


def _format_match_reasons(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple, set)):
        return " | ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _is_company_provisional(record: dict[str, Any]) -> bool:
    confidence = str(record.get("confidence") or "").strip().lower()
    notes = str(record.get("notes") or "").strip().lower()
    return confidence == "provisional" or "provisional" in notes


def _derive_relevance_tier(job: dict[str, Any]) -> str:
    existing = str(job.get("relevance_tier") or "").strip()
    if existing:
        return existing
    return score_job(job).relevance_tier


def _format_list_json(value: object) -> str:
    if value is None:
        return "[]"
    if isinstance(value, str):
        return json.dumps([item.strip() for item in value.split("|") if item.strip()])
    if isinstance(value, (list, tuple, set)):
        return json.dumps([str(item).strip() for item in value if str(item).strip()])
    return json.dumps([str(value).strip()])


def _parse_listish(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [item.strip() for item in text.split("|") if item.strip()]
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [str(parsed).strip()] if str(parsed).strip() else []


def _job_sort_key(job: dict[str, Any]) -> tuple[object, int, str, str]:
    timestamp = parse_dashboard_timestamp(job.get("last_seen_at") or job.get("last_seen"))
    return (
        timestamp or parse_dashboard_timestamp("1970-01-01T00:00:00Z"),
        int(job.get("match_score", 0) or 0),
        str(job.get("title") or "").strip().lower(),
        str(job.get("job_url") or "").strip().lower(),
    )


def _collect_review_export_companies(rows: list[dict[str, str]]) -> list[str]:
    return sorted({row["company"] for row in rows if row.get("company")})


def collect_review_export_companies(rows: list[dict[str, str]]) -> list[str]:
    """Return the sorted unique company names present in a review export."""

    return _collect_review_export_companies(rows)


def _serialize_snapshot_job(job: dict[str, Any]) -> dict[str, str]:
    return {
        "company_name": str(job.get("company_name") or "").strip(),
        "title": str(job.get("title") or "").strip(),
        "location": str(job.get("location") or "").strip(),
        "relevance_tier": _derive_relevance_tier(job),
        "match_score": str(int(job.get("match_score", 0) or 0)),
        "job_url": str(job.get("job_url") or "").strip(),
        "apply_url": str(job.get("apply_url") or "").strip(),
        "source_name": str(job.get("source_name") or "").strip(),
        "source_mode": str(job.get("source_mode") or "").strip(),
        "match_reasons": _format_list_json(job.get("match_reasons")),
        "risk_flags": _format_list_json(job.get("risk_flags")),
        "first_seen": str(job.get("first_seen_at") or job.get("first_seen") or "").strip(),
        "last_seen": str(job.get("last_seen_at") or job.get("last_seen") or "").strip(),
        "status": str(job.get("status") or "new").strip(),
    }


def write_verified_saved_jobs_snapshot(
    saved_jobs: list[dict[str, Any]],
    *,
    verified_companies_path: Path,
    output_path: Path = DEFAULT_VERIFIED_SNAPSHOT_PATH,
) -> list[dict[str, str]]:
    """Persist the latest verified-only saved-job snapshot for later review export."""

    verified_company_names = set(get_usable_verified_company_names(verified_companies_path))
    rows = [
        _serialize_snapshot_job(job)
        for job in saved_jobs
        if str(job.get("company_name") or "").strip() in verified_company_names
        and str(job.get("status") or "").strip() != "rejected"
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SNAPSHOT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def load_verified_saved_jobs_snapshot(path: Path) -> list[dict[str, Any]]:
    """Load a saved-job snapshot produced by a verified-only run."""

    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    jobs: list[dict[str, Any]] = []
    for row in rows:
        jobs.append(
            {
                "company_name": str(row.get("company_name") or "").strip(),
                "title": str(row.get("title") or "").strip(),
                "location": str(row.get("location") or "").strip() or None,
                "relevance_tier": str(row.get("relevance_tier") or "").strip(),
                "match_score": int(row.get("match_score", 0) or 0),
                "job_url": str(row.get("job_url") or "").strip() or None,
                "apply_url": str(row.get("apply_url") or "").strip() or None,
                "source_name": str(row.get("source_name") or "").strip() or None,
                "source_mode": str(row.get("source_mode") or "").strip() or None,
                "match_reasons": _parse_listish(row.get("match_reasons")),
                "risk_flags": _parse_listish(row.get("risk_flags")),
                "first_seen_at": str(row.get("first_seen") or "").strip() or None,
                "last_seen_at": str(row.get("last_seen") or "").strip() or None,
                "status": str(row.get("status") or "new").strip(),
            }
        )
    return jobs


def _build_current_verified_jobs_from_database(
    connection: sqlite3.Connection,
    *,
    verified_company_names: set[str],
) -> list[dict[str, Any]]:
    jobs = get_jobs(connection)
    source_rows = get_source_status_rows(connection)
    verified_jobs = filter_jobs_to_verified_companies(jobs, verified_company_names)
    verified_source_rows = filter_source_rows_to_verified_companies(
        source_rows,
        verified_company_names,
    )

    latest_source_by_company: dict[str, dict[str, Any]] = {}
    for row in verified_source_rows:
        company_name = str(row.get("company_name") or "").strip()
        if company_name not in verified_company_names:
            continue
        timestamp = parse_dashboard_timestamp(row.get("last_checked") or row.get("updated_at"))
        existing = latest_source_by_company.get(company_name)
        if existing is None:
            latest_source_by_company[company_name] = dict(row)
            latest_source_by_company[company_name]["_timestamp"] = timestamp
            continue
        existing_timestamp = existing.get("_timestamp")
        if timestamp is not None and (
            existing_timestamp is None or timestamp > existing_timestamp
        ):
            latest_source_by_company[company_name] = dict(row)
            latest_source_by_company[company_name]["_timestamp"] = timestamp

    filtered_jobs: list[dict[str, Any]] = []
    for company_name, source_row in latest_source_by_company.items():
        target_source_name = str(source_row.get("source_name") or "").strip()
        limit = int(source_row.get("jobs_saved", 0) or 0)
        if limit <= 0:
            continue
        company_jobs = [
            job
            for job in verified_jobs
            if str(job.get("company_name") or "").strip() == company_name
            and str(job.get("status") or "").strip() != "rejected"
        ]
        source_matched_jobs = [
            job
            for job in company_jobs
            if str(job.get("source_name") or "").strip() == target_source_name
        ]
        review_jobs = source_matched_jobs or company_jobs
        review_jobs = sorted(review_jobs, key=_job_sort_key, reverse=True)
        filtered_jobs.extend(review_jobs[:limit])
    return filtered_jobs


def build_saved_jobs_review_rows(
    connection: sqlite3.Connection,
    *,
    verified_companies_path: Path,
    saved_jobs_snapshot_path: Path = DEFAULT_VERIFIED_SNAPSHOT_PATH,
) -> list[dict[str, str]]:
    """Build review rows from the latest verified saved-job snapshot or DB fallback."""

    verified_company_names = set(get_usable_verified_company_names(verified_companies_path))
    if not verified_company_names:
        return []

    current_verified_jobs = load_verified_saved_jobs_snapshot(saved_jobs_snapshot_path)
    if current_verified_jobs:
        current_verified_jobs = [
            job
            for job in current_verified_jobs
            if str(job.get("company_name") or "").strip() in verified_company_names
            and str(job.get("status") or "").strip() != "rejected"
        ]
    else:
        current_verified_jobs = _build_current_verified_jobs_from_database(
            connection,
            verified_company_names=verified_company_names,
        )

    rows: list[dict[str, str]] = []
    for job in current_verified_jobs:
        if str(job.get("status") or "").strip() == "rejected":
            continue
        rows.append(
            {
                "company": str(job.get("company_name") or "").strip(),
                "title": str(job.get("title") or "").strip(),
                "location": str(job.get("location") or "").strip(),
                "relevance_tier": _derive_relevance_tier(job),
                "score": str(int(job.get("match_score", 0) or 0)),
                "job_url": str(job.get("job_url") or "").strip(),
                "match_reasons": _format_match_reasons(job.get("match_reasons")),
                "first_seen": str(job.get("first_seen_at") or job.get("first_seen") or "").strip(),
                "last_seen": str(job.get("last_seen_at") or job.get("last_seen") or "").strip(),
                "user_decision": "",
                "user_notes": "",
            }
        )
    return rows


def export_saved_jobs_review(
    connection: sqlite3.Connection,
    *,
    verified_companies_path: Path,
    output_path: Path,
    saved_jobs_snapshot_path: Path = DEFAULT_VERIFIED_SNAPSHOT_PATH,
) -> list[dict[str, str]]:
    """Write the latest verified saved-job review CSV and return exported rows."""

    rows = build_saved_jobs_review_rows(
        connection,
        verified_companies_path=verified_companies_path,
        saved_jobs_snapshot_path=saved_jobs_snapshot_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def build_saved_jobs_review_dashboard_rows(
    connection: sqlite3.Connection,
    *,
    verified_companies_path: Path,
    saved_jobs_snapshot_path: Path = DEFAULT_VERIFIED_SNAPSHOT_PATH,
) -> list[dict[str, str]]:
    """Build dashboard-friendly review rows with provisional flags."""

    verified_company_names = set(get_usable_verified_company_names(verified_companies_path))
    current_verified_jobs = load_verified_saved_jobs_snapshot(saved_jobs_snapshot_path)
    if current_verified_jobs:
        current_verified_jobs = [
            job
            for job in current_verified_jobs
            if str(job.get("company_name") or "").strip() in verified_company_names
            and str(job.get("status") or "").strip() != "rejected"
        ]
    else:
        current_verified_jobs = _build_current_verified_jobs_from_database(
            connection,
            verified_company_names=verified_company_names,
        )
    verified_records = {
        str(record.get("company_name") or "").strip(): record
        for record in load_verified_company_records(verified_companies_path)
    }
    dashboard_rows: list[dict[str, str]] = []
    for job in current_verified_jobs:
        company_name = str(job.get("company_name") or "").strip()
        record = verified_records.get(company_name, {})
        dashboard_rows.append(
            {
                "Company": company_name,
                "Provisional": "Yes" if _is_company_provisional(record) else "No",
                "Title": str(job.get("title") or "").strip(),
                "Location": str(job.get("location") or "").strip() or "-",
                "Relevance Tier": _derive_relevance_tier(job) or "-",
                "Score": str(int(job.get("match_score", 0) or 0)),
                "Job URL": str(job.get("job_url") or "").strip(),
                "Match Reasons": _format_match_reasons(job.get("match_reasons")) or "-",
                "Risk Flags": _format_match_reasons(job.get("risk_flags")) or "-",
            }
        )
    return dashboard_rows


def load_review_export_preview(path: Path) -> list[dict[str, Any]]:
    """Return the current review CSV rows for dashboard preview if it exists."""

    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def serialize_review_preview(rows: list[dict[str, Any]]) -> str:
    """Serialize a small preview safely for dashboards or logs."""

    return json.dumps(rows[:5], ensure_ascii=True)
