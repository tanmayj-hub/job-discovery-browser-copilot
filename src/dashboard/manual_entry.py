"""Helpers for manual job entry from the dashboard."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from processing.score import score_job
from storage.db import get_job_by_id, upsert_job


def normalize_manual_job_entry(job_data: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one manual dashboard submission into the storage shape."""

    normalized = {
        "company_name": str(job_data["company_name"]).strip(),
        "title": str(job_data["title"]).strip(),
        "location": str(job_data.get("location") or "").strip() or None,
        "job_url": str(job_data["job_url"]).strip(),
        "apply_url": str(job_data.get("apply_url") or "").strip() or None,
        "source_name": str(job_data["source_name"]).strip(),
        "source_mode": str(job_data.get("source_mode") or "manual_only").strip(),
        "description": str(job_data.get("description") or "").strip() or None,
        "status": str(job_data.get("status") or "new").strip(),
    }
    score_result = score_job(normalized)
    normalized["match_score"] = score_result.match_score
    normalized["match_reasons"] = score_result.match_reasons
    normalized["risk_flags"] = score_result.risk_flags
    return normalized


def score_and_save_manual_job(
    connection: sqlite3.Connection,
    job_data: Mapping[str, Any],
) -> dict[str, Any]:
    """Score and save one manual job entry, returning the stored job row."""

    normalized = normalize_manual_job_entry(job_data)
    job_id = upsert_job(connection, normalized)
    saved = get_job_by_id(connection, job_id)
    if saved is None:
        raise ValueError(f"Unable to load saved job {job_id}")
    return saved
