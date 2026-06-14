"""Export lightweight saved-job review artifacts for manual feedback."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

from dashboard.verified_view import (
    filter_jobs_to_latest_verified_run,
    filter_jobs_to_verified_companies,
    filter_source_rows_to_verified_companies,
)
from processing.score import score_job
from storage.db import get_jobs, get_source_status_rows
from verified_companies import (
    get_usable_verified_company_names,
    load_verified_company_records,
)

DEFAULT_REVIEW_EXPORT_PATH = Path("data/exports/review/saved-jobs-review.csv")
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


def build_saved_jobs_review_rows(
    connection: sqlite3.Connection,
    *,
    verified_companies_path: Path,
) -> list[dict[str, str]]:
    """Build review rows from the latest verified-run saved jobs."""

    verified_company_names = set(get_usable_verified_company_names(verified_companies_path))
    if not verified_company_names:
        return []

    jobs = get_jobs(connection)
    source_rows = get_source_status_rows(connection)
    verified_jobs = filter_jobs_to_verified_companies(jobs, verified_company_names)
    verified_source_rows = filter_source_rows_to_verified_companies(
        source_rows,
        verified_company_names,
    )
    current_verified_jobs = filter_jobs_to_latest_verified_run(
        verified_jobs,
        verified_source_rows,
        verified_company_names,
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
) -> list[dict[str, str]]:
    """Write the latest verified saved-job review CSV and return exported rows."""

    rows = build_saved_jobs_review_rows(
        connection,
        verified_companies_path=verified_companies_path,
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
) -> list[dict[str, str]]:
    """Build dashboard-friendly review rows with provisional flags."""

    exported_rows = build_saved_jobs_review_rows(
        connection,
        verified_companies_path=verified_companies_path,
    )
    verified_records = {
        str(record.get("company_name") or "").strip(): record
        for record in load_verified_company_records(verified_companies_path)
    }
    dashboard_rows: list[dict[str, str]] = []
    for row in exported_rows:
        record = verified_records.get(row["company"], {})
        dashboard_rows.append(
            {
                "Company": row["company"],
                "Provisional": "Yes" if _is_company_provisional(record) else "No",
                "Title": row["title"],
                "Location": row["location"] or "-",
                "Relevance Tier": row["relevance_tier"] or "-",
                "Score": row["score"],
                "Job URL": row["job_url"] or "",
                "Match Reasons": row["match_reasons"] or "-",
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
