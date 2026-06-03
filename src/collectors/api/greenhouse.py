"""Greenhouse public jobs API collector."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from collectors.base import CollectorResult, NormalizedJob

GREENHOUSE_API_TIMEOUT_SECONDS = 15
GREENHOUSE_API_USER_AGENT = "JobDiscoveryBrowserCoPilot/0.1"
GREENHOUSE_API_HOSTS = {
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
    "boards-api.greenhouse.io",
}


def extract_greenhouse_board_token(url: str | None) -> str | None:
    """Extract a Greenhouse board token from supported public board URLs."""

    if not url:
        return None
    parsed = urlparse(str(url).strip())
    hostname = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if hostname not in GREENHOUSE_API_HOSTS:
        return None
    if hostname in {"boards.greenhouse.io", "job-boards.greenhouse.io"}:
        return path_parts[0] if path_parts else None
    if hostname == "boards-api.greenhouse.io" and len(path_parts) >= 4:
        if path_parts[0] == "v1" and path_parts[1] == "boards" and path_parts[3] == "jobs":
            return path_parts[2]
    return None


def _build_greenhouse_endpoint(board_token: str) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"


def _fetch_json(url: str, *, timeout: int = GREENHOUSE_API_TIMEOUT_SECONDS) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": GREENHOUSE_API_USER_AGENT,
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _normalize_greenhouse_job(
    job: dict[str, Any],
    *,
    company_name: str,
    source_name: str,
    board_slug: str,
) -> NormalizedJob:
    location = job.get("location")
    if isinstance(location, dict):
        location_name = str(location.get("name") or "").strip() or None
    else:
        location_name = str(location or "").strip() or None

    date_posted = None
    for field in ("first_published", "updated_at", "created_at"):
        value = job.get(field)
        if value:
            date_posted = str(value)
            break

    return NormalizedJob(
        company_name=company_name,
        title=str(job.get("title") or "").strip(),
        location=location_name,
        job_url=str(job.get("absolute_url") or "").strip() or None,
        apply_url=str(job.get("absolute_url") or "").strip() or None,
        source_name=source_name,
        source_mode="api_allowed",
        description=str(job.get("content") or "").strip() or None,
        date_posted=date_posted,
        external_job_id=str(job.get("id")) if job.get("id") is not None else None,
        ats_type="greenhouse",
        board_slug=board_slug,
        raw_payload_json=json.dumps(job, ensure_ascii=True, sort_keys=True),
    )


def collect_greenhouse_jobs(company: dict[str, Any]) -> CollectorResult:
    """Collect all public jobs from a Greenhouse board API."""

    company_name = str(company.get("name") or company.get("company_name") or "")
    source_name = str(
        company.get("source_name") or company.get("website_category") or "greenhouse"
    )
    board_token = extract_greenhouse_board_token(company.get("careers_url"))
    if not board_token:
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="invalid_source_config",
            collector="greenhouse_api",
            ats_type="greenhouse",
            source_mode="api_allowed",
            error="Missing Greenhouse board token in careers_url.",
        )

    endpoint = _build_greenhouse_endpoint(board_token)
    try:
        payload = _fetch_json(endpoint)
    except (HTTPError, URLError, TimeoutError) as exc:
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="api_error",
            collector="greenhouse_api",
            ats_type="greenhouse",
            source_mode="api_allowed",
            error=f"Greenhouse API request failed: {exc}",
        )
    except ValueError as exc:
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="parse_error",
            collector="greenhouse_api",
            ats_type="greenhouse",
            source_mode="api_allowed",
            error=f"Greenhouse API response could not be parsed: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="api_error",
            collector="greenhouse_api",
            ats_type="greenhouse",
            source_mode="api_allowed",
            error=f"Unexpected Greenhouse API error: {exc}",
        )

    jobs_payload = payload.get("jobs") if isinstance(payload, dict) else None
    if not isinstance(jobs_payload, list):
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="parse_error",
            collector="greenhouse_api",
            ats_type="greenhouse",
            source_mode="api_allowed",
            error="Greenhouse API response did not contain a jobs list.",
        )

    try:
        jobs = [
            _normalize_greenhouse_job(
                raw_job,
                company_name=company_name,
                source_name=source_name,
                board_slug=board_token,
            ).to_dict()
            for raw_job in jobs_payload
            if isinstance(raw_job, dict) and str(raw_job.get("title") or "").strip()
        ]
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="parse_error",
            collector="greenhouse_api",
            ats_type="greenhouse",
            source_mode="api_allowed",
            error=f"Failed to normalize Greenhouse jobs: {exc}",
        )

    return CollectorResult(
        company_name=company_name,
        source_name=source_name,
        status="success" if jobs else "no_jobs_found",
        collector="greenhouse_api",
        ats_type="greenhouse",
        source_mode="api_allowed",
        jobs_discovered=len(jobs),
        jobs=jobs,
    )
