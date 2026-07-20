"""Trace manual Scotiabank expectations through collection and review outputs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

JOB_ID_PATTERN = re.compile(r"/(\d{6,})(?:/|$)")


def canonical_job_id(url: object) -> str:
    """Return the numeric SuccessFactors job identifier embedded in a job URL."""

    match = JOB_ID_PATTERN.search(str(url or ""))
    return match.group(1) if match else ""


def load_scotiabank_expected_urls(fixture_path: Path) -> list[str]:
    """Load non-empty expected Scotiabank URLs in their supplied audit order."""

    payload = yaml.safe_load(fixture_path.read_text(encoding="utf-8")) or {}
    for company in payload.get("companies") or []:
        if str(company.get("company_name") or "") != "Scotiabank":
            continue
        return [str(url) for url in company.get("expected_jobs") or [] if str(url or "").strip()]
    return []


def trace_expected_jobs(
    expected_urls: list[str],
    candidates: list[dict[str, str]],
    persisted_jobs: list[dict[str, Any]],
    review_rows: list[dict[str, str]],
    *,
    direct_statuses: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Classify expected roles without treating direct-page-only roles as extraction misses."""

    candidate_by_id = {canonical_job_id(row.get("url")): row for row in candidates}
    persisted_by_id = {
        canonical_job_id(row.get("job_url")): row for row in persisted_jobs if row.get("job_url")
    }
    review_by_id = {
        canonical_job_id(row.get("job_url")): row for row in review_rows if row.get("job_url")
    }
    direct_statuses = direct_statuses or {}
    trace: list[dict[str, str]] = []

    for expected_url in expected_urls:
        job_id = canonical_job_id(expected_url)
        candidate = candidate_by_id.get(job_id)
        persisted = persisted_by_id.get(job_id)
        review_row = review_by_id.get(job_id)
        if candidate is None:
            direct_status = direct_statuses.get(job_id, "unknown")
            outcome = (
                "active_but_not_in_current_listing"
                if direct_status in {"active", "redirected"}
                else "inactive_or_expired"
                if direct_status in {"inactive_or_expired", "not_found"}
                else "unknown"
            )
            trace.append(
                {
                    "expected_url": expected_url,
                    "job_id": job_id,
                    "title": str(persisted.get("title") if persisted else ""),
                    "direct_status": direct_status,
                    "raw_collection": "no",
                    "score": "",
                    "relevance_tier": "",
                    "rejection_reason": "Not present in the fresh Canada search listing.",
                    "persisted_state": str(
                        persisted.get("status") if persisted else "not persisted"
                    ),
                    "review_state": str(
                        review_row.get("review_state") if review_row else "not in slice"
                    ),
                    "dashboard_visibility": "not in current review slice",
                    "final_outcome": outcome,
                }
            )
            continue

        relevant = str(candidate.get("is_relevant") or "").lower() == "true"
        if relevant and persisted is not None:
            outcome = "collected_and_visible"
            visibility = (
                "Review needed"
                if str(review_row.get("review_state") if review_row else "")
                in {"New", "Score changed", "Tier changed", "Newly selected after calibration"}
                else "Previously reviewed filter"
                if review_row
                else "All Source-Verified Jobs"
            )
        elif relevant:
            outcome = "collected_but_slice_excluded"
            visibility = "not persisted"
        else:
            outcome = "collected_but_scoring_rejected"
            visibility = "not applicable"
        trace.append(
            {
                "expected_url": expected_url,
                "job_id": job_id,
                "title": str(candidate.get("title") or ""),
                "direct_status": "active",
                "raw_collection": "yes",
                "score": str(candidate.get("score") or ""),
                "relevance_tier": str(candidate.get("relevance_tier") or ""),
                "rejection_reason": str(candidate.get("rejection_reason") or ""),
                "persisted_state": str(
                    persisted.get("status") if persisted else "not persisted"
                ),
                "review_state": str(
                    review_row.get("review_state") if review_row else "not in slice"
                ),
                "dashboard_visibility": visibility,
                "final_outcome": outcome,
            }
        )
    return trace
