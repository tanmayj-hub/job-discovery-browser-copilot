"""Read-only helpers for the verified-company dashboard workflow."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def filter_jobs_to_verified_companies(
    jobs: list[dict[str, Any]],
    verified_company_names: set[str],
) -> list[dict[str, Any]]:
    """Return only jobs whose company is in the verified-company set."""

    if not verified_company_names:
        return []
    return [
        job
        for job in jobs
        if str(job.get("company_name") or "").strip() in verified_company_names
    ]


def filter_source_rows_to_verified_companies(
    source_rows: list[dict[str, Any]],
    verified_company_names: set[str],
) -> list[dict[str, Any]]:
    """Return only source rows whose company is in the verified-company set."""

    if not verified_company_names:
        return []
    return [
        row
        for row in source_rows
        if str(row.get("company_name") or "").strip() in verified_company_names
    ]


def derive_last_run_timestamp(source_rows: list[dict[str, Any]]) -> str | None:
    """Return the latest available source-status timestamp."""

    timestamps = [
        str(row.get("last_checked") or row.get("updated_at") or "").strip()
        for row in source_rows
        if str(row.get("last_checked") or row.get("updated_at") or "").strip()
    ]
    return max(timestamps) if timestamps else None


def parse_dashboard_timestamp(value: object) -> datetime | None:
    """Parse dashboard timestamps from SQLite and collector outputs."""

    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace(" ", "T")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def derive_verified_run_cutoffs(
    source_rows: list[dict[str, Any]],
    verified_company_names: set[str],
) -> dict[str, datetime]:
    """Return the latest source-check timestamp for each verified company."""

    cutoffs: dict[str, datetime] = {}
    if not verified_company_names:
        return cutoffs

    for row in source_rows:
        company_name = str(row.get("company_name") or "").strip()
        if company_name not in verified_company_names:
            continue
        timestamp = parse_dashboard_timestamp(row.get("last_checked") or row.get("updated_at"))
        if timestamp is None:
            continue
        existing = cutoffs.get(company_name)
        if existing is None or timestamp > existing:
            cutoffs[company_name] = timestamp
    return cutoffs


def filter_jobs_to_latest_verified_run(
    jobs: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    verified_company_names: set[str],
) -> list[dict[str, Any]]:
    """Keep only verified-company jobs seen during the latest source check."""

    cutoffs = derive_verified_run_cutoffs(source_rows, verified_company_names)
    if not cutoffs:
        return []

    filtered: list[dict[str, Any]] = []
    for job in jobs:
        company_name = str(job.get("company_name") or "").strip()
        cutoff = cutoffs.get(company_name)
        if cutoff is None:
            continue
        job_timestamp = parse_dashboard_timestamp(
            job.get("last_seen_at") or job.get("last_seen") or job.get("updated_at")
        )
        if job_timestamp is not None and job_timestamp >= cutoff:
            filtered.append(job)
    return filtered
